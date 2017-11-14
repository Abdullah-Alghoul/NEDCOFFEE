# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp import SUPERUSER_ID

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_line':self.get_line,
        })
        
        
    
    def get_line(self):
        
        sql = '''
            SELECT id from stock_stack order by name
        '''
        val =[]
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            stack = self.pool.get('stock.stack').browse(self.cr,1,i['id'])
            if stack.init_qty == 0:
                continue
            
            val.append({
                        'stack_name':stack.name,
                        'product_id':stack.product_id.default_code,
                        'init_qty':stack.init_qty,
                        'stack_qty':stack.stack_qty
                        })
        return val
    