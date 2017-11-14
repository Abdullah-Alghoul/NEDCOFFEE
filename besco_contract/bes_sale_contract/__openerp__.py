# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'BESCO Sale Contract',
    'version': '9.0',
    'category': 'BESCO 90',
    'depends': ['general_account', 'general_stock', 'bes_contract_base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'ir_sequence.xml',
        'wizard/wizrad_si_view.xml',
        'wizard/wizrad_nls_view.xml',
        'wizard/wizrad_gdn_view.xml',
        'wizard/wizrad_do_view.xml',
        'wizard/wizrad_nvs_view.xml',
        'wizard/wizrad_invoice_view.xml',
        #'wizard/wizrad_out_stock_wti_view.xml',
        'port_view.xml',
        'sale_contract_view.xml',
        'delivery_order_view.xml',
        's_contract_view.xml',
        'delivery_order_view.xml',
        
        #THANH: add this to default value for object wizard
        'property_data.xml'
    ],
    'installable': True,
    'auto_install': False,
}
