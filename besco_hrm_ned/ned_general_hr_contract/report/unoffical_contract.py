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
        self.employee_ids = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_company_name': self.get_company_name,
            'get_company_address': self.get_company_address,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'get_partner_address': self.get_partner_address,
            'get_employee_ids': self.get_employee_ids,
            'get_employee_id': self.get_employee_id,
            'get_employee_address': self.get_employee_address
        })
    
    def get_employee_ids(self):
        res = []
        if not self.employee_ids:
            self.get_header()
        for i in self.employee_ids:
#           hr_contract_obj = self.env['hr.contract'].search([('employee_id', '=', i)])
            hr_contract_pool = self.pool.get('hr.contract')
            hr_contract_ids = hr_contract_pool.search(self.cr, self.uid, [('employee_id', '=', i)])
            hr_contract_obj = hr_contract_pool.browse(self.cr, self.uid, hr_contract_ids[0])
            res.append({'employee_code':hr_contract_obj.employee_id.code,
                        'employee_name': hr_contract_obj.employee_id.name,
                        'employee_nation':hr_contract_obj.employee_id.country_id.name,
                        'birthday': hr_contract_obj.employee_id.birthday,
                        'address_id': hr_contract_obj.employee_id.address_home_id,
                        'identification_id': hr_contract_obj.employee_id.identification_id,
                        'id_date_issue': hr_contract_obj.employee_id.identification_date_issue,
                        'id_place_issue': hr_contract_obj.employee_id.identification_place_issue,
                        'contract_type': hr_contract_obj.type_id.name,
                        'date_start': hr_contract_obj.date_start,
                        'date_end': hr_contract_obj.date_end,
                        'work_address_id': hr_contract_obj.job_id.address_id,
                        'job_name': hr_contract_obj.job_id.name,
                        'trial_date_start': hr_contract_obj.trial_date_start,
                        'trial_date_end': hr_contract_obj.trial_date_end,
                        'wage': hr_contract_obj.wage
                        })
        return res
    
    def get_employee_id(self):
        a = self.get_employee_ids()[0]
        return a
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.employee_ids = wizard_data['employee_ids']
        return True
    
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
        
    def get_company_address(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.street
    
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
    
    def get_employee_address(self, employee_id):
        address = ''
        if employee_id:
            address += employee_id.permanent_street or ''
            address += employee_id.permanent_ward_id and ', ' + employee_id.permanent_ward_id.name or ''
            address += employee_id.permanent_district_id and ', ' + employee_id.permanent_district_id.name or ''
            address += employee_id.permanent_state_id and ', ' + employee_id.permanent_state_id.name or ''
            address += employee_id.permanent_country_id and ', ' + employee_id.permanent_country_id.name or ''
        return address
    
    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.website
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
