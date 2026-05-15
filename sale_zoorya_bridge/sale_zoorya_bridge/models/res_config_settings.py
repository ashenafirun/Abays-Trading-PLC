# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    zoorya_odoo17_url = fields.Char(
        string='Odoo 17 URL',
        config_parameter='zoorya_bridge.odoo17_url',
        help='Base URL of the Odoo 17 instance (e.g. https://pos.yourdomain.com)',
    )
    zoorya_api_key = fields.Char(
        string='Zoorya API Key',
        config_parameter='zoorya_bridge.api_key',
        help='API key configured in pos_ecommerce_sync on Odoo 17',
    )
    zoorya_store_id = fields.Char(
        string='Default Store ID',
        config_parameter='zoorya_bridge.store_id',
        help=(
            'Sent as "storeId" in the webhook payload. '
            'Must match the company name in Odoo 17 exactly. '
            'Leave blank to use this Odoo 18 company name automatically.'
        ),
    )
    zoorya_machine_id = fields.Char(
        string='Machine ID',
        config_parameter='zoorya_bridge.machine_id',
        help=(
            'Optional. Routes orders to a specific POS machine in Odoo 17. '
            'Must match the "Machine Identifier" field on the Odoo 17 POS config.'
        ),
    )
    zoorya_auto_send_on_confirm = fields.Boolean(
        string='Auto-send to POS on Confirmation',
        config_parameter='zoorya_bridge.auto_send_on_confirm',
        help='Automatically push the order to Odoo 17 POS when a quotation is confirmed.',
    )

    def action_test_zoorya_connection(self):
        """Ping Odoo 17 with the configured API key."""
        self.ensure_one()
        url_base = (self.zoorya_odoo17_url or '').rstrip('/')
        api_key = self.zoorya_api_key or ''

        if not url_base:
            raise UserError(_('Please enter the Odoo 17 URL first.'))
        if not api_key:
            raise UserError(_('Please enter the Zoorya API key first.'))

        endpoint = f'{url_base}/zoorya/payment_status'
        try:
            response = requests.post(
                endpoint,
                json={'orderNo': '__connection_test__'},
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': api_key,
                },
                timeout=15,
            )
        except requests.exceptions.Timeout:
            raise UserError(_(
                'Connection timeout.\n'
                'Odoo 17 did not respond within 15 seconds.'
            ))
        except requests.exceptions.ConnectionError as exc:
            raise UserError(_('Cannot reach Odoo 17:\n%s') % exc)

        if response.status_code == 401:
            raise UserError(_('Authentication failed — check the API key on both sides.'))

        try:
            result = response.json()
        except ValueError:
            raise UserError(_(
                'Odoo 17 responded but did not return JSON (HTTP %s).'
            ) % response.status_code)

        if response.status_code >= 500:
            error = result.get('error') or response.text[:200]
            raise UserError(_('Odoo 17 server error:\n%s') % error)

        _logger.info('[ZOORYA BRIDGE] Connection test OK → %s', endpoint)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection OK'),
                'message': _(
                    'Successfully reached Odoo 17 at %s.\n'
                    'The Zoorya bridge endpoint is responding.'
                ) % url_base,
                'type': 'success',
                'sticky': False,
            },
        }
