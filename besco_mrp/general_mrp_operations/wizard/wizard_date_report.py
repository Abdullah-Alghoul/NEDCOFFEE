# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time

class wizard_date_report(osv.osv_memory):
    _name = "wizard.date.report"
    _columns = {
                'from_date': fields.date('From date', required=True),
                'to_date': fields.date('To date', required=True)
        }
    
    _defaults = { 
            'from_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
            'to_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }   
    
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.date.report'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'date_report' , 'datas': datas} 
    
wizard_date_report()
