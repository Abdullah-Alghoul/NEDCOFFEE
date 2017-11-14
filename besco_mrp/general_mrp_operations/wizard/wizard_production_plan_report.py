# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time

class wizard_production_plan_report(osv.osv_memory):
    _name = "wizard.production.plan.report"
    _columns = {
                'state_id': fields.many2one('mrp.production.stage', 'State', required=True),
                'workcenter_id': fields.many2one('mrp.workcenter', 'Workcenter', required=True),
        }
    
    def _default_state_id(self, cr, uid, context=None):
        state_ids = self.pool.get('mrp.production.stage').search(cr, uid, [])
        return state_ids and state_ids[0] or False
    
    _defaults = {
                 'state_id': _default_state_id
                 } 
    
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.production.plan.report'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'production_plan_report' , 'datas': datas} 
    
wizard_production_plan_report()
