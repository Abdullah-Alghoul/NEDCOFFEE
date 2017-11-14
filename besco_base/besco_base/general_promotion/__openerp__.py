# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "General Master Promotion",
    "version" : "9.0",
    "author" : "BESCO GROUP",
    'category': 'General 90',
    "depends" : ["general_base", "general_product", "stock"],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    """,
    'data': [
                   "security/ir.model.access.csv",
                   "security/security.xml",
                    'promotion_view.xml',
                    'menu.xml'
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
