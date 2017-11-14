# -*- coding: utf-8 -*-

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.translate import _
import time

class wizard_print_inventory(osv.osv_memory):
    _name = "wizard.print.inventory"
    _description = "Print Inventory"
                    
    def print_report(self, cr, uid, ids, context=None): 
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'stock.picking'
        datas['form'] = {'active_ids':context.get('active_ids', [])}
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_pending_grp' , 'datas': datas}
    
wizard_print_inventory() 

        
class wizard_print_request_materials(osv.osv_memory):
    _name = "wizard.print.request.materials"
    _description = "Print Request Materials"
    _columns = {
                'from_date' : fields.date(string='From Date'),
                'to_date' : fields.date(string='To Date'),
                'production_id':fields.many2one('mrp.production',string="Production"),
    }
                    
    def print_report(self, cr, uid, ids, context=None): 
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.print.request.materials'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_print_request_materials' , 'datas': datas}
    
    def print_request(self, cr, uid, ids, context=None): 
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.print.request.materials'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_material_request_Reports' , 'datas': datas}
    
    
    
    
wizard_print_request_materials() 
