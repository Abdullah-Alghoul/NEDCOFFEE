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


class reports_date(osv.osv_memory):
    _name = 'reports.date'
    _columns = {
              'date': fields.date('Ngày báo cáo', required=True),
              'date_tichluy': fields.date('Ngày tích luỹ', required=True),
              }
    _defaults = { 
            'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
            'date_tichluy': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        }   
    
    def print_inphieu(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'report.mrp.planning'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'trapaco_reports_date' , 'datas': datas} 
reports_date()
