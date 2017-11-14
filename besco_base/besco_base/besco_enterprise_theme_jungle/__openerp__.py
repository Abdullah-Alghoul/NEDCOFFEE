# -*- coding: utf-8 -*-
# Copyright 2016 Openworx, LasLabs Inc.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": "BESCO Enterprise Theme - Jungle Color",
    "summary": """
    BESCO Backend theme!
    
Professional them, for Professional business
""",
    "version": "1.0",
    "category": "Themes/Backend", 
    "website": "http://www.besco.vn",
	"description": """
		Professional theme v9 community edition.
		The app dashboard is based on the module web_responsive from LasLabs Inc and the theme on Bootstrap United.
    """,
	'images':['images/screen.png'],
    "author": "BESCO",
    "license": "LGPL-3",
    "depends": ['web','website'],
    "data": [
        'views/assets.xml',
        'views/web.xml',
        'views/res_company.xml',
        'views/templates.xml',  
                ],
    "installable": True, 
}

