from odoo import models, fields


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Transfer',
        ondelete='set null',
        index=True,
        readonly=True,
    )
