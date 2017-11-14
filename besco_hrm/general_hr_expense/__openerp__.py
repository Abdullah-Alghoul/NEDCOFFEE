# -*- coding: utf-8 -*-
{
    'name': 'General HR Expense',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'summary': 'Employees Expense Management',
    'description': """
    """,
    'depends': ['general_hr', 'hr_expense', 'general_hr_account', 'report_aeroo',"base", "general_base", "account", "account_cancel", "account_asset"],
    'data': [
#              'security/general_hr_expense_security.xml',
#              'security/ir.model.access.csv',
#              'wizard/hr_expense_paid.xml',
#              'wizard/analysis_hr_expense.xml',
             
             'hr_expense_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
