from odoo import models, fields, api, exceptions
from datetime import datetime


class PickingApprovalWizard(models.TransientModel):
    _name = 'picking.approval.wizard'
    _description = 'Picking Approval Wizard'

    picking_id = fields.Many2one('stock.picking', string='Transfer', required=True)
    approval_action = fields.Selection([
        ('inspect', 'Inspect'),
        ('receive', 'Receive'),
        ('audit', 'Audit'),
        ('approve', 'Approve'),
    ], string='Action', required=True)
    employee_name = fields.Char(string='Your Full Name', required=True,
                                help='Enter your full name as it will appear on the GRN printout')
    signature = fields.Binary(string='Your Signature', required=True,
                              help='Draw your signature')

    def action_confirm(self):
        self.ensure_one()
        picking = self.picking_id
        name = self.employee_name.strip()
        now = datetime.now()

        if self.approval_action == 'inspect':
            if picking.x_approval_state != 'draft':
                raise exceptions.UserError('This transfer has already been inspected.')
            picking.write({
                'x_approval_state': 'inspected',
                'x_inspected_name': name,
                'x_inspected_signature': self.signature,
                'x_inspected_by': self.env.user.id,
                'x_inspected_date': now,
            })

        elif self.approval_action == 'receive':
            if picking.x_approval_state != 'inspected':
                raise exceptions.UserError('Transfer must be Inspected first.')
            picking.write({
                'x_approval_state': 'received',
                'x_received_name': name,
                'x_received_signature': self.signature,
                'x_received_by': self.env.user.id,
                'x_received_date': now,
            })

        elif self.approval_action == 'audit':
            if picking.x_approval_state != 'received':
                raise exceptions.UserError('Transfer must be Received first.')
            picking.write({
                'x_approval_state': 'audited',
                'x_audited_name': name,
                'x_audited_signature': self.signature,
                'x_audited_by': self.env.user.id,
                'x_audited_date': now,
            })

        elif self.approval_action == 'approve':
            if picking.x_approval_state != 'audited':
                raise exceptions.UserError('Transfer must be Audited first.')
            picking.write({
                'x_approval_state': 'approved',
                'x_approved_name': name,
                'x_approved_signature': self.signature,
                'x_approved_by': self.env.user.id,
                'x_approved_date': now,
            })

        picking.message_post(
            body=f'<b>{self.approval_action.capitalize()}</b> by <b>{name}</b> on {now.strftime("%d/%m/%Y %H:%M")}',
            subtype_xmlid='mail.mt_note',
        )
        return {'type': 'ir.actions.act_window_close'}
