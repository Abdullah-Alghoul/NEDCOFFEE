# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

{
    "name" : "General Report Warehouse",
    "version" : "1.0",
    "author" : 'Pham Tuan Kiet <tykiet.208@gmail.com>',
    'complexity': "normal",
    "description": """
    """,
    "category": 'General 9.0',
    "website" : "",
    "images" : [],
    "depends" : ["general_stock"],
    "data" : [
        "security/ir.model.access.csv",
        "report/report_view.xml",
#         "wizard/stock_report.xml",
        "report_stock_balance_sheet.xml"
    ],
    "test" : [
    ],
    'certificate': False,
    "auto_install": False,
    "application": True,
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
