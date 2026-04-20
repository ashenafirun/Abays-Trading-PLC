# -*- coding: utf-8 -*-


from odoo import models
from odoo.http import request
from ..controllers.main import SESSION_EMP_ID

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        result[SESSION_EMP_ID] = request.session.get(SESSION_EMP_ID, 0)
        result["employee_avatar"] = ''
        result["employee_name"] = ''

        if result[SESSION_EMP_ID] > 0:
            employee = self.env['hr.employee'].sudo().browse(result[SESSION_EMP_ID])
            if employee:
                result["employee_avatar"] = f'/web/image/hr.employee.public/{employee.id}/avatar_128'
                result["employee_name"] = employee.name

        return result