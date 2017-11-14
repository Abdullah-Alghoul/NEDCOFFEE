# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

from osv import fields, osv
from tools.translate import _
import time
from datetime import datetime
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
from openerp import netsvc

class report_mrp_incomplete(osv.osv_memory):
    _name = 'report.mrp.incomplete'
    _columns = {
              }
    _defaults = { 
    }      
    
    
    def print_inphieu(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'report.mrp.incomplete'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'trapaco_reports_incomplete' , 'datas': datas} 

report_mrp_incomplete()
