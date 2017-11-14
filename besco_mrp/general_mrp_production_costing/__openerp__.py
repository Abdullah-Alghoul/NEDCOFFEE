# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "General MRP Production Costing",
    "version" : "7.0",
    "author" : "Phạm Tuấn Kiệt <kiet.pt@besco.vn>",
    'category': 'General 90',
    "depends" : ["general_base","general_mrp","general_account","general_mrp_account"],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    """,
    'update_xml': [
        "security/security.xml",
        
        "mrp_costing_config_view.xml",
        "mrp_production_costing_view.xml"
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
