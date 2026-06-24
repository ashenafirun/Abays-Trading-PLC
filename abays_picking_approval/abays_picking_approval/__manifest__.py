{
    'name': 'Abays Picking Approval',
    'version': '18.0.1.0.0',
    'summary': '4-stage approval workflow for FA/GRN transfers before validation',
    'author': 'Abays Trading PLC',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [
        'security/picking_approval_groups.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
