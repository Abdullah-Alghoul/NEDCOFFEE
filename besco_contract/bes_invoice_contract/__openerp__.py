# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'BESCO Account Invoice',
    'version': '9.0',
    'category': 'BESCO 90',
    'depends': ['general_account','bes_stock_contract','bes_contract_base','bes_purchase_contract'],
    'data': [
                'account_invoice_view.xml',
            ],
    'installable': True,
    'auto_install': False,
}
