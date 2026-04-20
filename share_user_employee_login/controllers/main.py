
import logging

from odoo import SUPERUSER_ID, api, http, tools, _
from odoo.http import request
from odoo.http import route
from odoo.addons.web.controllers.home import Home as WebHome


_logger = logging.getLogger(__name__)

SESSION_EMP_ID = "employee_id_login"


class Home(WebHome):

    @http.route(
        '/web/employee/login',
        type='http', auth='public', methods=['GET', 'POST'], sitemap=False,
        website=True, multilang=False
    )
    def web_employee_login(self, redirect=None, **kwargs):
        if request.session.uid:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        if not request.session.get('pre_uid'):
            return request.redirect('/web/login')

        error = None

        user = request.env['res.users'].sudo().browse(request.session['pre_uid'])

        if not user._is_internal() or not user.share_account_enabled or not user.shared_employee_ids:
            return request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

        if user and request.httprequest.method == 'POST' and kwargs.get('employee_id') and kwargs.get('code'):
            emp = request.env['hr.employee'].sudo().browse(int(kwargs.get('employee_id')))
            if emp:
                if emp.pin != kwargs.get('code'):
                    error = _("Invalid PIN Code.")
                else:
                    request.session.finalize(request.env)
                    request.update_env(user=request.session.uid)
                    request.update_context(**request.session.context)
                    response = request.redirect(self._login_redirect(request.session.uid, redirect=redirect))

                    request.session[SESSION_EMP_ID] = emp.id

                    request.session.touch()
                    return response
            else:
                error = _("Employee does not exist.")

        request.session.touch()
        return request.render('share_user_employee_login.employee_login_form', {
            'user': user,
            'error': error,
            'shared_employee_ids': user.shared_employee_ids,
            'redirect': redirect,
        })
