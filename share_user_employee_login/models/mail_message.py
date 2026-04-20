

from odoo import api, fields, models
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = 'mail.message'

    employee_id = fields.Many2one("hr.employee", string="Employee", compute="_compute_employee_id")

    def _compute_employee_id(self):
        for message in self:
            message.employee_id = False
            if message.x_employee_create_uid:
                message.employee_id = self.env['hr.employee'].sudo().browse(message.x_employee_create_uid)
