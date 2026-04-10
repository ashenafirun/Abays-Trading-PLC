
from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import UserError

from ..controllers.main import SESSION_EMP_ID

class ResDeviceLog(models.Model):
    _inherit = 'res.device.log'

    employee_id = fields.Many2one("hr.employee", string="Employee", compute="_compute_employee_id")

    def _compute_employee_id(self):
        for device in self:
            device.employee_id = False
            if device.x_employee_create_uid:
                device.employee_id = self.env['hr.employee'].sudo().browse(device.x_employee_create_uid)

    @api.model
    def _update_device(self, request):
        super(ResDeviceLog, self)._update_device(request)

        if request and hasattr(request, 'session'):
            emp_id = request.session.get(SESSION_EMP_ID)
            if emp_id:
                session_identifier = request.session.sid[:42]

                last_record = self.env['res.device.log'].sudo().search([
                    ('session_identifier', '=', session_identifier),
                    ('x_employee_create_uid', '=', False)
                ], limit=1, order='id desc')

                if last_record:
                    last_record.write({'x_employee_create_uid': emp_id})


class ResUsers(models.Model):
    _inherit = 'res.users'

    share_account_enabled = fields.Boolean(string="Share Account", copy=False)
    shared_employee_ids = fields.Many2many('hr.employee', string='Shared Employee', index=True, copy=False)

    @api.depends('totp_secret')
    def _compute_totp_enabled(self):
        super()._compute_totp_enabled()
        for user in self.sudo():
            if user.share_account_enabled:
                user.totp_enabled = False

    def _inverse_token(self):
        for user in self.sudo():
            if user.share_account_enabled:
                raise UserError("Cannot enable 2FA on shared account.")
        return super()._inverse_token()

    def write(self, vals):

        for u in self.sudo():
            if u.totp_enabled and vals.get('share_account_enabled', False):
                raise UserError("Cannot share account while 2FA is enbaled.")
            if u.share and vals.get('share_account_enabled', False):
                raise UserError("Cannot share account for public or portal user.")

        res = super().write(vals)

        if res and 'shared_employee_ids' in vals:
            for u in self.sudo():
                employee_ids = u.shared_employee_ids.ids
                devices = self.env["res.device"].search([("user_id", "=", u.id)])
                devices = devices.filtered(lambda d: d.employee_id.id not in employee_ids)
                devices._revoke()

        return res

    def _check_credentials(self, credential, env):
        auth_info = super(ResUsers, self)._check_credentials(credential, env)
        if auth_info and auth_info.get('auth_method', '') == 'passkey' and auth_info.get('uid', ''):
            uid = auth_info.get('uid', '')
            user = self.env['res.users'].sudo().browse(uid)
            if user and user.share_account_enabled and user.shared_employee_ids:
                auth_info['auth_method'] = 'password'
                auth_info['mfa'] = 'default'

        return auth_info

    def _mfa_url(self):
        if self.sudo()._is_internal() and self.sudo().share_account_enabled and self.sudo().shared_employee_ids:
            return '/web/employee/login'

        return super()._mfa_url()

    def action_totp_invite(self):
        if self.share_account_enabled:
            raise UserError("Cannot enable 2FA on shared account.")

        return super(ResUsers, self).action_totp_invite()

    @check_identity
    def action_totp_enable_wizard(self):
        if self.share_account_enabled:
            raise UserError("Cannot enable 2FA on shared account.")

        return super(ResUsers, self).action_totp_enable_wizard()

