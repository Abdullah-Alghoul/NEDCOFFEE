# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        #super(Parser, self).__init__(cr, uid, name, context=context)
        self.date_type = 'using_date'
        self.start_date = False
        self.end_date = False
        self.asset_types = []
        
        self.company_name = False
        self.company_address = False
        self.vat = False
        self.gross_value =  0.0
        self.value_of_month =  0.0
        
        self.data = {}
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            
            'get_wh':self.get_wh,
            'get_dept': self.get_dept,
            'get_line':self.get_line,
            
            'get_gross_value':self.get_gross_value,
            'get_value_of_month':self.get_value_of_month,
        })
    
    def get_company(self):
        if self.company_id:
            company_obj = self.pool.get('res.company').browse(self.cr, self.uid, self.company_id)
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
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.start_date = wizard_data['date_start']
        self.end_date = wizard_data['date_end']
        self.date_type = wizard_data['date_type']
        self.asset_types = (','.join(map(str, wizard_data['asset_category_ids'])))
        self.company_id = wizard_data['company_id'][0]
        self.get_company()
        
        #THANH: Load all data
        res, gross_value, value_of_month = self.pool.get('sql.list.of.asset').get_line(self.cr, self.date_type, self.start_date, self.end_date, self.asset_types, self.company_id)
        self.gross_value = gross_value
        self.value_of_month = value_of_month
        self.data = res
        
    def get_start_date(self):
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    def get_vietname_date(self, date):
        if not date:
            return ''
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
        
    def get_wh(self):
        wh = []
        for key, val in self.data.items():
            wh.append(key)
        return wh
    
    def get_dept(self, wh):
        dept = []
        for key, val in self.data.items():
            if key == wh:
                for dept_key, dept_vals in val.items():
                    dept.append(dept_key)
        return dept
    
    def get_line(self, wh, dept):
        return self.data[wh][dept]
    
    def get_gross_value(self):
        return self.gross_value
    
    def get_value_of_month(self):
        return self.value_of_month
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
