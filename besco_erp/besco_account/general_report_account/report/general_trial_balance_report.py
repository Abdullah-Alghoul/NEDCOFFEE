# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'no_child': self.no_child,
        })
    def no_child(self, coa_id):
        if not coa_id:
            return False
        res = self.pool.get('account.account').search(self.cr, self.uid, [('parent_id', 'child_of', coa_id)])
        if len(res) > 0:
            return True
        return False
    
    def get_start_date(self,report):
        return self.get_vietname_date(report.date_start) 
    
    def get_end_date(self,report):
        return self.get_vietname_date(report.date_end) 
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
