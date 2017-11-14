# -*- encoding: utf-8 -*-
{
    'name': 'Web Printscreen ZB',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'description': """
        Module to export current active tree view in to excel report
    """,
    'depends': ['web'],
    'data': ['views/web_printscreen_zb.xml'],
    'qweb': ['static/src/xml/web_printscreen_export.xml'],
    'installable': True,
    'auto_install': False,
    'web_preload': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: