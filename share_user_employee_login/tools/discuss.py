from odoo.addons.mail.tools.discuss import Store

from odoo.http import request

original_get_result = Store.get_result

def custom_get_result(self):
    res = original_get_result(self)

    if 'mail.message' in res:
        messages = res['mail.message']
        for val in messages:
            val['employee_name'] = ''
            val['employee_id'] = 0
            id = val['id']
            msg = request.env['mail.message'].sudo().browse(id)
            if 'employee_id' in msg._fields and msg.employee_id:
                val['employee_name'] = msg.employee_id.name
                val['employee_id'] = msg.employee_id.id
                val['employee_avatar'] = f'/web/image/hr.employee.public/{msg.employee_id.id}/avatar_128'

    return res

Store.get_result = custom_get_result