# -*- coding: utf-8 -*-
{
    'name': 'Report Partner Balance',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'description': """
    """,
    'depends': ['general_account','report_aeroo'],
     'data': [
            'security/security.xml',
            'security/ir.model.access.csv',
            'report/report_view.xml',
            'partner_balance_view.xml',
            
            'menu.xml',
            ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
