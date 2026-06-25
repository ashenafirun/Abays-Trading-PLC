from odoo import models, fields, api, exceptions
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_approval_state = fields.Selection([
        ('draft', 'Not Started'),
        ('inspected', 'Inspected'),
        ('received', 'Received'),
        ('audited', 'Audited'),
        ('approved', 'Approved'),
    ], string='Approval Stage', default='draft', tracking=True, copy=False)

    x_inspected_by = fields.Many2one('res.users', readonly=True, copy=False)
    x_inspected_name = fields.Char(string='Inspected By', readonly=True, copy=False)
    x_inspected_signature = fields.Binary(string='Inspected Signature', readonly=True, copy=False)
    x_inspected_date = fields.Datetime(string='Inspected Date', readonly=True, copy=False)

    x_received_by = fields.Many2one('res.users', readonly=True, copy=False)
    x_received_name = fields.Char(string='Received By', readonly=True, copy=False)
    x_received_signature = fields.Binary(string='Received Signature', readonly=True, copy=False)
    x_received_date = fields.Datetime(string='Received Date', readonly=True, copy=False)

    x_audited_by = fields.Many2one('res.users', readonly=True, copy=False)
    x_audited_name = fields.Char(string='Audited By', readonly=True, copy=False)
    x_audited_signature = fields.Binary(string='Audited Signature', readonly=True, copy=False)
    x_audited_date = fields.Datetime(string='Audited Date', readonly=True, copy=False)

    x_approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    x_approved_name = fields.Char(string='Approved By', readonly=True, copy=False)
    x_approved_signature = fields.Binary(string='Approved Signature', readonly=True, copy=False)
    x_approved_date = fields.Datetime(string='Approved Date', readonly=True, copy=False)

    x_show_approval = fields.Boolean(compute='_compute_show_approval')

    @api.depends('picking_type_id')
    def _compute_show_approval(self):
        for rec in self:
            rec.x_show_approval = rec.picking_type_id.sequence_code == 'GRN'

    def _get_employee_info(self):
        """Get linked HR employee name and signature for the current user."""
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1
        )
        if employee:
            return employee.name, employee.x_employee_signature
        # fallback to user name if no employee record
        return self.env.user.name, False

    def _do_approval(self, action):
        emp_name, emp_signature = self._get_employee_info()
        now = datetime.now()
        vals = {
            'inspect': {
                'x_approval_state': 'inspected',
                'x_inspected_by': self.env.user.id,
                'x_inspected_name': emp_name,
                'x_inspected_signature': emp_signature,
                'x_inspected_date': now,
            },
            'receive': {
                'x_approval_state': 'received',
                'x_received_by': self.env.user.id,
                'x_received_name': emp_name,
                'x_received_signature': emp_signature,
                'x_received_date': now,
            },
            'audit': {
                'x_approval_state': 'audited',
                'x_audited_by': self.env.user.id,
                'x_audited_name': emp_name,
                'x_audited_signature': emp_signature,
                'x_audited_date': now,
            },
            'approve': {
                'x_approval_state': 'approved',
                'x_approved_by': self.env.user.id,
                'x_approved_name': emp_name,
                'x_approved_signature': emp_signature,
                'x_approved_date': now,
            },
        }
        self.write(vals[action])
        self.message_post(
            body=f'<b>{action.capitalize()}</b> by <b>{emp_name}</b> on {now.strftime("%d/%m/%Y %H:%M")}',
            subtype_xmlid='mail.mt_note',
        )

    def action_inspect(self):
        for rec in self:
            if rec.x_approval_state != 'draft':
                raise exceptions.UserError('Already inspected.')
            rec._do_approval('inspect')

    def action_receive_approval(self):
        for rec in self:
            if rec.x_approval_state != 'inspected':
                raise exceptions.UserError('Must be Inspected first.')
            rec._do_approval('receive')

    def action_audit(self):
        for rec in self:
            if rec.x_approval_state != 'received':
                raise exceptions.UserError('Must be Received first.')
            rec._do_approval('audit')

    def action_approve(self):
        for rec in self:
            if rec.x_approval_state != 'audited':
                raise exceptions.UserError('Must be Audited first.')
            rec._do_approval('approve')

    def button_validate(self):
        for rec in self:
            if rec.x_show_approval and rec.x_approval_state != 'approved':
                labels = {'draft': 'Inspection', 'inspected': 'Receive',
                          'received': 'Audit', 'audited': 'Final Approval'}
                raise exceptions.UserError(
                    f'Requires full approval before validation.\n'
                    f'Next step: {labels.get(rec.x_approval_state, "Approval")}'
                )
        return super().button_validate()
