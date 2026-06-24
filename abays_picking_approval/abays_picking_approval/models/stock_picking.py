from odoo import models, fields, api, exceptions
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # --- Approval stage field ---
    x_approval_state = fields.Selection([
        ('draft', 'Not Started'),
        ('inspected', 'Inspected'),
        ('received', 'Received'),
        ('audited', 'Audited'),
        ('approved', 'Approved'),
    ], string='Approval Stage', default='draft', tracking=True, copy=False)

    # --- Step 1: Inspected by ---
    x_inspected_by = fields.Many2one('res.users', string='Inspected By', readonly=True, copy=False)
    x_inspected_date = fields.Datetime(string='Inspected Date', readonly=True, copy=False)

    # --- Step 2: Received by ---
    x_received_by = fields.Many2one('res.users', string='Received By', readonly=True, copy=False)
    x_received_date = fields.Datetime(string='Received Date', readonly=True, copy=False)

    # --- Step 3: Audited by ---
    x_audited_by = fields.Many2one('res.users', string='Audited By', readonly=True, copy=False)
    x_audited_date = fields.Datetime(string='Audited Date', readonly=True, copy=False)

    # --- Step 4: Approved by ---
    x_approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    x_approved_date = fields.Datetime(string='Approved Date', readonly=True, copy=False)

    # --- Computed visibility: only show approval buttons on GRN operation type ---
    x_show_approval = fields.Boolean(
        string='Show Approval',
        compute='_compute_show_approval',
    )

    @api.depends('picking_type_id')
    def _compute_show_approval(self):
        for rec in self:
            rec.x_show_approval = rec.picking_type_id.sequence_code == 'GRN'

    # --- Button: Inspect ---
    def action_inspect(self):
        for rec in self:
            if rec.x_approval_state != 'draft':
                raise exceptions.UserError('This transfer has already been inspected.')
            rec.x_approval_state = 'inspected'
            rec.x_inspected_by = self.env.user
            rec.x_inspected_date = datetime.now()
            rec._log_approval('Inspected', self.env.user)

    # --- Button: Receive ---
    def action_receive_approval(self):
        for rec in self:
            if rec.x_approval_state != 'inspected':
                raise exceptions.UserError('Transfer must be Inspected first.')
            rec.x_approval_state = 'received'
            rec.x_received_by = self.env.user
            rec.x_received_date = datetime.now()
            rec._log_approval('Received', self.env.user)

    # --- Button: Audit ---
    def action_audit(self):
        for rec in self:
            if rec.x_approval_state != 'received':
                raise exceptions.UserError('Transfer must be Received first.')
            rec.x_approval_state = 'audited'
            rec.x_audited_by = self.env.user
            rec.x_audited_date = datetime.now()
            rec._log_approval('Audited', self.env.user)

    # --- Button: Approve ---
    def action_approve(self):
        for rec in self:
            if rec.x_approval_state != 'audited':
                raise exceptions.UserError('Transfer must be Audited first.')
            rec.x_approval_state = 'approved'
            rec.x_approved_by = self.env.user
            rec.x_approved_date = datetime.now()
            rec._log_approval('Approved', self.env.user)

    # --- Block validate until fully approved for GRN ---
    def button_validate(self):
        for rec in self:
            if rec.x_show_approval and rec.x_approval_state != 'approved':
                stage_labels = {
                    'draft': 'Inspection',
                    'inspected': 'Receive',
                    'received': 'Audit',
                    'audited': 'Final Approval',
                }
                next_step = stage_labels.get(rec.x_approval_state, 'Approval')
                raise exceptions.UserError(
                    f'This transfer requires full approval before validation.\n'
                    f'Next required step: {next_step}'
                )
        return super().button_validate()

    def _log_approval(self, action, user):
        self.message_post(
            body=f'<b>{action}</b> by <b>{user.name}</b> on {datetime.now().strftime("%d/%m/%Y %H:%M")}',
            subtype_xmlid='mail.mt_note',
        )
