# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED Account Invoice',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['ned_contract','general_account','ned_stock','bes_sale_contract','account_cashflow_operations'],
    'data': [
             'security/ir.model.access.csv',
             'account_invoice.xml',
             'report/report_view.xml',
             'stock.xml',
             'cron.xml',
             'mortgage_management.xml'
            ],
    'installable': True,
    'auto_install': False,
}

