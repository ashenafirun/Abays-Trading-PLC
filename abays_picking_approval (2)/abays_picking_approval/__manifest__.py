{
    'name': 'Abays Picking Approval',
    'version': '18.0.3.0.0',
    'summary': '4-stage GRN approval - auto fills employee name and signature',
    'author': 'Abays Trading PLC',
    'category': 'Inventory',
    'depends': ['stock', 'hr'],
    'data': [
        'security/picking_approval_groups.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
