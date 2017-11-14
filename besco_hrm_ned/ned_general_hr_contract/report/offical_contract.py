# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.exceptions import UserError

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
        self.localcontext.update({
            'get_vietname_date': self.get_vietname_date,
            'get_contract_date': self.get_contract_date,
            'get_vietname_datetime': self.get_vietname_datetime,
            'get_company_name': self.get_company_name,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'get_partner_address': self.get_partner_address,
            'calculate_monthdelta': self.calculate_monthdelta,
            'bhxh_of_laborer': self.bhxh_of_laborer,
            'bhxh_of_company': self.bhxh_of_company,
            'bhyt_of_laborer': self.bhyt_of_laborer,
            'bhyt_of_company': self.bhyt_of_company,
            'bhtn_of_laborer': self.bhtn_of_laborer,
            'bhtn_of_company': self.bhtn_of_company,
            'kpcd_of_laborer': self.kpcd_of_laborer,
            'kpcd_of_company': self.kpcd_of_company,
            'get_temp_address': self.get_temp_address,
            'get_resident_address': self.get_resident_address,
            'strip_accents': self.strip_accents,
            'get_contract_date_end': self.get_contract_date_end
            })
    def get_contract_date(self, date_start, trial_date_start):
        if date_start:
            return self.get_vietname_date(date_start)
        elif trial_date_start:
            return self.get_vietname_date(trial_date_start)  
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_contract_date_end(self, date):
        if not date:
            return False
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_company_name(self):
        sql = "SELECT name FROM res_company"
        self.cr.execute(sql)
        temp = self.cr.fetchone()
        return temp[0]
    
    def get_company_phone(self):
        sql = "SELECT phone FROM res_company"
        self.cr.execute(sql)
        temp = self.cr.fetchone()
        return str(temp[0])
    
    def strip_accents(self, name):
        return self.pool.get('wizard.export.payslips.bank').strip_accents(name) 
    
    def get_partner_address(self, partner_id):
        address = ''
        if partner_id:
            address += partner_id.street or ''
            address += partner_id.state_id and ', ' + partner_id.state_id.name or ''
            address += partner_id.country_id and ', ' + partner_id.country_id.name or ''
        return address
    
    def get_temp_address(self, partner_id):
        address = ''
        if partner_id:
            address += partner_id.temporary_street or ''
            address += partner_id.temporary_ward_id and ', ' + partner_id.temporary_ward_id.name or ''
            address += partner_id.temporary_district_id and ', ' + partner_id.temporary_district_id.name or ''
            address += partner_id.temporary_state_id and ', ' + partner_id.temporary_state_id.name or ''
            address += partner_id.temporary_country_id and ', ' + partner_id.temporary_country_id.name or ''
        return address
    
    def get_resident_address(self, partner_id):
        address = ''
        if partner_id:
            address += partner_id.permanent_street or ''
            address += partner_id.permanent_ward_id and ', ' + partner_id.permanent_ward_id.name or ''
            address += partner_id.permanent_district_id and ', ' + partner_id.permanent_district_id.name or ''
            address += partner_id.permanent_state_id and ', ' + partner_id.permanent_state_id.name or ''
            address += partner_id.permanent_country_id and ', ' + partner_id.permanent_country_id.name or ''
        return address
    
    
          
    def calculate_monthdelta(self, str1, str2):
        if str1 and str2:
            date1 = datetime.strptime(str1, "%Y-%m-%d")
            date2 = datetime.strptime(str2, "%Y-%m-%d")
            def is_last_day_of_the_month(date):
                days_in_month = calendar.monthrange(date.year, date.month)[1]
                return date.day == days_in_month
            imaginary_day_2 = 31 if is_last_day_of_the_month(date2) else date2.day
            monthdelta = (
                (date2.month - date1.month) + 
                (date2.year - date1.year) * 12 + 
                (-1 if date1.day > imaginary_day_2 else 0)
                )
        else:
            monthdelta = (
                u'Hợp đồng dài hạn'
                )
        return monthdelta
    
    def bhxh_of_laborer(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHXH':
                salary += contract_insurance_obj.of_laborer or 0
        return salary
    
    def bhxh_of_company(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHXH':
                salary += contract_insurance_obj.of_company or 0
        return salary
    
    def bhyt_of_laborer(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHYT':
                salary += contract_insurance_obj.of_laborer or 0
        return salary
    
    def bhyt_of_company(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHYT':
                salary += contract_insurance_obj.of_company or 0
        return salary
    
    def bhtn_of_laborer(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHTN':
                salary += contract_insurance_obj.of_laborer or 0
        return salary
    
    def bhtn_of_company(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHTN':
                salary += contract_insurance_obj.of_company or 0
        return salary
    
    def kpcd_of_laborer(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'KPCD':
                salary += contract_insurance_obj.of_laborer or 0
        return salary
    
    def kpcd_of_company(self, contract_id):
        salary = 0
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        if not contract_id:
            return salary
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            return salary
        
        for line in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,line )
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'KPCD':
                salary += contract_insurance_obj.of_company or 0
        return salary
    
    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.website
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
