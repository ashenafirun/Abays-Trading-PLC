from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class PartialPaymentWizard(models.TransientModel):
    _name = 'partial.payment.wizard'
    _description = 'Apply a partial amount from an existing payment to an invoice'

    move_id = fields.Many2one(
        'account.move', string='Invoice', required=True, readonly=True,
    )

    @api.model
    def action_open_from_move(self, move):
        """Called from the invoice server action. Runs in normal Python
        (not the safe_eval sandbox), so translations and full ORM work."""
        if move.move_type not in ('out_invoice', 'in_invoice', 'out_refund', 'in_refund'):
            raise UserError(_("Apply Partial Payment only works on customer/vendor invoices."))
        if move.state != 'posted':
            raise UserError(_("Post the invoice first."))
        if move.payment_state in ('paid', 'in_payment', 'reversed'):
            raise UserError(_("This invoice is already settled."))

        inv_line = move.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            and not l.reconciled)
        if len(inv_line) != 1:
            raise UserError(_(
                "Could not find a single open receivable/payable line on this invoice."))

        wiz = self.create({
            'move_id': move.id,
            'invoice_line_id': inv_line.id,
            'invoice_residual': abs(inv_line.amount_residual),
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Apply Partial Payment'),
            'res_model': 'partial.payment.wizard',
            'view_mode': 'form',
            'res_id': wiz.id,
            'target': 'new',
        }
    company_id = fields.Many2one(related='move_id.company_id')
    company_currency_id = fields.Many2one(related='company_id.currency_id')

    # The invoice's own open receivable/payable line
    invoice_line_id = fields.Many2one(
        'account.move.line', string='Invoice Line', required=True, readonly=True,
    )
    invoice_residual = fields.Monetary(
        string='Invoice Amount Due', currency_field='company_currency_id',
        readonly=True,
    )

    # The counterpart open line to draw from (the existing payment)
    counterpart_line_id = fields.Many2one(
        'account.move.line', string='Payment to apply',
        domain="[('id', 'in', available_line_ids)]",
    )
    available_line_ids = fields.Many2many(
        'account.move.line', compute='_compute_available_lines',
    )
    counterpart_available = fields.Monetary(
        string='Payment Available', currency_field='company_currency_id',
        compute='_compute_counterpart_available',
    )

    amount = fields.Monetary(
        string='Amount to Apply', currency_field='company_currency_id',
    )

    @api.depends('move_id')
    def _compute_available_lines(self):
        """Open counterpart lines: same partner, same account, opposite sign,
        not fully reconciled, single-currency only."""
        for wiz in self:
            inv_line = wiz.invoice_line_id
            if not inv_line:
                wiz.available_line_ids = False
                continue
            # Opposite sign to the invoice line (a payment credits a receivable)
            invoice_is_debit = float_compare(
                inv_line.debit, inv_line.credit,
                precision_rounding=wiz.company_currency_id.rounding) > 0
            domain = [
                ('account_id', '=', inv_line.account_id.id),
                ('partner_id', '=', inv_line.partner_id.id),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                ('id', '!=', inv_line.id),
                # single currency only: line currency == company currency
                ('currency_id', '=', wiz.company_currency_id.id),
            ]
            if invoice_is_debit:
                domain.append(('credit', '>', 0))
            else:
                domain.append(('debit', '>', 0))
            wiz.available_line_ids = self.env['account.move.line'].search(domain)

    @api.depends('counterpart_line_id')
    def _compute_counterpart_available(self):
        for wiz in self:
            wiz.counterpart_available = abs(
                wiz.counterpart_line_id.amount_residual) if wiz.counterpart_line_id else 0.0

    @api.onchange('counterpart_line_id')
    def _onchange_counterpart(self):
        """Default the amount to the smaller of the two residuals, so the
        common case (pay it all up to what's available) is one click."""
        if self.counterpart_line_id:
            self.amount = min(self.invoice_residual, self.counterpart_available)

    def action_apply(self):
        self.ensure_one()
        rounding = self.company_currency_id.rounding

        # --- Guardrails -------------------------------------------------
        if not self.counterpart_line_id:
            raise UserError(_("Select a payment to apply."))

        if float_is_zero(self.amount, precision_rounding=rounding) or self.amount < 0:
            raise UserError(_("Enter a positive amount to apply."))

        if float_compare(self.amount, self.invoice_residual,
                         precision_rounding=rounding) > 0:
            raise UserError(_(
                "You cannot apply more than the invoice amount due (%s).",
                self.invoice_residual))

        if float_compare(self.amount, self.counterpart_available,
                         precision_rounding=rounding) > 0:
            raise UserError(_(
                "The selected payment only has %s available.",
                self.counterpart_available))

        inv_line = self.invoice_line_id
        cp_line = self.counterpart_line_id

        # Single-currency safety net
        if inv_line.currency_id != self.company_currency_id or \
           cp_line.currency_id != self.company_currency_id:
            raise UserError(_(
                "This tool only supports single-currency (company currency) "
                "lines. Reconcile multi-currency items the standard way."))

        # --- Which side is debit / credit ------------------------------
        if inv_line.debit > 0:
            debit_line, credit_line = inv_line, cp_line
        else:
            debit_line, credit_line = cp_line, inv_line

        # Create the partial reconcile directly, for exactly the typed amount.
        self.env['account.partial.reconcile'].create({
            'amount': self.amount,
            'debit_move_id': debit_line.id,
            'credit_move_id': credit_line.id,
        })

        return {'type': 'ir.actions.act_window_close'}
