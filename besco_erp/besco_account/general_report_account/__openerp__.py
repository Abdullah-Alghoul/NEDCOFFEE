# -*- coding: utf-8 -*-
{
    "name" : "Vietname Legal Reports",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "description": """
    """,
    "images" : [],
    "depends" : ["general_account", "general_account_regularization",
                 "report_aeroo"],
    "data" : [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/templates.xml",
        
        "menu.xml",
        "report/report_view.xml",
        
        "report_account_ledger.xml",
        "report_trial_balance.xml",
        "report_financial_report.xml",
    ],
    'certificate': False,
    "auto_install": False,
    "application": False,
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
