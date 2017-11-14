# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
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
        self.type = False
        self.localcontext.update({
            #'roman_numberal': self.roman_numberal,
            'get_line':self.get_line,
            'get_date':self.get_date,
            'get_another_value': self.get_another_value,
            'get_contract_value': self.get_contract_value
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.type = wizard_data['type'] and wizard_data['type'][1] or False
    
    def get_date(self, date):
        if not date:
            return False
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    
    def get_line(self):
        emp_ids = []
        sql ='''
            SELECT id from hr_employee ORDER BY code
        '''
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            emp_ids.append(line['id'])
        
        return self.pool.get('hr.employee').browse(self.cr,self.uid,emp_ids)
    
    def get_contract_value(self, emp_obj):
#         emp_obj = self.pool.get('hr.employee').browse(cr, uid, emp_id)
        check_68z = self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_68z")
        check_76z = self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_76z")
        net = reduction_dependents = reduction_yourself = sum_reduction_dependents = social_insurance = pit = gross_salary = taxable_salary = False
        bhxh = bhyt = bhtn = kpcd = bhxh_co = bhyt_co = bhtn_co = kpcd_co = False
        if check_76z: 
            contract_ids = self.pool.get('hr.contract').search(self.cr, self.uid, [('employee_id', '=', emp_obj.id),('state', 'in', ('trial','open')),('employee_id.insurance_code_id.name','=','TZ0076Z')])
        else: 
            contract_ids = self.pool.get('hr.contract').search(self.cr, self.uid, [('employee_id', '=', emp_obj.id),('state', 'in', ('trial','open'))])
        if contract_ids:
            contract_ids = contract_ids[0]
            contract_obj = self.pool.get('hr.contract').browse(self.cr,self.uid,contract_ids)
            net = contract_obj.wage
            reduction_dependents = contract_obj.structure_id.reduction_dependents
            reduction_yourself = contract_obj.structure_id.reduction_yourself
            sum_reduction_dependents = reduction_dependents * emp_obj.dependant_of_taxpayer + reduction_yourself
            social_insurance = contract_obj.social_insurance
            pit = contract_obj.pit
            gross_salary = contract_obj.gross_salary
            taxable_salary = contract_obj.taxable_salary
            for i in contract_obj.insurance_ids:
                if i.insurance_laborer_id.code == 'BHXH':
                    bhxh = i.of_laborer
                if i.insurance_laborer_id.code == 'BHYT':
                    bhyt = i.of_laborer
                if i.insurance_laborer_id.code == 'BHTN':
                    bhtn = i.of_laborer
                if i.insurance_laborer_id.code == 'KPCD':
                    kpcd = i.of_laborer
                if i.insurance_company_id.code == 'BHXH_COMP':
                    bhxh_co = i.of_company
                if i.insurance_company_id.code == 'BHYT_COMP':
                    bhyt_co = i.of_company
                if i.insurance_company_id.code == 'BHTN_COMP':
                    bhtn_co = i.of_company
                if i.insurance_company_id.code == 'KPCD_COMP':
                    kpcd_co = i.of_company
            
        return {'net': net,
                'gross_salary': gross_salary,
                'reduction_dependents': reduction_dependents,
                'reduction_yourself': reduction_yourself,
                'sum_reduction_dependents': sum_reduction_dependents,
                'social_insurance': social_insurance,
                'pit': pit,
                'gross_salary': gross_salary,
                'taxable_salary': taxable_salary,
                'bhxh': bhxh,
                'bhyt': bhyt,
                'bhtn': bhtn,
                'kpcd': kpcd,
                'sum_bh': bhxh + bhyt + bhtn + kpcd,
                'bhxh_co': bhxh_co,
                'bhyt_co': bhyt_co,
                'bhtn_co': bhtn_co,
                'kpcd_co': kpcd_co,
                'sum_bh_co': bhxh_co + bhyt_co + bhtn_co + kpcd_co,
                }
    
    def get_another_value(self, emp_obj):
#         emp_obj = self.pool.get('hr.employee').browse(cr, uid, emp_id)
        gender = marital = ''
        if emp_obj.gender == 'male':
            gender = u'Nam'
        if emp_obj.gender == 'female':
            gender = u'Nữ'
        if emp_obj.gender == 'other':
            gender = u'Khác'
        if emp_obj.marital == 'single':
            marital = u'Độc thân'
        if emp_obj.marital == 'married':
            marital = u'Đã kết hôn'
        if emp_obj.marital == 'widower':
            marital = u'Đơn thân'
        if emp_obj.marital == 'divorced':
            marital = u'Đã Ly dị'
        return {'gender': gender,
                'marital': marital,
                }