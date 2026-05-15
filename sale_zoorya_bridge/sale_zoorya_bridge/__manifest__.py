# -*- coding: utf-8 -*-
{
    'name': 'Sale → POS Zoorya Bridge',
    'version': '18.0.1.1.0',
    'license': 'LGPL-3',
    'summary': 'Push Odoo 18 Sale Orders / Quotations to zoorya POS via Zoorya webhook',
    'description': """
        Sale → POS Zoorya Bridge
        ========================
        * Send any Sale Order or Quotation to zoorya POS with one click
        * Auto-send on order confirmation (optional)
        * Tracks sync state: Draft → Sent → Paid / Failed
        * Polls zoorya payment_status endpoint to detect when POS marks the order paid
        * Configurable: zoorya URL, API key, store ID, machine ID
    """,
    'author': 'teddy',
    'category': 'Sales/Point of Sale',
    'depends': ['sale'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
