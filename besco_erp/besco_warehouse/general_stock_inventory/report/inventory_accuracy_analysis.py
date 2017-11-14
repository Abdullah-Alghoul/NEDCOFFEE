# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.sum_system_value = 0.0
        self.sum_count_value  = 0.0
        self.sum_adjust_value = 0.0
        self.sum_percent = 0.0
        
        self.localcontext.update({
            'get_header':self.get_header,
            'get_line':self.get_line,
            'get_sum_system_value': self.get_sum_system_value,
            'get_sum_count_value':self.get_sum_count_value,
            'get_sum_adjust_value':self.get_sum_adjust_value,
            'get_sum_percent':self.get_sum_percent,
            'get_vietname_date':self.get_vietname_date,
            'get_group_type':self.get_group_type,
            'get_vietname_datetime': self.get_vietname_datetime
        })
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_group_type(self,type):
        if not type:
            return 'All Product'
        group_type = {
                'Product':'One product only',
                'partial':'Manual Selection of Products',
                'none':'All Product'
                }
        return group_type[type],
    
    def get_header(self):
        res ={}
        
        group_type = {
                'product':'One product only',
                'partial':'Manual Selection of Products',
                'none':'All Product'
                }
        
        wizard_data = self.localcontext['data']['form']
        inventory_id = wizard_data['inventory_id'][0]
        location_id = wizard_data['location_id'][0]
        
        sql ='''
            SELECT sw.name warehouse_name, si.name inventory_name,sl.name location_name,si.date,si.group_type,com.name company_name
            FROM  stock_inventory si
            LEFT JOIN res_company com on si.company_id = com.id
            LEFT JOIN stock_warehouse sw on si.warehouse_id = sw.id
            LEFT JOIN stock_location sl on si.location_id = sl.id
            WHERE si.id = %s
        ''' %(inventory_id)
        
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            res= {
                'warehouse_name':i['warehouse_name'],
                'inventory_name':i['inventory_name'],
                'date':i['date'],
                'group_type':group_type[i['group_type']],
                'company_name':i['company_name'],
                }        
        sql ='''
            SELECT name
            FROM stock_location
            where id = %s
        '''%(location_id)
        
        self.cr.execute(sql)
        data =self.cr.dictfetchone()
        if data and data ['name']:
            inventory_location = data and data ['name']
        res.update({'inventory_location':inventory_location})
        
        return res
                    
    def get_line(self,order_line):
 
        sum_adjust_qty = 0
        sum_count_qty  = 0
        
       
        res =[]
        for i in order_line:
            res.append(
                       {'product_name':i.product_id and i.product_id.name or False,
                       'uom_name':i.product_uom_id and i.product_uom_id.name or False,
                       'product_ean':i.product_id and i.product_id.barcode,
                       'default_code':i.product_id and i.product_id.default_code or False,
                       
                       'sys_qty':i.theoretical_qty or 0,
                       'product_qty':i.product_qty or 0,
                       'adjust_quantity':i.adjust_quantity or 0,
                       
                       'sys_value': round(i['theoretical_qty'] * i['freeze_cost'],0),
                       'count_value': round(i['freeze_cost'] * i['product_qty'],0),
                       'adjust_value': round(i['freeze_cost'] * (i['product_qty']  - i['theoretical_qty']),0),
                       'percent': i['product_qty'] and  i['adjust_quantity'] * 100 / i['product_qty'] or 0
                       })
            
            self.sum_system_value += round(i['theoretical_qty'] * i['freeze_cost'],0)
            self.sum_count_value  += round(i['freeze_cost'] * i['product_qty'],0)
            self.sum_adjust_value += round(i['freeze_cost'] * (i['product_qty']  - i['theoretical_qty']),0)
            sum_adjust_qty += i['adjust_quantity']
            sum_count_qty  += i['product_qty']
        self.sum_percent  = sum_count_qty and (sum_adjust_qty* 100 / sum_count_qty) or 0 
        
        return res
    
    def get_sum_percent(self):
        return self.sum_percent
    
    def get_sum_system_value(self):
        return self.sum_system_value
    
    def get_sum_count_value(self):
        return self.sum_count_value
    
    def get_sum_adjust_value(self):
        return self.sum_adjust_value
    
   
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
