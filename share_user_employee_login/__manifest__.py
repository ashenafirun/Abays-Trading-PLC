{
    "name": "Share User Account For Multiple Employees",
    "summary": "With this app, you can share an internal user with multiple employees. Each employee can log in to Odoo using their employee pin code. "
               "Employee Login|Share User|Share Account|Employee Account",
    'description': """
        With this app, you can share an internal user with multiple employees. Each employee can log in to Odoo using their employee pin code.
    """,
    'version': '18.0.0.1',

    "category": "Productivity/Technical Settings",
    'author': "Sonny Huynh",
    "depends": ["base", "mail", "web", "hr"],
    "data": [
        'data/share_internal_user_group.xml',
        "views/res_user_views.xml",
        "views/mail_views.xml",
        "views/res_device_views.xml",
        "views/templates.xml",
    ],

    'assets': {

        'web.assets_backend': [
            'share_user_employee_login/static/src/js/thread_patch.js',
            'share_user_employee_login/static/src/js/user_menu_patch.js',
            'share_user_employee_login/static/src/js/composer_patch.js',

            'share_user_employee_login/static/src/xml/message.xml',
            'share_user_employee_login/static/src/xml/user_menu_patch.xml',
            'share_user_employee_login/static/src/xml/composer_patch.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    "application": False,
    "installable": True,
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'license': 'OPL-1',
    'price': 250.00,
    'currency': 'EUR',
}

