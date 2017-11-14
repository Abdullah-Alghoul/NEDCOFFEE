# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'General Sale Returned',
    'version': '9.0',
    'category': 'General 90',
    'depends': ['crm_claim'],
    'data': [
        'sale_sequence.xml',
        'sale_return_view.xml',
        'sale_return_report.xml',
        'data/mail_template_data.xml',
        
        'views/report_saleorder.xml',
        'views/report_salequotation.xml',
        
    ],
    'installable': True,
    'auto_install': False,
}
