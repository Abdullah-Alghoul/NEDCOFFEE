# -*- encoding: utf-8 -*-
{
    'name': 'Cash Flow Management Operations',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'description': '''
Cash Management Operations: 
     1) Straigth Loan Demands
        Supported are Straight Loan Demands with following characteristics:
        - Option 1 : Single payment of principal and interest amount on the maturity date
        - Option 2 : Payment of interest at start date and principal amount on the maturity date
        - Day Count Basis : 360 or 365
        - Interest calculation formula : amount * rate * days/day_count_basis
        - Currency equal to currency of associated Bank Journal
        - Generation of Straight Load Demand letter meant for the Bank
        Confirming a Straight Loan Demand results in the following actions:
        - creation of a Cash Management Provision Entries
     2) Short Term Placements
        Functionality : idem as Straight Loand Demands

    ''',
    'depends': ['general_account'],
    'update_xml' : [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'account_cash_operation.xml',
        
        'wizard/print_report.xml',
        'wizard/wizard_generate_accrual_entry_view.xml',
        
        'report/report_view.xml',
    ],
    'installable': True,
}
