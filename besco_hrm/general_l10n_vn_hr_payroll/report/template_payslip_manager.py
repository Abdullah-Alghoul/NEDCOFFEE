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
        self.type_report = False
        self.date_from = False
        self.date_to = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_company': self.get_company,
            'get_company_address': self.get_company_address,
            'get_company_name': self.get_company_name,
            'get_work100': self.get_work100,
            'get_overtime': self.get_overtime,
            'get_holidays': self.get_holidays,
            'get_payslip_line': self.get_payslip_line,
            'get_total': self.get_total,
            'get_payslips': self.get_payslips,
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
        return date.strftime('%d-%m-%Y')
     
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
#     
    def get_company(self):
        user_obj = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
          
    def get_company_name(self):
        self.get_company()
        return self.company_name
     
    def get_company_address(self):
        self.get_company()
        return self.company_address
     
    def get_company_phone(self):
        sql = "SELECT phone FROM res_company"
        self.cr.execute(sql)
        temp = self.cr.fetchone()
        return str(temp[0])
#     
    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.website
    
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
        if self.get_work100(obj.worked_days_line_ids)['day'] == 0.0:
            return {'rate_150': rate_150,
                    'total_150': 0.0,
                    'rate_200': rate_200,
                    'total_200': 0.0,
                    'rate_300': rate_300,
                    'total_300': 0.0,}
        
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
        if self.get_work100(obj.worked_days_line_ids)['day'] == 0.0:
            return {'quantity_paid': quantity_paid,
                    'total_paid': 0.0,
                    'quantity_unpaid': quantity_unpaid,
                    'total_unpaid': 0.0,}
        return {'quantity_paid': quantity_paid,
                'total_paid': quantity_paid * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day'],
                'quantity_unpaid': quantity_unpaid,
                'total_unpaid': quantity_unpaid * obj.contract_id.wage/self.get_work100(obj.worked_days_line_ids)['day'],}
    
    def get_payslip_line(self, obj):
        tu = pc = 0
        for i in obj.line_ids:
            if i.code == 'TU':
                tu += i.total
            if i.code == 'BDKTT':
                pc += i.total
                
        return {'tu': tu,
                'pc': pc
                }
    
    def get_total(self, obj):
        wage = obj.contract_id.wage
        total_150 = self.get_overtime(obj)['total_150']
        total_200 = self.get_overtime(obj)['total_200']
        total_300 = self.get_overtime(obj)['total_300']
        total_paid = self.get_holidays(obj)['total_paid']
        total_unpaid = self.get_holidays(obj)['total_unpaid']
        return wage + total_150 + total_200 + total_300 +total_paid + total_unpaid
    
    def get_payslips(self):
        self.get_header()
        
        payslip_structure_pool = self.pool.get('hr.payroll.structure')
        payslip_structure_ids = False
#         if self.type_report == 'officier':
        payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNNVVP')])
#         elif self.type_report == 'worker':
#             payslip_structure_ids = payslip_structure_pool.search(self.cr, self.uid, [('code','=','VNCN')])
        
        res = []
        payslip_ids_sql=''
        if self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_68z"):
            payslip_ids_sql = """SELECT hr_payslip.id FROM hr_payslip, hr_employee, insurance_code 
                                WHERE hr_payslip.employee_id = hr_employee.id AND hr_employee.insurance_code_id = insurance_code.id AND insurance_code.name = 'TZ0068Z'
                                AND to_char(hr_payslip.date_from, 'YYYY-MM-DD') = '%s' AND to_char(hr_payslip.date_to, 'YYYY-MM-DD') = '%s' 
                                AND hr_payslip.struct_id = %s""" % (self.date_from, self.date_to, payslip_structure_ids[0])
        self.cr.execute(payslip_ids_sql)
        payslip_pool = self.pool.get('hr.payslip')
        for payslip_id in self.cr.fetchall():
            payslip_obj = payslip_pool.browse(self.cr, self.uid, payslip_id[0])
            if self.get_work100(payslip_obj.worked_days_line_ids)['day'] == 0.0:
                res.append({'employee_name': payslip_obj.employee_id.name_related,
                        'employee_code': payslip_obj.employee_id.code,
                        'get_work100': 0.0,
                        'contract_wage': payslip_obj.contract_id.wage,
                        'quy_doi_ngay': 0.0,
                        'quy_doi_gio': 0.0,
                        'date_from': self.get_vietname_date(self.date_from),
                        'date_to': self.get_vietname_date(self.date_to),
                        'job': payslip_obj.employee_id.job_id.name,
                        'joining_date': self.get_vietname_date(payslip_obj.employee_id.joining_date),
                        'ky_luong': self.get_vietname_date(self.date_from)[3:10],
                        'quantity_150': self.get_overtime(payslip_obj)['rate_150'],
                        'quantity_200': self.get_overtime(payslip_obj)['rate_200'],
                        'quantity_300': self.get_overtime(payslip_obj)['rate_300'],
                        'total_150': self.get_overtime(payslip_obj)['total_150'],
                        'total_200': self.get_overtime(payslip_obj)['total_200'],
                        'total_300': self.get_overtime(payslip_obj)['total_300'],
                        'quantity_paid': self.get_holidays(payslip_obj)['quantity_paid'],
                        'quantity_unpaid': self.get_holidays(payslip_obj)['quantity_unpaid'],
                        'total_paid': self.get_holidays(payslip_obj)['total_paid'],
                        'total_unpaid': self.get_holidays(payslip_obj)['total_unpaid'],
                        'unit_normal_ot': 0.0,
                        'unit_rest_ot': 0.0,
                        'unit_holiday_ot': 0.0,
                        'pc': self.get_payslip_line(payslip_obj)['pc'],
                        'tu': self.get_payslip_line(payslip_obj)['tu'] * (-1),
                        'get_total_disbured': self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc'],
                        'get_total': self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc'] - self.get_payslip_line(payslip_obj)['tu'],
                        })
            else:
                res.append({'employee_name': payslip_obj.employee_id.name_related,
                            'employee_code': payslip_obj.employee_id.code,
                            'get_work100': self.get_work100(payslip_obj.worked_days_line_ids)['day'],
                            'contract_wage': payslip_obj.contract_id.wage,
                            'quy_doi_ngay': payslip_obj.contract_id.wage/self.get_work100(payslip_obj.worked_days_line_ids)['day'],
                            'quy_doi_gio': payslip_obj.contract_id.wage/self.get_work100(payslip_obj.worked_days_line_ids)['day']/8,
                            'date_from': self.get_vietname_date(self.date_from),
                            'date_to': self.get_vietname_date(self.date_to),
                            'job': payslip_obj.employee_id.job_id.name,
                            'joining_date': self.get_vietname_date(payslip_obj.employee_id.joining_date),
                            'ky_luong': self.get_vietname_date(self.date_from)[3:10],
                            'quantity_150': self.get_overtime(payslip_obj)['rate_150'],
                            'quantity_200': self.get_overtime(payslip_obj)['rate_200'],
                            'quantity_300': self.get_overtime(payslip_obj)['rate_300'],
                            'total_150': self.get_overtime(payslip_obj)['total_150'],
                            'total_200': self.get_overtime(payslip_obj)['total_200'],
                            'total_300': self.get_overtime(payslip_obj)['total_300'],
                            'quantity_paid': self.get_holidays(payslip_obj)['quantity_paid'],
                            'quantity_unpaid': self.get_holidays(payslip_obj)['quantity_unpaid'],
                            'total_paid': self.get_holidays(payslip_obj)['total_paid'],
                            'total_unpaid': self.get_holidays(payslip_obj)['total_unpaid'],
                            'unit_normal_ot': payslip_obj.contract_id.wage/self.get_work100(payslip_obj.worked_days_line_ids)['day']/8*1.5,
                            'unit_rest_ot': payslip_obj.contract_id.wage/self.get_work100(payslip_obj.worked_days_line_ids)['day']/8*2,
                            'unit_holiday_ot': payslip_obj.contract_id.wage/self.get_work100(payslip_obj.worked_days_line_ids)['day']/8*4,
                            'pc': self.get_payslip_line(payslip_obj)['pc'],
                            'tu': self.get_payslip_line(payslip_obj)['tu'] * (-1),
                            'get_total_disbured': self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc'],
                            'get_total': self.get_total(payslip_obj) + self.get_payslip_line(payslip_obj)['pc'] - self.get_payslip_line(payslip_obj)['tu'],
                            })
        return res

        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
