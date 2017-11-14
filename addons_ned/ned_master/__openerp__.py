# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED Master Data',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['general_base', 'product','general_product', 'stock'],
    'data': [
             'security/ir.model.access.csv',
             'district_merge.xml',
             'master_view.xml'
             ],
    'installable': True,
    'auto_install': False,
}
    