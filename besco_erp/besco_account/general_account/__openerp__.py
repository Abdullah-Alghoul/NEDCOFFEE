# -*- coding: utf-8 -*-
{
    "name" : "General Account",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "depends" : ["base", "general_base", "account", "account_cancel", "account_asset"],
    "description": """
    """,
    'data': [
            'security/ir.model.access.csv',
            'security/security.xml',
            
            'wizard/update_due_date.xml',
            'wizard/account_chart_view.xml',
            'wizard/quick_create_entry_view.xml',
            'views/account_financial_report.xml',
            
            'data/ir_sequence.xml',
            
            'account_period_view.xml',
            'account_invoice_view.xml',
            'account_view.xml',
            'account_payment.xml',
            'company_view.xml',
            'chart_of_account.xml',
            'cron.xml',
            'menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
