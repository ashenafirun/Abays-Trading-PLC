# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import json
import logging

_logger = logging.getLogger(__name__)

SYNC_STATES = [
    ('draft',      'Not Sent'),
    ('sent',       'Sent to POS'),
    ('paid',       'Paid'),
    ('failed',     'Failed'),
    ('cancelled',  'Cancelled in POS'),
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ─── Sync state & tracking fields ────────────────────────────────────────

    zoorya_sync_state = fields.Selection(
        SYNC_STATES,
        string='POS Sync Status',
        default='draft',
        tracking=True,
        copy=False,
        index=True,
    )
    zoorya_pos_reference = fields.Char(
        string='POS Reference',
        readonly=True,
        copy=False,
        help='POS order reference assigned by Odoo 17 (e.g. Z-Order 00001-001-0003)',
    )
    zoorya_order_id = fields.Char(
        string='Zoorya Order ID',
        readonly=True,
        copy=False,
        help='The orderNo sent in the webhook payload — equals this sale order name',
    )
    zoorya_synced_at = fields.Datetime(
        string='Sent to POS At',
        readonly=True,
        copy=False,
    )
    zoorya_sync_error = fields.Text(
        string='Sync Error',
        readonly=True,
        copy=False,
    )
    zoorya_pos_state = fields.Char(
        string='POS Order State',
        readonly=True,
        copy=False,
        help='Raw state of the POS order as reported by Odoo 17',
    )
    zoorya_amount_paid = fields.Monetary(
        string='Amount Paid in POS',
        currency_field='currency_id',
        readonly=True,
        copy=False,
    )

    # ─── Configuration helper ─────────────────────────────────────────────────

    def _get_zoorya_config(self):
        """Return bridge config from system parameters."""
        get = self.env['ir.config_parameter'].sudo().get_param
        return {
            'odoo17_url':          (get('zoorya_bridge.odoo17_url') or '').rstrip('/'),
            'api_key':             get('zoorya_bridge.api_key') or '',
            'store_id':            get('zoorya_bridge.store_id') or '',
            'machine_id':          get('zoorya_bridge.machine_id') or '',
            'auto_send_on_confirm': get('zoorya_bridge.auto_send_on_confirm') == 'True',
        }

    # ─── Payload builder ──────────────────────────────────────────────────────

    def _build_zoorya_payload(self):
        """
        Build the webhook JSON payload from this sale order.
        Maps Odoo 18 sale.order → Zoorya /zoorya/webhook/order format expected
        by pos_ecommerce_sync on Odoo 17.
        """
        self.ensure_one()
        config = self._get_zoorya_config()

        store_id  = config['store_id']  or self.company_id.name
        machine_id = config['machine_id']

        # ── Customer ──────────────────────────────────────────────────────────
        partner = self.partner_id
        customer = {
            'name':  partner.name  or '',
            'email': partner.email or '',
            'phone': partner.phone or partner.mobile or '',
            'vat':   partner.vat   or '',
        }
        if partner.street:
            customer['street'] = partner.street
        if partner.city:
            customer['city'] = partner.city

        # ── Order lines ───────────────────────────────────────────────────────
        lines = []
        for line in self.order_line:
            if line.display_type:          # skip section / note lines
                continue
            if line.product_uom_qty <= 0:
                continue

            product  = line.product_id
            qty      = line.product_uom_qty
            code     = (product.default_code or str(product.id)).strip()

            # Use price_subtotal (= qty × unit_price × (1-discount%), excl. tax)
            # Dividing back gives us the per-unit ex-tax price regardless of
            # whether the product tax is price-included or price-excluded.
            unit_price_excl = round(line.price_subtotal / qty, 6) if qty else 0.0
            line_total       = round(line.price_subtotal, 2)

            # is_taxed: True when any sale tax with amount > 0 applies
            is_taxed = any(t.amount > 0 for t in line.tax_id)

            # POS / product category (best-effort — works if POS module present)
            category_name = None
            if hasattr(product, 'pos_categ_ids') and product.pos_categ_ids:
                category_name = product.pos_categ_ids[0].name
            elif product.categ_id:
                category_name = product.categ_id.name

            line_data = {
                'code':      code,
                'name':      line.name or product.name,
                'quantity':  qty,
                'unitprice': round(unit_price_excl, 2),
                'linetotal': line_total,
                'is_taxed':  is_taxed,
            }
            if category_name:
                line_data['category'] = category_name

            lines.append(line_data)

        if not lines:
            raise UserError(_('No valid order lines to send to POS.'))

        # ── Totals ────────────────────────────────────────────────────────────
        # amount_untaxed is the definitive ex-tax total after discounts
        total_value = round(self.amount_untaxed, 2)

        # ── Payment hint ──────────────────────────────────────────────────────
        payment_name = (
            self.payment_term_id.name
            if self.payment_term_id
            else 'Cash'
        )

        # ── Notes ─────────────────────────────────────────────────────────────
        notes = self.note or ''
        if self.client_order_ref:
            ref_note = f'Customer Ref: {self.client_order_ref}'
            notes = f'{ref_note}\n{notes}' if notes else ref_note

        # ── Assemble payload ──────────────────────────────────────────────────
        payload = {
            'order': {
                'header': {
                    'orderNo':          self.name,
                    'displayedOrderNo': self.name,
                    'storeId':          store_id,
                    'totalValue':       total_value,
                    'notes':            notes,
                },
                'customer': customer,
                'lines':    lines,
                'payment': {
                    'description': payment_name,
                    'method':      payment_name,
                    'value':       total_value,
                },
            }
        }

        if machine_id:
            payload['order']['header']['machineId'] = machine_id

        return payload

    # ─── Send to POS ─────────────────────────────────────────────────────────

    def action_send_to_pos(self):
        """Button action: send selected orders to Odoo 17 POS."""
        for order in self:
            order._send_to_pos()

    def _send_to_pos(self):
        """Build payload and POST it to the Odoo 17 Zoorya webhook endpoint."""
        self.ensure_one()
        if self.zoorya_sync_state in ('sent', 'paid'):
            raise UserError(_(
                'This order has already been sent to POS.\n'
                'Use "Reset Sync" first if you need to send it again.'
            ))
        if self.state == 'cancel':
            raise UserError(_('Cancelled orders cannot be sent to POS.'))

        config = self._get_zoorya_config()

        if not config['odoo17_url']:
            raise UserError(_(
                'Odoo 17 URL is not configured.\n'
                'Go to Settings → Technical → Zoorya Bridge to set it up.'
            ))
        if not config['api_key']:
            raise UserError(_(
                'Zoorya API key is not configured.\n'
                'Go to Settings → Technical → Zoorya Bridge to set it up.'
            ))

        try:
            payload = self._build_zoorya_payload()
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('Failed to build order payload: %s') % str(e))

        url = f"{config['odoo17_url']}/zoorya/webhook/order"
        _logger.info('[ZOORYA BRIDGE] Sending %s → %s', self.name, url)
        _logger.debug('[ZOORYA BRIDGE] Payload: %s', json.dumps(payload, indent=2))

        try:
            response = requests.post(
                url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key':    config['api_key'],
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

        except requests.exceptions.Timeout:
            self._set_sync_failed('Connection timeout — Odoo 17 did not respond within 30 s')
            raise UserError(_(
                'Connection timeout.\n'
                'Please verify the Odoo 17 URL in Settings → Zoorya Bridge.'
            ))
        except requests.exceptions.ConnectionError as e:
            msg = f'Cannot connect to Odoo 17: {e}'
            self._set_sync_failed(msg)
            raise UserError(_(msg))
        except requests.exceptions.HTTPError:
            detail = ''
            try:
                body = response.json()
                detail = body.get('error') or body.get('message') or ''
            except Exception:
                detail = (response.text or '').strip()[:500]
            msg = f'HTTP {response.status_code}'
            if detail:
                msg = f'{msg}: {detail}'
            self._set_sync_failed(msg)
            raise UserError(_(msg))
        except ValueError:
            msg = 'Odoo 17 returned a non-JSON response'
            self._set_sync_failed(msg)
            raise UserError(_(msg))

        _logger.info('[ZOORYA BRIDGE] Response for %s: %s', self.name, result)

        if result.get('success'):
            # status can be 'created' (immediately processed) or 'queued'
            self.write({
                'zoorya_sync_state':    'sent',
                'zoorya_order_id':      result.get('order_id') or self.name,
                'zoorya_pos_reference': result.get('pos_reference') or '',
                'zoorya_synced_at':     fields.Datetime.now(),
                'zoorya_sync_error':    False,
            })
            status = result.get('status', 'sent')
            _logger.info('[ZOORYA BRIDGE] ✅ %s → POS (%s)', self.name, status)
        else:
            error = result.get('error') or 'Unknown error from Odoo 17'
            self._set_sync_failed(error)
            raise UserError(_('Failed to send order to POS:\n%s') % error)

    def _set_sync_failed(self, error_msg):
        self.write({
            'zoorya_sync_state': 'failed',
            'zoorya_sync_error': error_msg,
        })
        _logger.error('[ZOORYA BRIDGE] ❌ %s failed: %s', self.name, error_msg)

    # ─── Auto-send on confirm ─────────────────────────────────────────────────

    def action_confirm(self):
        result = super().action_confirm()
        config = self._get_zoorya_config()
        if config['auto_send_on_confirm']:
            for order in self:
                if order.zoorya_sync_state == 'draft':
                    try:
                        order._send_to_pos()
                    except Exception as e:
                        # Log but don't block the confirmation
                        _logger.warning(
                            '[ZOORYA BRIDGE] Auto-send failed for %s: %s',
                            order.name, e
                        )
        return result

    # ─── Payment status check ─────────────────────────────────────────────────

    def action_check_pos_payment(self):
        """Button action: poll Odoo 17 for the latest payment status."""
        for order in self:
            if not order.zoorya_order_id:
                raise UserError(_('This order has not been sent to POS yet.'))
            order._check_pos_payment()
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'title':   _('POS Payment Status'),
                'message': _('Payment status refreshed from Odoo 17 POS.'),
                'type':    'success',
                'sticky':  False,
            }
        }

    def _check_pos_payment(self):
        """Poll /zoorya/payment_status on Odoo 17 and update local fields."""
        self.ensure_one()
        config = self._get_zoorya_config()
        if not config['odoo17_url'] or not config['api_key']:
            return

        try:
            url = f"{config['odoo17_url']}/zoorya/payment_status"
            response = requests.post(
                url,
                json={'orderNo': self.zoorya_order_id},
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key':    config['api_key'],
                },
                timeout=15,
            )
            if response.status_code != 200:
                _logger.warning(
                    '[ZOORYA BRIDGE] payment_status HTTP %s for %s',
                    response.status_code, self.name
                )
                return

            result = response.json()
            if not result.get('success'):
                _logger.warning(
                    '[ZOORYA BRIDGE] payment_status not found for %s: %s',
                    self.name, result.get('error')
                )
                return

            pay_status = result.get('status')         # 'paid' | 'partial' | 'unpaid'
            pos_state  = result.get('state')          # 'draft' | 'paid' | 'cancel' ...
            pos_ref    = result.get('pos_reference') or self.zoorya_pos_reference
            amount_paid = float(result.get('amount_paid', 0))

            write_vals = {
                'zoorya_pos_reference': pos_ref,
                'zoorya_pos_state':     pos_state or '',
                'zoorya_amount_paid':   amount_paid,
            }

            if pay_status == 'paid' or pos_state == 'paid':
                write_vals['zoorya_sync_state'] = 'paid'
            elif pos_state == 'cancel':
                write_vals['zoorya_sync_state'] = 'cancelled'

            self.write(write_vals)
            _logger.info(
                '[ZOORYA BRIDGE] Payment status for %s: %s (POS state: %s)',
                self.name, pay_status, pos_state
            )

        except Exception as e:
            _logger.warning(
                '[ZOORYA BRIDGE] Could not check payment status for %s: %s',
                self.name, e
            )

    # ─── Reset ────────────────────────────────────────────────────────────────

    def action_reset_zoorya_sync(self):
        """Allow re-sending a failed order."""
        self.write({
            'zoorya_sync_state':    'draft',
            'zoorya_sync_error':    False,
            'zoorya_pos_reference': False,
            'zoorya_order_id':      False,
            'zoorya_synced_at':     False,
            'zoorya_pos_state':     False,
            'zoorya_amount_paid':   0.0,
        })

    # ─── Cron job ─────────────────────────────────────────────────────────────

    @api.model
    def cron_check_pos_payments(self):
        """
        Scheduled action: refresh payment status for all orders
        that were sent to POS but are not yet marked paid/cancelled.
        """
        orders = self.search([
            ('zoorya_sync_state', '=', 'sent'),
            ('zoorya_order_id', '!=', False),
        ])
        if not orders:
            return

        _logger.info(
            '[ZOORYA BRIDGE CRON] Checking payment status for %d orders', len(orders)
        )
        for order in orders:
            order._check_pos_payment()
