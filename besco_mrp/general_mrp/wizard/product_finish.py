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

class product_finish(osv.osv_memory):
    _name = 'product.finish'
    _columns = {
              'production_id': fields.many2one('mrp.production', 'Lệnh sản xuất', required=True)
              }
    
    def print_inphieu(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'report.mrp.incomplete'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'trapaco_product_finish' , 'datas': datas} 
product_finish()
