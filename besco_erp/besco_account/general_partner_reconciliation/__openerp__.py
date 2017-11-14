# -*- coding: utf-8 -*-
{
    "name" : "General Partner Reconciliation",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "depends" : ["account"],
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    """,
    'data': [
            'security/ir.model.access.csv',
#             'security/security.xml',
            
            'partner_reconciliation_view.xml',
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
