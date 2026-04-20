from . import tools
from . import controllers
from . import models

from odoo import api, SUPERUSER_ID

def pre_init_hook(env):

    env.cr.execute("""
        UPDATE ir_model_fields 
        SET state = 'base' 
        WHERE name IN ('x_employee_create_uid', 'x_employee_write_uid') 
        AND state = 'manual'
    """)

def post_init_hook(env):

    field_names = ('x_employee_create_uid', 'x_employee_write_uid')
    module_name = 'share_user_employee_login'

    env.cr.execute("""
        UPDATE ir_model_fields 
        SET state = 'manual'
        WHERE name IN %s
    """, (field_names,))

    env.cr.execute("""
        DELETE FROM ir_model_data 
        WHERE model = 'ir.model.fields' 
        AND module = %s 
        AND res_id IN (SELECT id FROM ir_model_fields WHERE name IN %s)
    """, (module_name, field_names))
