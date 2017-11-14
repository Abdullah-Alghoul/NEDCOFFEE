# -*- coding: utf-8 -*-
{
    'name': 'BESCO VAS Tax Statement',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'description': """
    """,
    'depends': ['general_account', 'report_aeroo'],
     'data': [
            'security/security.xml',
            'wizard/print_tax_statement_view.xml',
            'report/report_view.xml',
            'menu.xml',
            
            'property_data.xml',
            ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
