# -*- coding: utf-8 -*-
##############################################################################
#
#    HLVSolution, Open Source Management Solution
#
##############################################################################



from report import report_sxw
import pooler
from osv import osv
from tools.translate import _
import random
import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        pool = pooler.get_pool(self.cr.dbname)
        res_user_obj = pool.get('res.users').browse(cr, uid, uid)
        self.company_name = False
        self.company_address = False
        self.get_company(cr, uid)
        self.res_name = False
        self.from_date = False
        self.to_date = False
        self.shop_id = False
        self.shop_name = False
        self.categ_id = False
        self.categ_name = False
        self.customer_id = False
        self.customer_name = False
        self.localcontext.update({
            'dated': time.strftime('%d %b %Y'),
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime': self.get_vietname_datetime,
            'get_company': self.get_company,
            'get_categ_name': self.get_categ_name,
            'get_from_date': self.get_from_date,
            'get_to_date': self.get_to_date,
            'get_shop_name': self.get_shop_name,
            'get_customer_name': self.get_customer_name,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_current_date': self.get_current_date,
        })

    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.from_date = wizard_data['from_date']
        self.to_date = wizard_data['to_date']
        self.shop_id = wizard_data['shop_id'] and wizard_data['shop_id'][0] or False
        self.shop_name = wizard_data['shop_id'] and wizard_data['shop_id'][1] or False
        self.categ_id = wizard_data['categ_id'] and wizard_data['categ_id'][0] or False
        self.categ_name = wizard_data['categ_id'] and wizard_data['categ_id'][1] or False
        self.customer_id = wizard_data['customer_id'] and wizard_data['customer_id'][0] or False
        self.customer_name = wizard_data['customer_id'] and wizard_data['customer_id'][1] or False
        return True
    
    def get_current_date(self):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
        
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_company(self,cr,uid):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
        
    def get_company_name(self):
        return self.company_name
    
    def get_company_address(self):
        return self.company_address 
    
    def get_categ_name(self):
        if not self.categ_name: 
            res = u'Tất cả'
        else:
            res = self.categ_name
        return res
    
    def get_from_date(self):
        if not self.from_date:
            self.get_header()
        return self.from_date
    
    def get_to_date(self):
        if not self.to_date:
            self.get_header()
        return self.to_date
    
    def get_shop_name(self):
        if not self.shop_name: 
            self.get_header()
        return self.shop_name
    
    def get_customer_name(self):
        if not self.categ_name:
            res = u'Tất cả'
        else:
            res = self.customer_name
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
