# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "BESCO MRP",
    "version" : "9.0",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    'category': 'General 90',
    "depends" : ["mrp","mrp_operations", "general_product", "general_stock"],
    "description": """
    """,
    'update_xml': [
                'security/security.xml',
                'security/ir.model.access.csv',
                'report/report_view.xml',
                'mrp_view.xml',
                'product_view.xml',
                
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
