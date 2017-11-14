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
        self.date_from = False
        self.date_to = False
        self.code_type = False
        self.code = False
        self.sum_bhxh = False
        self.sum_bhyt = False
        self.wage_new_emp = False
        self.wage_ex_emp = False
        self.wage_up_emp = False
        self.wage_down_emp = False
        self.localcontext.update({
            'get_vietname_date': self.get_vietname_date,
            'get_vietname_datetime': self.get_vietname_datetime,
            'get_header': self.get_header,
            'get_new_employee': self.get_new_employee,
            'get_ex_employee': self.get_ex_employee,
            'get_wagedown_employee': self.get_wagedown_employee,
            'get_wageup_employee': self.get_wageup_employee,
            'total_wage': self.total_wage,
            'get_code': self.get_code,
            'get_sum_bhxh': self.get_sum_bhxh,
            "get_sum_bhyt": self.get_sum_bhyt,
            'get_wage_emp': self.get_wage_emp,
            'get_wage_change_emp': self.get_wage_change_emp
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.date_from = wizard_data['start_date']
        self.date_to = wizard_data['end_date']
        self.code = wizard_data['code_type']
        return True
    
    def get_code(self):
        if not self.code:
            self.get_header()
        return self.code[1:]
    
    def get_new_employee(self):
        if not self.date_from:
            self.get_header()
        res = []
        sql = '''SELECT DISTINCT hr.id FROM hr_employee hr, hr_contract ct
            WHERE hr.official_joining_date BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD')
            AND hr.insurance_code_id = '%s'
            AND ct.employee_id = hr.id AND ct.state in('open','close') ''' % (self.date_from, self.date_to, self.code[0])
        self.cr.execute(sql)
        employee_list = self.cr.fetchall()
        if employee_list:
            for employee in employee_list:
                sql = '''SELECT MAX(id) FROM hr_contract WHERE employee_id = %s''' % employee
                self.cr.execute(sql)
                contract_id = self.cr.fetchone()
                if contract_id:
                    emp_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, employee)
                    
                    contract_obj = self.pool.get('hr.contract').browse(self.cr, self.uid, contract_id)
                    res.append({
                        'name' : emp_obj.name,
                        'insurance_number' : emp_obj.insurance_number,
                        'job' : emp_obj.job_id.name_vn,
                        'wage' : contract_obj.gross_salary,
                        'date_from' : emp_obj.official_joining_date,
                    })
                    self.wage_new_emp += contract_obj.gross_salary
                    if emp_obj.insurance_number:
                        self.sum_bhyt += 1
                    else:
                        self.sum_bhxh += 1
        return res
    
    def get_sum_bhyt(self):
        if self.sum_bhyt == 0:
            return 0
        return self.sum_bhyt
    
    def get_sum_bhxh(self):
        if self.sum_bhxh == 0:
            return 0
        return self.sum_bhxh

    def get_wage_emp(self):
        return self.wage_new_emp 
    
    def get_wage_change_emp(self):
        return  self.wage_ex_emp
    
    def get_ex_employee(self):
        res = []
        sql = '''SELECT hr.id
            FROM hr_employee hr, hr_contract ct
            WHERE hr.resigned_date BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD') 
            AND hr.insurance_code_id = %s
            AND ct.employee_id = hr.id AND ct.state in('open','close')
                                '''% (self.date_from, self.date_to, self.code[0])
        self.cr.execute(sql)
        employee_list = self.cr.fetchall()
        if employee_list:
            for employee in employee_list:
                sql = '''SELECT MAX(id) FROM hr_contract WHERE employee_id = %s''' % employee
                self.cr.execute(sql)
                contract_id = self.cr.fetchone()
                if contract_id:
                    emp_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, employee)
                    contract_obj = self.pool.get('hr.contract').browse(self.cr, self.uid, contract_id)
                        
                    res.append({
                        'name' : emp_obj.name,
                        'insurance_number' : emp_obj.insurance_number,
                        'job' : emp_obj.job_id.name_vn,
                        'wage' : contract_obj.gross_salary,
                        'date_from' : emp_obj.resigned_date,
                    })
                    self.wage_ex_emp += contract_obj.gross_salary
        return res
    
    
    
    def get_wageup_employee(self):
        res = []
        sql = '''SELECT ct_his.id 
                        FROM hr_contract c,hr_employee e ,hr_contract_history ct_his
                        WHERE c.employee_id IN (
                        SELECT employee_id 
                        FROM hr_contract 
                        WHERE ct_his.date BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD'))
                        AND  c.employee_id = e.id
                        AND ct_his.contract_id= c.id
                        AND e.insurance_code_id = '%s'
                        AND ct_his.wage > wage_old
                        ''' % (self.date_from, self.date_to, self.code[0])
        self.cr.execute(sql)
        contract_ids = self.cr.fetchall()
        for contract_id in contract_ids:
            wage = 0
            contract_history_obj = self.pool.get('hr.contract.history').browse(self.cr, self.uid,contract_id)
            if contract_history_obj.wage == contract_history_obj.contract_id.wage:
                wage = contract_history_obj.contract_id.gross_salary
            else :
                wage =contract_history_obj.gross_salary_old
            res.append({
                'name' : contract_history_obj.contract_id.employee_id.name,
                'insurance_number' : contract_history_obj.contract_id.employee_id.insurance_number,
                'job' : contract_history_obj.contract_id.employee_id.job_id.name_vn,
                'wage' : wage,
                'date_from' : contract_history_obj.date,
            })
            self.wage_new_emp += wage
        return res
    
    def get_wagedown_employee(self):
        res = []
        sql = '''SELECT ct_his.id 
                        FROM hr_contract c,hr_employee e ,hr_contract_history ct_his
                        WHERE c.employee_id IN (
                        SELECT employee_id 
                        FROM hr_contract 
                        WHERE ct_his.date BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD'))
                        AND  c.employee_id = e.id
                        AND ct_his.contract_id= c.id
                        AND e.insurance_code_id = '%s'
                        AND ct_his.wage < wage_old
                        ''' % (self.date_from, self.date_to, self.code[0])
        self.cr.execute(sql)
        contract_ids = self.cr.fetchall()
        for contract_id in contract_ids:
            wage = 0
            contract_history_obj = self.pool.get('hr.contract.history').browse(self.cr, self.uid,contract_id)
            if contract_history_obj.wage == contract_history_obj.contract_id.wage:
                wage = contract_history_obj.contract_id.gross_salary
            else :
                wage =contract_history_obj.gross_salary_old
            res.append({
                'name' : contract_history_obj.contract_id.employee_id.name,
                'insurance_number' : contract_history_obj.contract_id.employee_id.insurance_number,
                'job' : contract_history_obj.contract_id.employee_id.job_id.name_vn,
                'wage' : wage,
                'date_from' : contract_history_obj.date,
            })
            self.wage_new_emp += wage
        return res
#     def get_wagedown_employee(self):
#         res = []
#         if not self.date_from:
#             self.get_header()
#         sql = '''
#             SELECT employee_id, id FROM hr_contract 
#                             WHERE(date_start IN (
#                                 SELECT (date_end +INTERVAL '1 day') 
#                                 FROM hr_contract_history
#                                 WHERE contract_id IN (
#                                     SELECT id 
#                                     FROM hr_contract 
#                                     WHERE state = 'close' AND employee_id IN (
#                                         SELECT employee_id 
#                                         FROM hr_contract 
#                                         WHERE date_start BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD'))))
#                                 AND employee_id IN (
#                                     SELECT employee_id 
#                                     FROM hr_contract 
#                                     WHERE date_start BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD'))
#                                 AND wage <  (
#                                     SELECT wage
#                                     FROM hr_contract_history
#                                     WHERE contract_id IN (
#                                         SELECT id 
#                                         FROM hr_contract 
#                                         WHERE state = 'close' AND employee_id IN (
#                                             SELECT employee_id 
#                                             FROM hr_contract 
#                                             WHERE date_start BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD')))))
#             '''%(self.date_from,self.date_to,self.date_from,self.date_to,self.date_from,self.date_to)
#         self.cr.execute(sql)
#         wageup_employee_list = self.cr.fetchall()
#         if wageup_employee_list:
#             for wageup_employee in wageup_employee_list:
#                 emp_obj = self.pool.get('hr.employee').browse(self.cr,self.uid,wageup_employee[0])
#                 contract_obj = self.pool.get('hr.contract').browse(self.cr,self.uid,wageup_employee[1])
#                 res.append({
#                     'name' : emp_obj.name,
#                     'insurance_number' : emp_obj.insurance_number,
#                     'job' : emp_obj.job_id.name,
#                     'wage' : contract_obj.wage,
#                     'date_from' : contract_obj.date_start,
#                 })
#         return res

    
    def total_wage(self, res):
        total = 0
        for item in res:
            total += item['wage']
        return total
    
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
    
