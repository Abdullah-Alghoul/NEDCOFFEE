# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
from duplicity.errors import UserError
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import calendar
from datetime import datetime

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
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_company_name': self.get_company_name,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'get_partner_address': self.get_partner_address,
            'calculate_monthdelta': self.calculate_monthdelta,
            'insurance_contribution': self.insurance_contribution
        })
    
    
    def insurance_contribution(self,contract_id):
        res = []
        contract_insurance_pool = self.pool.get('hr.contract.insurance')
        contract_insurance_ids = contract_insurance_pool.search(self.cr,self.uid,[('contract_id','=',contract_id)])
        if not contract_insurance_ids:
            raise UserError('Contract has not insurance yet')
        for contract_insurance_id in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,contract_insurance_id)
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHXH' :
                social_insurance_id = contract_insurance_id
                res.append({
                    'employee': contract_insurance_obj.of_laborer,
                    'employer': contract_insurance_obj.of_company
                })
        for contract_insurance_id in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,contract_insurance_id)
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHYT':
                social_insurance_id = contract_insurance_id
                res.append({
                    'employee': contract_insurance_obj.of_laborer,
                    'employer': contract_insurance_obj.of_company
                })
        for contract_insurance_id in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,contract_insurance_id)
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'BHTN':
                social_insurance_id = contract_insurance_id
                res.append({
                    'employee': contract_insurance_obj.of_laborer,
                    'employer': contract_insurance_obj.of_company
                })
        for contract_insurance_id in contract_insurance_ids:
            contract_insurance_obj = contract_insurance_pool.browse(self.cr,self.uid,contract_insurance_id)
            code = contract_insurance_obj.insurance_laborer_id.code
            if code == 'KPCD':
                social_insurance_id = contract_insurance_id
                res.append({
                    'employee': contract_insurance_obj.of_laborer,
                    'employer': contract_insurance_obj.of_company
                })
        return res
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
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
    
    def get_partner_address(self, partner_id):
        address = ''
        if partner_id:
            address += partner_id.street or ''
            address += partner_id.state_id and ', ' + partner_id.state_id.name or ''
            address += partner_id.country_id and ', ' + partner_id.country_id.name or ''
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
            

    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.website
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
