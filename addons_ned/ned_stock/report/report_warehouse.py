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
        self.acc_number = False
        self.localcontext.update({
            'get_date':self.get_date,
            'get_datetime':self.get_datetime,
            'total_bb':self.total_bb,
            'total_sc16':self.total_sc16,
            'gross_weight':self.gross_weight,
            'get_printf':self.get_printf,
            'get_printf_dates':self.get_printf_dates,
            'get_maize':self.get_maize,
            'get_do':self.get_do,
            'get_nvs':self.get_nvs,
            'get_grp':self.get_grp
        })
    
    def get_maize(self,line):
        if not line:
            return 'N'
        if line[0].maize_yn:
            return'Y'
        else:
            return 'N'
    
    def get_packing(self,line):
        
        return 
        
    def get_printf(self):
        users = self.pool.get('res.users').browse(self.cr,self.uid,self.uid)
        return users.name
    
    def get_printf_dates(self):
        now = datetime.now()
        strs = str(now.hour) +":" + str(now.minute) +" "+str(now.day) +"/"+str(now.month) +"/"+str(now.year)
        return strs
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def gross_weight(self,line):
        if not line:
            return 0
        return (line[0].first_weight - line[0].second_weight) or 0.0
    
    def total_bb(self,line):
        if not line:
            return 0
        return line[0].black + line[0].broken
    
    def total_sc16(self,line):
        if not line:
            return 0
        return line.screen18 + line.screen16
    
    def get_do(self,o):
        sql ='''
            SELECT id from delivery_order where picking_id = %s
        '''%(o.id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            delivery = self.pool.get('delivery.order').browse(self.cr,self.uid,line['id'])
            return delivery and delivery.name or ''
    
    def get_nvs(self,o):
        sql ='''
            SELECT id from delivery_order where picking_id = %s
        '''%(o.id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            delivery = self.pool.get('delivery.order').browse(self.cr,self.uid,line['id'])
            return delivery and delivery.contract_id.name or ''
    
    def get_grp(self,line):
        if line.stack_id:
            for stack_line in line.stack_id.move_ids:
                if stack_line.location_id.usage !='internal' and stack_line.location_dest_id.usage == 'internal':
                    return stack_line.picking_id.name
        
        return ''
            
        
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
