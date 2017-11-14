# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED Contracts',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['ned_master', 'bes_contract_base', 'bes_purchase_contract', 'bes_sale_contract', 'general_account'],
    'data': [
            'wizard/wizrad_trucking_list.xml',
            'wizard/wizrad_invoice_view.xml',
            'security/ir.model.access.csv',
            'wizard/wizard_purchase_contract_view.xml',
            'report/report_view.xml',
            'purchase_contract_view.xml',
            'sale_contract_view.xml',
            's_contract_view.xml',
            'request_payment_view.xml',
            'long_short.xml',
            'wizard/partner_balance_confirmation.xml',
            #THANH: add filter sales/purchase for payment
            'account_payment_view.xml',
            'cron.xml',
            'contract_return_view.xml',
            'gain_loss.xml',
            #'dashboard_report.xml',
            'ir_sequence.xml'
            
            ],
    'installable': True,
    'auto_install': False,
}
