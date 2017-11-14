# -*- coding: utf-8 -*-
{
    "name" : "General Account Analytic",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "depends" : ["base", "account", "analytic", "general_account"],
    "description": """
    """,
    'data': [
        'data/ir_sequence.xml',
        
        'views/analytic_view.xml',
        'views/analytic_distribution.xml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
