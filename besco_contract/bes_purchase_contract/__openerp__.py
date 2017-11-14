# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'BESCO Purchase Contract',
    'version': '9.0',
    'category': 'BESCO 90',
    'depends': ['general_stock', 'bes_contract_base', 'account'],
    'data': [
             
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/wizard_purchase_contract_view.xml',
        'ir_sequence.xml',
        'purchase_contract_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}
