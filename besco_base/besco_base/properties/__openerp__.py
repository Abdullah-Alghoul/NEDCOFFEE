#!/usr/bin/env python
#-*- coding:utf-8 -*-
##############################################################################
#
#
##############################################################################

{
    "name" : "Project Property",
    "version" : "1.0",
    "depends" : ["base"],
    "author" : "Le Truong Thanh",
    "description": """Project property""",
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'data': [      
        "security/properties_security.xml",  
        "properties_view.xml",
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate' : '',
}
