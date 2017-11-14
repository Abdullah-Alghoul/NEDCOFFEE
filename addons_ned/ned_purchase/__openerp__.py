# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED Purchase',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['general_purchase','purchase','general_mrp_operations','ned_mrp'],
    'data': [
             
             'report/report_view.xml',
             'purchase.xml',
             
             ],
    'installable': True,
    'auto_install': False,
}
