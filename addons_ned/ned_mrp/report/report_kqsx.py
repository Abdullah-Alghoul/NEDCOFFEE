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
        self.date_start = False
        self.localcontext.update({
            'get_line':self.get_line,
            'get_totalqty':self.get_totalqty
        })
        
    def get_balance_net(self,net,gdp_net,delivery_net):
        return net - (gdp_net + delivery_net)
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_line(self):
        self.get_header()
        result_ids = []
        sql ='''
            SELECT id from mrp_operation_result_produced_product 
                        WHERE operation_result_id in (
                        SELECT id from mrp_operation_result 
                            WHERE production_shift = '1'
                                and '2016-10-01' 
                                between date(timezone('UTC',start_date::timestamp)) and date(timezone('UTC',end_date::timestamp)))
                        Order by id
        '''%(self.production_shift,self.from_date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            result_ids.append(i['id'])
        
        return self.pool.get('mrp.operation.result.produced.product').browse(self.cr,self.uid,result_ids)
    
    def get_totalqty(self,line):
        total_qty =0.0
        for i in line:
            total_qty += i.total_qty
        
        return total_qty
        
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.from_date = wizard_data['date_from'] or False
        self.to_date = wizard_data['date_to'] or False
        self.production_shift = wizard_data['production_shift'] and wizard_data['production_shift'][0]  or False
        return True