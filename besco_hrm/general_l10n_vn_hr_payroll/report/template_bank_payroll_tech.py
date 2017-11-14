# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
from unittest import result
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
        self.company_address = False
        self.sum_money_officier = 0.0
        self.sum_tu_officier = 0.0
        self.sum_money_receipt_officier = 0.0
        self.sum_money_worker = 0.0
        self.sum_tu_worker = 0.0
        self.sum_money_receipt_worker = 0.0
        self.localcontext.update({
#             'khongdau': self.khongdau,
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_month_year': self.get_month_year,
            'get_total': self.get_total,
            'get_sum': self.get_sum,
            'get_info_worker': self.get_info_worker,
            'get_info_officier': self.get_info_officier,
            'get_info_manager': self.get_info_manager,
            'get_payslip_line': self.get_payslip_line,
            'get_overtime': self.get_overtime,
            'get_holidays': self.get_holidays,
            'get_work100': self.get_work100,
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.type_report = wizard_data['type_report']
        self.date_from = wizard_data['date_from']
        self.date_to = wizard_data['date_to']
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
        return date.strftime('%d-%m-%Y')
    
    def get_work100(self, worked_days_line_ids):
        for i in worked_days_line_ids:
            if i.code == 'WORK100':
                return {'day': i.number_of_days,
                        'hour': i.number_of_hours}
    
    def get_overtime(self, obj):
        rate_150 = rate_200 = rate_300 = 0
        for i in obj.overtime_ids:
            if i.rate == 150.00:
                rate_150 += i.number_of_hours
            if i.rate == 200.00:
                rate_200 += i.number_of_hours
            if i.rate == 400.00:
                rate_300 += i.number_of_hours
        work100 = self.get_work100(obj.worked_days_line_ids)['day'] if self.get_work100(obj.worked_days_line_ids) else 0.0
        if work100 == 0.0:
            return {'rate_150': rate_150,
                    'total_150': 0.0,
                    'rate_200': rate_200,
                    'total_200': 0.0,
                    'rate_300': rate_300,
                    'total_300': 0.0,}
        else:
            return {'rate_150': rate_150,
                    'total_150': rate_150 * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day']/8*1.5,
                    'rate_200': rate_200,
                    'total_200': rate_200 * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day']/8*2,
                    'rate_300': rate_300,
                    'total_300': rate_300 * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day']/8*3,}
    def get_holidays(self, obj):
        quantity_paid = quantity_unpaid = 0
        for i in obj.worked_days_line_ids:
            if i.code == 'paid':
                quantity_paid += i.number_of_days
            if i.code == 'un-paid':
                quantity_unpaid += i.number_of_days
        work100 = self.get_work100(obj.worked_days_line_ids)['day'] if self.get_work100(obj.worked_days_line_ids) else 0.0
        if work100 == 0.0:
            return {'quantity_paid': quantity_paid,
                    'total_paid': 0.0,
                    'quantity_unpaid': quantity_unpaid,
                    'total_unpaid': 0.0,}
        else:
            return {'quantity_paid': quantity_paid,
                    'total_paid': quantity_paid * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day'],
                    'quantity_unpaid': quantity_unpaid,
                    'total_unpaid': quantity_unpaid * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day'],}
        
    def get_sum(self):
        res = []
        return {'money_officier': self.sum_money_officier,
                'tu_officier': self.sum_tu_officier,
                'money_receipt_officier': self.sum_money_receipt_officier,
                'money_worker': self.sum_money_worker,
                'tu_worker': self.sum_tu_worker,
                'money_receipt_worker': self.sum_money_receipt_worker,
                }
    
    def get_payslip_line(self, obj):
        tu = ns = total_ns = pc = tl = 0
        for i in obj.line_ids:
            if i.code == 'TU':
                tu += i.total
            if i.code == 'NS':
                ns += i.amount
                total_ns += i.total
            if i.code == 'BDKTT':
                pc += i.total
            if i.code == 'TL':
                tl += i.total
        return {'tu': tu,
                'ns': ns,
                'total_ns': total_ns,
                'pc': pc,
                'tl':tl}
        
    def get_total(self, obj):
        wage = obj.contract_id.wage
        total_150 = self.get_overtime(obj)['total_150']
        total_200 = self.get_overtime(obj)['total_200']
        total_300 = self.get_overtime(obj)['total_300']
        total_paid = self.get_holidays(obj)['total_paid']
        total_unpaid = self.get_holidays(obj)['total_unpaid']
        return wage + total_150 + total_200 + total_300 +total_paid + total_unpaid
    
    def get_month_year(self):
        self.get_header()
        return self.get_vietname_date(self.date_to)
    
    def get_info_manager(self):
        self.get_header()
        
        # payslip_structure_pool = self.pool.get('hr.payroll.structure')
        # payslip_structure_ids = False
#         if self.type_report == 'officier':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNNVVP')])
#         elif self.type_report == 'worker':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNCN')])


        res = []
        payslip_ids_sql = ''
        if self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_68z"):
            payslip_ids_sql = """select distinct hr_payslip.id FROM hr_payslip, hr_employee, insurance_code, hr_contract,resource_calendar
                                WHERE hr_payslip.employee_id = hr_employee.id AND hr_employee.insurance_code_id = insurance_code.id AND insurance_code.name = 'TZ0068Z'
                                AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s' 
                                AND hr_payslip.employee_id = hr_contract.employee_id AND hr_contract.working_hours = resource_calendar.id AND resource_calendar.unskilled_worker is not True""" % (self.date_from, self.date_to)
#         else:
#             payslip_ids_sql = """select distinct id FROM hr_payslip
#                                 WHERE to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s' 
#                                 AND struct_id = %s""" % (self.date_from, self.date_to, payslip_structure_ids[0])
            self.cr.execute(payslip_ids_sql)
            payslip_pool = self.pool.get('hr.payslip')
            for payslip_id in self.cr.fetchall():
                payslip_obj = payslip_pool.browse(self.cr, self.uid, payslip_id[0])
                res.append({'employee_name': payslip_obj.employee_id.name_related,
                            'bank_number': payslip_obj.employee_id.bank_account_id.acc_number,
                            'bank': payslip_obj.employee_id.bank_account_id.bank_id.name + ' - ' + payslip_obj.employee_id.bank_account_id.bank_id.bic or False,
                            'money':self.get_payslip_line(payslip_obj)['tl'] - self.get_payslip_line(payslip_obj)['tu'],
                            'tu': self.get_payslip_line(payslip_obj)['tu'] * (-1),
                            'money_receipt': self.get_payslip_line(payslip_obj)['tl'],
                            })
                self.sum_money_officier += self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc']
                self.sum_tu_officier += self.get_payslip_line(payslip_obj)['tu'] * (-1)
                self.sum_money_receipt_officier += self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc'] - self.get_payslip_line(payslip_obj)['tu']
        return res
    
    def get_info_officier(self):
        self.get_header()
        
        # payslip_structure_pool = self.pool.get('hr.payroll.structure')
        # payslip_structure_ids = False
#         if self.type_report == 'officier':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNNVVP')])
#         elif self.type_report == 'worker':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNCN')])
        
        res = []
        payslip_ids_sql = ''
        if self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_76z"):
            payslip_ids_sql = """select distinct hr_payslip.id FROM hr_payslip, hr_employee, insurance_code, hr_contract,resource_calendar
                                WHERE hr_payslip.employee_id = hr_employee.id AND hr_employee.insurance_code_id = insurance_code.id AND insurance_code.name = 'TZ0076Z'
                                AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s' 
                                AND hr_payslip.employee_id = hr_contract.employee_id AND hr_contract.working_hours = resource_calendar.id AND resource_calendar.unskilled_worker is not True""" % (self.date_from, self.date_to)
        else:
            payslip_ids_sql = """select distinct hr_payslip.id FROM hr_payslip, hr_employee, hr_contract,resource_calendar
                                            WHERE hr_payslip.employee_id = hr_employee.id
                                            AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s'
                                            AND hr_payslip.employee_id = hr_contract.employee_id AND hr_contract.working_hours = resource_calendar.id AND resource_calendar.unskilled_worker is not True""" % (self.date_from, self.date_to)
        self.cr.execute(payslip_ids_sql)
        payslip_pool = self.pool.get('hr.payslip')
        for payslip_id in self.cr.fetchall():
            payslip_obj = payslip_pool.browse(self.cr, self.uid, payslip_id[0])
            bank_name = payslip_obj.employee_id.bank_account_id.bank_id.name
            bank_bic= payslip_obj.employee_id.bank_account_id.bank_id.bic
            if not bank_name:
                bank_name = ''
            if not bank_bic:
                bank_bic =''
            res.append({'employee_name': payslip_obj.employee_id.name_related,
                        'bank_number': payslip_obj.employee_id.bank_account_id.acc_number,
                        'bank': bank_name + ' - ' + bank_bic or False,
                        'money':self.get_payslip_line(payslip_obj)['tl'] - self.get_payslip_line(payslip_obj)['tu'],
                        'tu': self.get_payslip_line(payslip_obj)['tu'] * (-1),
                        'money_receipt': self.get_payslip_line(payslip_obj)['tl'],
                        })
            self.sum_money_officier += self.get_payslip_line(payslip_obj)['tl']
            self.sum_tu_officier += self.get_payslip_line(payslip_obj)['tu'] * (-1)
            self.sum_money_receipt_officier += self.get_payslip_line(payslip_obj)['tl'] - self.get_payslip_line(payslip_obj)['tu']
        return res 
    
    def get_info_worker(self):
        self.get_header()
        
        # payslip_structure_pool = self.pool.get('hr.payroll.structure')
        # payslip_structure_ids = False
#         if self.type_report == 'officier':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNNVVP')])
#         elif self.type_report == 'worker':
#         payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNCN')])
        
        res = []
        payslip_ids_sql = ''
        if self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_76z"):
            payslip_ids_sql = """select distinct hr_payslip.id FROM hr_payslip, hr_employee, insurance_code, hr_contract,resource_calendar
                                WHERE hr_payslip.employee_id = hr_employee.id AND hr_employee.insurance_code_id = insurance_code.id AND insurance_code.name = 'TZ0076Z'
                                AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s'
                                AND hr_payslip.employee_id = hr_contract.employee_id AND hr_contract.working_hours = resource_calendar.id AND resource_calendar.unskilled_worker = True""" % (self.date_from, self.date_to)
        else:
            payslip_ids_sql = """select distinct hr_payslip.id FROM hr_payslip, hr_employee, hr_contract,resource_calendar
                                            WHERE hr_payslip.employee_id = hr_employee.id
                                            AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s'
                                            AND hr_payslip.employee_id = hr_contract.employee_id AND hr_contract.working_hours = resource_calendar.id AND resource_calendar.unskilled_worker = True""" % (self.date_from, self.date_to)
        self.cr.execute(payslip_ids_sql)
        payslip_pool = self.pool.get('hr.payslip')
        for payslip_id in self.cr.fetchall():
            payslip_obj = payslip_pool.browse(self.cr, self.uid, payslip_id[0])
            if payslip_obj.employee_id.bank_account_id.bank_id.name == 'Techcombank':
                bank_name = payslip_obj.employee_id.bank_account_id.bank_id.name
                bank_bic= payslip_obj.employee_id.bank_account_id.bank_id.bic
                if not bank_name:
                    bank_name = ''
                if not bank_bic:
                    bank_bic =''
                res.append({'employee_name': payslip_obj.employee_id.name_related,
                            'bank_number': payslip_obj.employee_id.bank_account_id.acc_number,
                            'bank': bank_name + ' - ' + bank_bic or False,
                            'money':self.get_payslip_line(payslip_obj)['tl'] - self.get_payslip_line(payslip_obj)['tu'],
                            'tu': self.get_payslip_line(payslip_obj)['tu'] * (-1),
                            'money_receipt': self.get_payslip_line(payslip_obj)['tl'],
                            })
                self.sum_money_worker += self.get_payslip_line(payslip_obj)['tl'] - self.get_payslip_line(payslip_obj)['tu']
                self.sum_tu_worker += self.get_payslip_line(payslip_obj)['tu'] * (-1)
                self.sum_money_receipt_worker += self.get_payslip_line(payslip_obj)['tl']
        return res 
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
