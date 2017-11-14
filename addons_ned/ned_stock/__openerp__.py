# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'NED STOCK',
    'version': '9.0',
    'category': 'NED 90',
    'depends': ['general_stock','bes_stock_contract', 'ned_contract'],
    'data': [
            'wizard/stock_valuation_history_view.xml',
            'wizard/stock_view.xml',
            'wizard/wizard_print_report.xml',
            'report/report_view.xml',
            'security/ir.model.access.csv',
            
            'stock_view.xml',
            'grn_matching.xml',
             ],
    'installable': True,
    'auto_install': False,
}
