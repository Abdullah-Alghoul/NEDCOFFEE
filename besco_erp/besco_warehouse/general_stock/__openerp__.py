# -*- coding: utf-8 -*-
{
    "name" : "General Stock",
    "version" : "9.0",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    'category': 'BESCO',
    "depends" : ["general_base", "stock", "report_aeroo"],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    """,
    'data': [
         'security/security.xml',
         'report/report_view.xml',
         'report/stock_onhand_report.xml',
         
         'stock_view.xml',
         'stock_lot_view.xml',
         
         'menu.xml',
         ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
