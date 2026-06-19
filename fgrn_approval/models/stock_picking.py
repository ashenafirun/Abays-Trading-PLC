from odoo import models, fields, api
from odoo.exceptions import UserError

# FGRN(FGTN) operation type ID — Abays Trading PLC #SULULTA
FGRN_PICKING_TYPE_ID = 25
REQUIRED_APPROVALS = 4


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ── Fields ────────────────────────────────────────────────────────────────

    is_fgrn_type = fields.Boolean(
        compute='_compute_is_fgrn_type',
        store=True,
        string='Is FGRN Transfer',
    )
    fgrn_approval_id = fields.Many2one(
        'approval.request',
        string='FGRN Approval Request',
        copy=False,
        readonly=True,
        index=True,
    )
    fgrn_approval_status = fields.Selection(
        related='fgrn_approval_id.request_status',
        string='Approval Status',
        store=True,
    )
    fgrn_approved_count = fields.Integer(
        compute='_compute_fgrn_approval_counts',
        store=True,
        string='Approvals Received',
    )
    fgrn_is_approved = fields.Boolean(
        compute='_compute_fgrn_approval_counts',
        store=True,
        string='Fully Approved',
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends('picking_type_id')
    def _compute_is_fgrn_type(self):
        for picking in self:
            picking.is_fgrn_type = (
                picking.picking_type_id.id == FGRN_PICKING_TYPE_ID
            )

    @api.depends(
        'fgrn_approval_id',
        'fgrn_approval_id.approver_ids',
        'fgrn_approval_id.approver_ids.status',
    )
    def _compute_fgrn_approval_counts(self):
        for picking in self:
            if picking.fgrn_approval_id:
                approved = picking.fgrn_approval_id.approver_ids.filtered(
                    lambda a: a.status == 'approved'
                )
                picking.fgrn_approved_count = len(approved)
                picking.fgrn_is_approved = len(approved) >= REQUIRED_APPROVALS
            else:
                picking.fgrn_approved_count = 0
                picking.fgrn_is_approved = False

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_request_fgrn_approval(self):
        """Create an FGRN approval request and open it."""
        self.ensure_one()

        if self.fgrn_approval_id:
            raise UserError(
                'An approval request already exists for this transfer (%s). '
                'Open the Approvals smart button to view it.'
                % self.fgrn_approval_id.name
            )

        category = self.env['approval.category'].search(
            [('name', '=', 'FGRN Approval')], limit=1
        )
        if not category:
            raise UserError(
                'The "FGRN Approval" category was not found.\n'
                'Go to Approvals ▸ Configuration ▸ Approval Types and '
                'make sure it exists.'
            )

        approval = self.env['approval.request'].create({
            'name': 'FGRN Approval — %s' % self.name,
            'category_id': category.id,
            'picking_id': self.id,
            'request_owner_id': self.env.user.id,
        })
        self.fgrn_approval_id = approval.id
        # Submit the request so approvers receive notifications
        approval.action_confirm()

        return {
            'type': 'ir.actions.act_window',
            'name': 'FGRN Approval',
            'res_model': 'approval.request',
            'res_id': approval.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_fgrn_approval(self):
        """Open the linked approval request."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'FGRN Approval',
            'res_model': 'approval.request',
            'res_id': self.fgrn_approval_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Validation guard ──────────────────────────────────────────────────────

    def button_validate(self):
        """Block validation of FGRN transfers until all 4 approvals are done."""
        for picking in self:
            if picking.picking_type_id.id != FGRN_PICKING_TYPE_ID:
                continue  # Not an FGRN transfer — no restriction

            if not picking.fgrn_approval_id:
                raise UserError(
                    'This FGRN transfer requires approval before it can be validated.\n\n'
                    'Click "Request FGRN Approval" to start the approval process.'
                )

            if not picking.fgrn_is_approved:
                count = picking.fgrn_approved_count
                raise UserError(
                    'Cannot validate: %d of %d approvals received.\n\n'
                    'Required approvers:\n'
                    '  • Store Manager\n'
                    '  • Quality Manager\n'
                    '  • Warehouse Manager\n'
                    '  • Operations Manager\n\n'
                    'All 4 must approve before this transfer can be validated.'
                    % (count, REQUIRED_APPROVALS)
                )

        return super().button_validate()
