{
    'name': 'Partial Payment Reconcile (Single Currency)',
    'version': '1.0',
    'summary': 'Apply a typed partial amount from an existing payment onto a customer invoice',
    'description': """
Adds an "Apply Partial Payment" action on customer invoices.
Lets a user pick an existing, already-recorded payment (or any open
credit line for the same partner/account) and reconcile only a typed
amount against the invoice - leaving the invoice partially open and the
payment partially available. No write-off, no new payment, no double-count.

Single-currency only (company currency = line currency). Multi-currency
lines are blocked to avoid posting wrong FX gain/loss.
    """,
    'category': 'Accounting/Accounting',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/partial_payment_wizard_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
