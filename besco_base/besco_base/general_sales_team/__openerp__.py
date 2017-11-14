# -*- coding: utf-8 -*-

{
    "name" : "BESCO Sales Teams",
    "version" : "9.1",
    "author" : "BESCO",
    "category": 'BESCO',
    "description": """
    1) Set Sales team as Hirachies
    2) Modify some Sales team rules
    
    """,
    'website': 'http://www.besco.com',
    'init_xml': [],
    "depends" : ["general_base", "sales_team"],
    'data': [
        'security/security.xml',
        'views/sales_team_views.xml',
    ],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
