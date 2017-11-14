# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.start_date = False
        self.end_date = False
        self.asset_types = []
        
        self.company_name = False
        self.company_address = False
        self.vat = False
        self.total_residual = False
        self.depreciation_value = False
        self.acc_depreciation = False
        self.remain_value = False
        
        self.data = {}
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            
            'get_date_type':self.get_date_type,
            
            'get_wh':self.get_wh,
            'get_dept': self.get_dept,
            'get_line':self.get_line,
            
            'get_depreciation_value':self.get_depreciation_value,
            'get_acc_depreciation':self.get_acc_depreciation,
            'get_remaining_value':self.get_remaining_value,
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
    
    def get_date_type(self):
        if self.date_type == 'depreciation_date':
            return u'Ngày khấu hao'
        if self.date_type == 'using_date':
            return u'Ngày đưa vào sử dụng'
        if self.date_type == 'purchase_date':
            return u'Ngày mua'
        return '' 
    
    def get_company_vat(self):
        return self.vat
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        
        self.company_id = wizard_data['company_id'][0]
        self.start_date = wizard_data['date_start']
        self.end_date   = wizard_data['date_end']
        self.date_type = wizard_data['date_type']
        self.show_all = wizard_data['show_all']
        self.asset_types = (','.join(map(str, wizard_data['asset_category_ids'])))
        self.get_company()
        
        #THANH: Load all data
        res, depreciation_value, acc_depreciation, remain_value = self.pool.get('sql.depreciation.allocation').get_line(self.cr, self.date_type, self.show_all, self.start_date, self.end_date, self.asset_types, self.company_id)
        self.depreciation_value = depreciation_value
        self.acc_depreciation = acc_depreciation
        self.remain_value = remain_value
        self.data = res
        
    def get_start_date(self):
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    def get_convert_double(self,value):
        return float(value)
    
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
    
    def get_depreciation_value(self):
        return self.depreciation_value
    
    def get_acc_depreciation(self):
        return self.acc_depreciation
    
    def get_remaining_value(self):
        return self.remain_value
    
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
