# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED MRP COSTING',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ["general_account","ned_master","ned_mrp","ned_stock","ned_accounting"],
    'data': [
             
            'security/ir.model.access.csv',
            'report/report_view.xml',
            'costing_view.xml',
            'cron.xml'
             ],
    'installable': True,
    'auto_install': False,
}
