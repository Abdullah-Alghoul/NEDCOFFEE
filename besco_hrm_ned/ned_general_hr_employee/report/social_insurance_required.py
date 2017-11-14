# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
logger = logging.getLogger('report_aeroo')
import string
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.employee_ids = False
        self.uid = uid
        self.lead_planned_revenue = 0.0
        self.opp_planned_revenue = 0.0
        self.total_order = 0.0
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_header':self.get_header,
            'get_vietname_gender': self.get_vietname_gender,
            'get_household_head_name': self.get_household_head_name,
            'get_household_head_phone': self.get_household_head_phone,
            'get_insurance_fee': self.get_insurance_fee,
        })
    
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
    
    def get_vietname_gender(self, gender):
        if gender == 'male':
            return u'Nam'
        if gender == 'female':
            return u'Nữ'
        if gender == 'other':
            return u'Khác'
    
    def get_household_head_name(self, employee_id):
        emp_dependent_obj = self.pool.get('hr.employee.dependent').search(self.cr, self.uid, [('employee_id','=',employee_id)])
        for line in self.pool.get('hr.employee.dependent').browse(self.cr, self.uid, emp_dependent_obj):
            if line.is_household_head == True:
                return line.name
    
    def get_household_head_phone(self, employee_id):
        emp_dependent_obj = self.pool.get('hr.employee.dependent').search(self.cr, self.uid, [('employee_id','=',employee_id)])
        for line in self.pool.get('hr.employee.dependent').browse(self.cr, self.uid, emp_dependent_obj):
            if line.is_household_head == True:
                return line.mobile
        
    def get_insurance_fee(self, employee_id):
        res = []
        total = 0
        sql = '''
            select (sum(ins.of_laborer) + sum(ins.of_company)) as total
            from hr_contract con, hr_contract_insurance ins, hr_employee emp
            where con.id = ins.contract_id and con.employee_id = emp.id and emp.id = %s
            and con.state = 'open'
        ''' % (employee_id)
        self.cr.execute(sql)
        total = self.cr.fetchone()
        for fee in total:
            return int(fee)
        
        
        
        
        
        
        
        
