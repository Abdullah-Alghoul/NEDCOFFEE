# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED KCS',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['general_kcs', 'ned_stock','ned_contract'],
    'data': [
             "security/ir.model.access.csv",
             "wizard/wizard_report_kcs_quanlity.xml",
             "standard_view.xml",  
             "ir_sequence.xml",
             "kcs_view.xml",
             "report/report_view.xml",
             'dashboard_report.xml',
             'sale_contract_report.xml',
             'stock_intake_quality.xml',
             'pss.xml',
             'stock_contract_allocation.xml'
             ],
    'installable': True,
    'auto_install': False,
}