# -*- coding: utf-8 -*-
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
        self.start_date = False
        self.end_date = False
        self.type = False
        
        self.company_name = False
        self.company_address = False
        self.vat = False
        self.gross_value =  False
        self.depreciation_value =  False
        self.acc_depreciation =  False
        self.remaining_value =  False
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            'get_line':self.get_line,
            'get_name_values':self.get_name_values,
            'get_gross_value':self.get_gross_value,
            'get_depreciation_value':self.get_depreciation_value,
            'get_acc_depreciation':self.get_acc_depreciation,
            'get_remaining_value':self.get_remaining_value,
            
        })
    
    
    def get_company(self, company_id):
        if company_id:
            company_obj = self.pool.get('res.company').browse(self.cr, self.uid, company_id)
            self.company_name = company_obj.name or ''
            self.company_address = company_obj.street or ''
            self.vat = company_obj.vat or ''
        return True
             
    def get_company_name(self):
        self.get_header()
        return self.company_name
    
    def get_company_address(self):
        return self.company_address     
    
    def get_company_vat(self):
        return self.vat 
    
    def get_name_values(self):
        if self.type == 'short term':
            return  u'BẢNG PHÂN BỔ CHI PHÍ TRẢ TRƯỚC NGẮN HẠN'
        else:
            return u'BẢNG PHÂN BỔ CHI PHÍ TRẢ TRƯỚC DÀI HẠN'
        
    def get_quarter_date(self,year,quarter):
        self.start_date = False
        self.end_date  = False
        if quarter == '1':
            self.start_date = '''%s-01-01'''%(year)
            self.end_date = year + '-03-31'
        elif quarter == '2':
            self.start_date = year+'-04-01'
            self.end_date =year+'-06-30'
        elif quarter == '3':
            self.start_date = year+'-07-01'
            self.end_date = year+'-09-30'
        else:
            self.start_date = year+'-10-01'
            self.end_date = year+'-12-31'
          
    
    def get_id(self,get_id):
        wizard_data = self.localcontext['data']['form']
        period_id = wizard_data[get_id][0] or wizard_data[get_id][0] or False
        if not period_id:
            return 1
        else:
            return period_id
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        user_obj = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        self.get_company(user_obj.company_id.id or False)
        self.times = wizard_data['times']
        if self.times =='periods':
            self.start_date = self.pool.get('account.period').browse(self.cr,self.uid,self.get_id('period_id_start')).date_start
            self.end_date   = self.pool.get('account.period').browse(self.cr,self.uid,self.get_id('period_id_start')).date_stop
        elif self.times == 'dates':
            self.start_date = wizard_data['date_start']
            self.end_date   = wizard_data['date_end']
        
        elif self.times == 'years':
            self.start_date = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).date_start
            self.end_date   = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).date_stop
            
        else:
            quarter = wizard_data['quarter'] or False
            year = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).name
            self.get_quarter_date(year, quarter)
            
        self.type = wizard_data['type']
    
    def get_start_date(self):
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_line(self):
        res = self.pool.get('sql.expense.allocation').get_line(self.cr, self.start_date,self.end_date,self.type)
        return res
        
    def get_gross_value(self):
        if not self.gross_value:
            self.get_sum_line()
        return self.gross_value
    
    def get_depreciation_value(self):
        if not self.depreciation_value:
            self.get_sum_line()
        return self.depreciation_value
    
    def get_acc_depreciation(self):
        if not self.acc_depreciation:
            self.get_sum_line()
        return self.acc_depreciation
    
    def get_remaining_value(self):
        if not self.remaining_value:
            self.get_sum_line()
        return self.remaining_value
    
    
    def get_sum_line(self):
        res = self.pool.get('sql.expense.allocation').get_sum_line(self.cr, self.start_date,self.end_date,self.type)
        for line in res:
            self.gross_value = line['gross_value'] or False
            self.depreciation_value = line['depreciation_value'] or False
            self.acc_depreciation = line['acc_depreciation'] or False
            self.remaining_value = line['remaining_value'] or False
    
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
