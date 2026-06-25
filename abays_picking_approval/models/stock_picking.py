from odoo import models, fields, api, exceptions
from datetime import datetime


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # These fields already exist in the database from previous Studio work
    # We just declare them here so the module can use them
    x_inspected_name = fields.Char(string='Inspected By', readonly=True, copy=False)
    x_inspected_signature = fields.Binary(string='Inspected Signature', readonly=True, copy=False)
    x_inspected_date = fields.Datetime(string='Inspected Date', readonly=True, copy=False)

    x_received_name = fields.Char(string='Received By', readonly=True, copy=False)
    x_received_signature = fields.Binary(string='Received Signature', readonly=True, copy=False)
    x_received_date = fields.Datetime(string='Received Date', readonly=True, copy=False)

    x_audited_name = fields.Char(string='Audited By', readonly=True, copy=False)
    x_audited_signature = fields.Binary(string='Audited Signature', readonly=True, copy=False)
    x_audited_date = fields.Datetime(string='Audited Date', readonly=True, copy=False)

    x_approved_name = fields.Char(string='Approved By', readonly=True, copy=False)
    x_approved_signature = fields.Binary(string='Approved Signature', readonly=True, copy=False)
    x_approved_date = fields.Datetime(string='Approved Date', readonly=True, copy=False)

    x_grn_approval_stage = fields.Selection([
        ('draft', 'Not Started'),
        ('inspected', 'Inspected'),
        ('received', 'Received'),
        ('audited', 'Audited'),
        ('approved', 'Approved'),
    ], string='GRN Approval Stage', default='draft', copy=False)

    def _is_grn(self):
        return self.picking_type_id.sequence_code == 'GRN'

    def _get_employee_info(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.user.id)], limit=1
        )
        if employee:
            return employee.name, employee.x_employee_signature
        return self.env.user.name, False

    def action_grn_inspect(self):
        for rec in self:
            if not rec._is_grn():
                raise exceptions.UserError('Approval only applies to GRN transfers.')
            if rec.x_grn_approval_stage != 'draft':
                raise exceptions.UserError('Already inspected.')
            name, signature = rec._get_employee_info()
            rec.write({
                'x_grn_approval_stage': 'inspected',
                'x_inspected_name': name,
                'x_inspected_signature': signature,
                'x_inspected_date': datetime.now(),
            })
            rec.message_post(body=f'<b>Inspected</b> by <b>{name}</b>', subtype_xmlid='mail.mt_note')

    def action_grn_receive(self):
        for rec in self:
            if rec.x_grn_approval_stage != 'inspected':
                raise exceptions.UserError('Must be Inspected first.')
            name, signature = rec._get_employee_info()
            rec.write({
                'x_grn_approval_stage': 'received',
                'x_received_name': name,
                'x_received_signature': signature,
                'x_received_date': datetime.now(),
            })
            rec.message_post(body=f'<b>Received</b> by <b>{name}</b>', subtype_xmlid='mail.mt_note')

    def action_grn_audit(self):
        for rec in self:
            if rec.x_grn_approval_stage != 'received':
                raise exceptions.UserError('Must be Received first.')
            name, signature = rec._get_employee_info()
            rec.write({
                'x_grn_approval_stage': 'audited',
                'x_audited_name': name,
                'x_audited_signature': signature,
                'x_audited_date': datetime.now(),
            })
            rec.message_post(body=f'<b>Audited</b> by <b>{name}</b>', subtype_xmlid='mail.mt_note')

    def action_grn_approve(self):
        for rec in self:
            if rec.x_grn_approval_stage != 'audited':
                raise exceptions.UserError('Must be Audited first.')
            name, signature = rec._get_employee_info()
            rec.write({
                'x_grn_approval_stage': 'approved',
                'x_approved_name': name,
                'x_approved_signature': signature,
                'x_approved_date': datetime.now(),
            })
            rec.message_post(body=f'<b>Approved</b> by <b>{name}</b>', subtype_xmlid='mail.mt_note')

    def button_validate(self):
        for rec in self:
            if rec._is_grn() and rec.x_grn_approval_stage != 'approved':
                labels = {
                    'draft': 'Inspection',
                    'inspected': 'Receive',
                    'received': 'Audit',
                    'audited': 'Final Approval',
                }
                raise exceptions.UserError(
                    f'GRN requires full approval before validation.\n'
                    f'Next step: {labels.get(rec.x_grn_approval_stage, "Approval")}'
                )
        return super().button_validate()
