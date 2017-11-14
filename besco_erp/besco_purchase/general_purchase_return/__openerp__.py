# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'General Purchase Returned',
    'version': '9.0',
    'category': 'General 90',
    'depends': ['general_purchase','general_stock'],
    'data': [
        'purchase_sequence.xml',
        'purchase_return_view.xml',
        'purchase_return_report.xml',
        'data/mail_template_data.xml',
        
        'views/report_purchaseorder.xml',
        'views/report_purchasequotation.xml',
    ],
    'installable': True,
    'auto_install': False,
}
