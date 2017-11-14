# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time

class wizard_report_kcs_quanlity(osv.osv_memory):
    _name = "wizard.report.kcs.quanlity"
    _columns = {
        's_contract': fields.many2one("s.contract", "S Contract")
    }
    
    def printf_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.report.kcs.quanlity'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_stock_with_kcs_quality_details' , 'datas': datas} 
    