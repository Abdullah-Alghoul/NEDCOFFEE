# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'BESCO Stock Contract',
    'version': '9.0',
    'category': 'BESCO 90',
    'depends': ['bes_purchase_contract', 'bes_sale_contract', 'general_stock', 'bes_contract_base'],
    'data': [
             'stock_view.xml',
             ],
    'installable': True,
    'auto_install': False,
}
