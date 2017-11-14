# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED Master Report',
    'version': '9.0',
    'category': 'NED 90 Report Manager',
    'depends': ['ned_contract','ned_kcs','ned_mrp'],
    'data': [
            'report.xml',
            # 'mrp_report.xml',
            'longshort.xml',
            'risk_mgt.xml',
            's_contract.xml',
            'shipment.xml',
            'production_report.xml',
            'grn_matching_report.xml'
             ],
    'installable': True,
    'auto_install': False,
    'author': 'Nedcoffee Vietnam Ltd',
}
