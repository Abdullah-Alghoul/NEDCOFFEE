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
        self.production_id = False
        self.production_shift = False
        self.total_qty = 0.0
        self.date_start = False
        self.localcontext.update({
            'get_line':self.get_line,
            'get_totalqty':self.get_totalqty,
            'get_emp':self.get_emp,
            'get_reportdate':self.get_reportdate,
            'get_catsx':self.get_catsx
        })
        
    def get_balance_net(self,net,gdp_net,delivery_net):
        return net - (gdp_net + delivery_net)
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_catsx(self):
        self.get_header()
        return 'Ca ' + self.production_shift
        
    
    def get_reportdate(self):
        self.get_header()
        return self.get_date(self.from_date)
        
    
    def get_emp(self):
        self.get_header()
        result_ids = []
        sql ='''
                SELECT id from mrp_operation_result 
                    WHERE production_shift = '%s'
                        and '%s' 
                        between date(timezone('UTC',start_date::timestamp)) and date(timezone('UTC',end_date::timestamp))
                Order by id
                limit 1
        '''%(self.production_shift,self.from_date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            result_ids.append(i['id'])
        return self.pool.get('mrp.operation.result').browse(self.cr,self.uid,result_ids).direct_labour
    
    def get_line(self):
        self.get_header()
        result_ids = []
        sql ='''
            SELECT id from mrp_operation_result_produced_product 
                        WHERE operation_result_id in (
                        SELECT id from mrp_operation_result 
                            WHERE production_shift = '%s'
                                and '%s' 
                                between date(timezone('UTC',start_date::timestamp)) and date(timezone('UTC',end_date::timestamp)))
                        Order by id
        '''%(self.production_shift,self.from_date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            result_ids.append(i['id'])
        
        return self.pool.get('mrp.operation.result.produced.product').browse(self.cr,self.uid,result_ids)
    
    def get_totalqty(self):
        self.get_header()
        result_ids = []
        sql ='''
            SELECT sum(product_qty) product_qty from mrp_operation_result_produced_product 
                WHERE operation_result_id in (
                SELECT id from mrp_operation_result 
                    WHERE production_shift = '%s'
                        and '%s' 
                        between date(timezone('UTC',start_date::timestamp)) and date(timezone('UTC',end_date::timestamp)))
        '''%(self.production_shift,self.from_date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            self.product_qty = i['product_qty'] or 0.0
        return self.product_qty
    
   
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.from_date = wizard_data['start_date'] or False
        self.production_shift = wizard_data['production_shift'] and wizard_data['production_shift'][0]  or False
        return True