{
    'name': 'FGRN Transfer Approval',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Approval workflow for FGRN(FGTN) transfers — 4 approvers required before validation',
    'description': """
        Custom approval module for FGRN(FGTN) transfers:
        - Requires approval from Store Manager, Quality Manager,
          Warehouse Manager, and Operations Manager
        - All 4 approvers work independently (any order)
        - Validate button hidden until all 4 approvals received
        - Transfer report prints approver name, date, and signature line
    """,
    'author': 'Abays Trading PLC',
    'depends': ['stock', 'approvals'],
    'data': [
        'views/stock_picking_views.xml',
        'report/stock_picking_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
