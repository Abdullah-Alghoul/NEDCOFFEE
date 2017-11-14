# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED MRP',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['general_mrp', 'general_mrp_operations',"ned_stock",'ned_contract','general_kcs'],
    'data': [
            'report/report_view.xml',
            'wizard/request.xml',
            'wizard/wizard_stock_picking_view.xml',
            'mrp_view.xml',
            'batch_report.xml',
            'purchase_contract_view.xml',
            'ir_sequence.xml',
            'security/ir.model.access.csv',
            'stock.xml',
            'dashboard_report.xml'
             ],
    'installable': True,
    'auto_install': False,
}
