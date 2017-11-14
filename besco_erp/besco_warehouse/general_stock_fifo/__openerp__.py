# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "General Stock FIFO",
    "version" : "9.0",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    'category': 'General 90',
    "depends" : ["general_stock", 
                 "general_account",
                ],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    
    """,
    'data': [
#         'security/ir.model.access.csv',
#         'security/security.xml',

        'cron.xml',
        'stock_fifo_view.xml',
        'menu.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
