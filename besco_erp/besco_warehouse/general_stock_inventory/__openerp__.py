# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "General Stock Inventory",
    "version" : "9.0",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    'category': 'General 90',
    "depends" : ["general_stock",
                 "report_aeroo", 
#                  "report_aeroo_ooo"
                 ],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    """,
    'data': [
        'report/report_view.xml',
        'stock_inventory.xml',
        
        'cron.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
