{
    'name': 'Abays GRN Approval',
    'version': '18.0.5.0.0',
    'summary': '4-stage GRN approval with access rights, auto signature background removal, date on printout',
    'author': 'Abays Trading PLC',
    'category': 'Inventory',
    'depends': ['stock', 'hr'],
    'data': [
        'security/picking_approval_groups.xml',
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/grn_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
