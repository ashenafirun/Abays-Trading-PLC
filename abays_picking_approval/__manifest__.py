{
    'name': 'Abays GRN Approval',
    'version': '18.0.4.0.0',
    'summary': '4-stage GRN approval with employee name and signature',
    'author': 'Abays Trading PLC',
    'category': 'Inventory',
    'depends': ['stock', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
