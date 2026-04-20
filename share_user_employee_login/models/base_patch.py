
from ..controllers.main import SESSION_EMP_ID

from odoo import models, fields, api, tools
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class Base(models.AbstractModel):
    _inherit = 'base'

    x_employee_create_uid = fields.Integer(string='Employee Created By', copy=False, readonly=True)
    x_employee_write_uid = fields.Integer(string='Employee Last Updated By', copy=False, readonly=True)

    def _register_hook(self):

        super()._register_hook()

        if not hasattr(self.env.registry, '_magic_fields_ownership_released'):
            _logger.info(">>> Releasing Magic Fields ownership to prevent deletion on uninstall...")

            field_names = ('x_employee_create_uid', 'x_employee_write_uid')

            query = """
                UPDATE ir_model_fields 
                SET state = 'manual' 
                WHERE name IN %s AND state = 'base';

                DELETE FROM ir_model_data 
                WHERE model = 'ir.model.fields' 
                  AND res_id IN (SELECT id FROM ir_model_fields WHERE name IN %s)
                  AND module != 'base';
            """
            self.env.cr.execute(query, (field_names, field_names))

            self.env.registry._magic_fields_ownership_released = True

        for model_name, model_class in self.env.registry.items():
            if not model_class._auto:
                f1 = model_class._fields.get('x_employee_create_uid')
                f2 = model_class._fields.get('x_employee_write_uid')

                if f1:
                    f1.store = False
                if f2:
                    f2.store = False

    def _prepare_create_values(self, vals_list):
        if not self._auto:
            return super()._prepare_create_values(vals_list)

        result_vals_list = super()._prepare_create_values(vals_list)
        emp_id = self._get_emp_id_from_session()
        if emp_id:
            for vals in result_vals_list:
                if 'x_employee_create_uid' in self._fields:
                    vals['x_employee_create_uid'] = emp_id
                if 'x_employee_write_uid' in self._fields:
                    vals['x_employee_write_uid'] = emp_id
        return result_vals_list

    def _write_multi(self, vals_list):
        if not self._auto:
            return super()._write_multi(vals_list)

        emp_id = self._get_emp_id_from_session()
        if emp_id:
            for vals in vals_list:
                if 'x_employee_write_uid' in self._fields:
                    vals['x_employee_write_uid'] = emp_id
        return super()._write_multi(vals_list)

    def _get_emp_id_from_session(self):
        try:
            if request and hasattr(request, 'session'):
                return request.session.get(SESSION_EMP_ID)
        except Exception:
            return False
        return False

    def _check_removed_columns(self, log=False):
        return super()._check_removed_columns(log=log)