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
        self.start_date = False
        self.department_ids = False
        self.get_company(cr, uid)
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_company_name': self.get_company_name,
            'get_day_start_date': self.get_day_start_date,
            'get_month_start_date': self.get_month_start_date,
            'get_year_start_date': self.get_year_start_date,
            'get_day_end_date': self.get_day_end_date,
            'get_month_end_date': self.get_month_end_date,
            'get_year_end_date': self.get_year_end_date,
            'get_total_department': self.get_total_department,
            'get_payroll_department_line': self.get_payroll_department_line,
            'get_payroll_employee_line': self.get_payroll_employee_line,
            'check_none': self.check_none,
            'get_company_address': self.get_company_address,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'numbers_to_strings': self.numbers_to_strings,
            'get_value_rule_employee': self.get_value_rule_employee,
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.department_ids = wizard_data['department_ids']
        self.start_date = wizard_data['start_date']
        return True
    
    def get_day_start_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[8:10]
    
    def get_month_start_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[5:7]

    def get_year_start_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[0:4]
    
    def get_day_end_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[8:10]
    
    def get_month_end_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[5:7]

    def get_year_end_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date[0:4]
    
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
    
    def get_company(self, cr, uid):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
         
    def get_company_name(self):
        self.get_header()
        return self.company_name
    
    def get_company_address(self):
        return self.company_address
    
    def get_company_phone(self):
        sql = "SELECT phone FROM res_company"
        self.cr.execute(sql)
        temp = self.cr.fetchone()
        return str(temp[0])
    
    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr, self.uid, temp[0])
        return res_partner.website
    
    def get_total_department(self, department_id, code):
        month_now = self.get_month_start_date()
        year_now = self.get_year_start_date()
        self.cr.execute("""SELECT SUM(total) FROM hr_payslip_line, hr_payslip, hr_contract
                            WHERE hr_payslip_line.slip_id = hr_payslip.id
                            AND to_char(hr_payslip.create_date, 'YYYYMM') = '%s%s'
                            AND hr_contract.department_id = %s
                            AND hr_payslip.contract_id = hr_contract.id
                            AND code = '%s'""" % (year_now, month_now, department_id, code))
        
        value = self.cr.fetchone()
        return value
    
    def get_value_rule_employee(self, payslip_id, code):
        res = []
        self.cr.execute("""SELECT total FROM hr_payslip_line WHERE slip_id = %s AND code = '%s'""" % (payslip_id, code))
        temp = self.cr.fetchone()
        if not temp:
            res.append(temp)
            return res
        return temp
    
    def check_none(self, num):
        if not num:
            return 0.0
        if num < 0: 
            return num * (-1)
        return num
    
    def get_payrols(self):
        res = []
        self.start_date
        self.end_date
        res.append({'month':line['month'] or False,
                    'year':line['year'] or False, })
        return res
        
    def get_payroll_department_line(self):
        res = []
        dep_name = []
        month_now = str(datetime.now())[5:7]
        year_now = str(datetime.now())[0:4]
        sql = "SELECT id, name FROM hr_department"
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            dep_name.append({'id':line['id'] or False,
                             'dep_name':line['name'] or False, })
        for i in dep_name:
            PCCV = self.get_total_department(i['id'], 'PCCV')
            PCAU = self.get_total_department(i['id'], 'PCAU')
            PCDL = self.get_total_department(i['id'], 'PCDL')
            PCLTN = self.get_total_department(i['id'], 'PCLTN')
            PCDT = self.get_total_department(i['id'], 'PCDT')
            LG = self.get_total_department(i['id'], 'LG')
            LGTT = self.get_total_department(i['id'], 'LGTT')
            BHXH_COMP = self.get_total_department(i['id'], 'BHXH_COMP')
            BHYT_COMP = self.get_total_department(i['id'], 'BHYT_COMP')
            BHTN_COMP = self.get_total_department(i['id'], 'BHTN_COMP')
            KPCD_COMP = self.get_total_department(i['id'], 'KPCD_COMP')
            BHXH = self.get_total_department(i['id'], 'BHXH')
            BHYT = self.get_total_department(i['id'], 'BHYT')
            BHTN = self.get_total_department(i['id'], 'BHTN')
            TNCN = self.get_total_department(i['id'], 'TNCN5')
            TU = self.get_total_department(i['id'], 'TU')
             
            self.cr.execute("""SELECT SUM(other_wage) FROM hr_payslip, hr_contract
                                WHERE to_char(hr_payslip.create_date, 'YYYYMM') = '%s%s'
                                AND hr_contract.department_id = %s
                                AND hr_payslip.contract_id = hr_contract.id""" % (year_now, month_now, i['id']))
            OTHER_WAGE = self.cr.fetchone()
             
            self.cr.execute("""SELECT SUM(default_work_days) FROM hr_payslip, hr_contract
                                WHERE to_char(hr_payslip.create_date, 'YYYYMM') = '%s%s'
                                AND hr_contract.department_id = %s
                                AND hr_payslip.contract_id = hr_contract.id""" % (year_now, month_now, i['id']))
            WORK_DAY = self.cr.fetchone()
            a = self.check_none(BHXH_COMP[0]) + self.check_none(BHYT_COMP[0]) + self.check_none(BHTN_COMP[0]) + self.check_none(KPCD_COMP[0])
            res.append({'NAME' : i['dep_name'],
                        'DEP_ID': i['id'],
                        'WORK_DAY' : self.check_none(WORK_DAY[0]),
                        'OTHER_WAGE' : self.check_none(OTHER_WAGE[0]),
                        'PCAU' : float(self.check_none(PCAU[0])),
                        'PCDT' : self.check_none(PCDT[0]),
                        'PCDL' : self.check_none(PCDL[0]),
                        'PCCV' : self.check_none(PCCV[0]),
                        'PCLTN' : self.check_none(PCLTN[0]),
                        'SUM_PC' : self.check_none(PCAU[0]) + self.check_none(PCDT[0]) + self.check_none(PCDL[0]) + self.check_none(PCCV[0]) + self.check_none(PCLTN[0]),
                        'GOSS' : self.check_none(LG[0]),
                        'NET' : self.check_none(LGTT[0]),
                        'BHXH18_COMP' : self.check_none(BHXH_COMP[0]),
                        'BHYT3_COMP' : self.check_none(BHYT_COMP[0]),
                        'BHTN1_COMP' : self.check_none(BHTN_COMP[0]),
                        'KPCD_COMP' : self.check_none(KPCD_COMP[0]),
                        'SUM_CP': self.check_none(BHXH_COMP[0]) + self.check_none(BHYT_COMP[0]) + self.check_none(BHTN_COMP[0]) + self.check_none(KPCD_COMP[0]),
                        'BHXH8' : self.check_none(BHXH[0]),
                        'BHYT15' : self.check_none(BHYT[0]),
                        'BHTN1' : self.check_none(BHTN[0]),
                        'SUM_BH_BB' : self.check_none(BHXH[0]) + self.check_none(BHYT[0]) + self.check_none(BHTN[0]),
                        'THUE' : self.check_none(TNCN[0]),
                        'TAMUNG' : self.check_none(TU[0]),
                        'SUM_SUB' : self.check_none(BHXH[0]) + self.check_none(BHYT[0]) + self.check_none(BHTN[0]) + self.check_none(TNCN[0]) + self.check_none(TU[0]),
                        'THUC_LINH' : self.check_none(LGTT[0]) - self.check_none(BHXH[0]) + self.check_none(BHYT[0]) + self.check_none(BHTN[0]) + self.check_none(TNCN[0]) + self.check_none(TU[0]),
                        })
        return res
    
    def get_payroll_employee_line(self, dep_id):
        res = []
        month_now = str(datetime.now())[5:7]
        year_now = str(datetime.now())[0:4]
        payslip_ids_sql = """SELECT id FROM hr_payslip
                            WHERE to_char(hr_payslip.create_date, 'YYYYMM') = '%s%s'
                            AND hr_payslip.department_id = %s""" % (year_now, month_now, dep_id)
        self.cr.execute(payslip_ids_sql)
        payslip_pool = self.pool.get('hr.payslip')
        for payslip_id in self.cr.fetchall():
            payslip_obj = payslip_pool.browse(self.cr, self.uid, payslip_id[0])
            
            PCAU = self.get_value_rule_employee(payslip_id[0], 'PCAU')
            PCCV = self.get_value_rule_employee(payslip_id[0], 'PCCV')
            PCDL = self.get_value_rule_employee(payslip_id[0], 'PCDL')
            PCLTN = self.get_value_rule_employee(payslip_id[0], 'PCLTN')
            PCDT = self.get_value_rule_employee(payslip_id[0], 'PCDT')
            LG = self.get_value_rule_employee(payslip_id[0], 'LG')
            LGTT = self.get_value_rule_employee(payslip_id[0], 'LGTT')
            BHXH_COMP = self.get_value_rule_employee(payslip_id[0], 'BHXH_COMP')
            BHYT_COMP = self.get_value_rule_employee(payslip_id[0], 'BHYT_COMP')
            BHTN_COMP = self.get_value_rule_employee(payslip_id[0], 'BHTN_COMP')
            KPCD_COMP = self.get_value_rule_employee(payslip_id[0], 'KPCD_COMP')
            BHXH = self.get_value_rule_employee(payslip_id[0], 'BHXH')
            BHYT = self.get_value_rule_employee(payslip_id[0], 'BHYT')
            BHTN = self.get_value_rule_employee(payslip_id[0], 'BHTN')
            TNCN = self.get_value_rule_employee(payslip_id[0], 'TNCN5')
            TU = self.get_value_rule_employee(payslip_id[0], 'TU')

            print payslip_obj
            res.append({'EMP_NAME' : payslip_obj.employee_id.name,
                        'JOB' : payslip_obj.employee_id.job_id.name,
                        'WORK_DAY' : payslip_obj.default_work_days,
                        'OTHER_WAGE' : payslip_obj.contract_id.other_wage,
                        'PCAU' : float(self.check_none(PCAU[0])),
                        'PCDT' : float(self.check_none(PCDT[0])),
                        'PCDL' : float(self.check_none(PCDL[0])),
                        'PCCV' : float(self.check_none(PCCV[0])),
                        'PCLTN' : float(self.check_none(PCLTN[0])),
                        'SUM_PC' : float(self.check_none(PCAU[0])) + float(self.check_none(PCDT[0])) + float(self.check_none(PCDL[0])) + float(self.check_none(PCCV[0])) + float(self.check_none(PCLTN[0])),
                        'GOSS' : float(self.check_none(LG[0])),
                        'NET' : float(self.check_none(LGTT[0])),
                        'BHXH18_COMP' : float(self.check_none(BHXH_COMP[0])),
                        'BHYT3_COMP' : float(self.check_none(BHYT_COMP[0])),
                        'BHTN1_COMP' : float(self.check_none(BHTN_COMP[0])),
                        'KPCD_COMP' : float(self.check_none(KPCD_COMP[0])),
                        'SUM_CP': float(self.check_none(BHXH_COMP[0])) + float(self.check_none(BHYT_COMP[0])) + float(self.check_none(BHTN_COMP[0])) + float(self.check_none(KPCD_COMP[0])),
                        'BHXH8' : float(self.check_none(BHXH[0])),
                        'BHYT15' : float(self.check_none(BHYT[0])),
                        'BHTN1' : float(self.check_none(BHTN[0])),
                        'SUM_BH_BB' : float(self.check_none(BHXH[0])) + float(self.check_none(BHYT[0])) + float(self.check_none(BHTN[0])),
                        'THUE' : float(self.check_none(TNCN[0])),
                        'TAMUNG' : float(self.check_none(TU[0])),
                        'SUM_SUB' : float(self.check_none(BHXH[0])) + float(self.check_none(BHYT[0])) + float(self.check_none(BHTN[0])) + float(self.check_none(TNCN[0])) + float(self.check_none(TU[0])),
                        'THUC_LINH' : float(self.check_none(LGTT[0])) - float(self.check_none(BHXH[0])) + float(self.check_none(BHYT[0])) + float(self.check_none(BHTN[0])) + float(self.check_none(TNCN[0])) + float(self.check_none(TU[0])),
                        })
            
                 
        return res
    
    def numbers_to_strings(self, arg):
        switcher = {
            0: "A",
            1: "B",
            2: "C",
            3: "D",
            4: "E",
            5: "F",
            6: "G",
            7: "H",
            8: "I",
            9: "J",
            10: "K",
            11: "L",
            12: "M",
            13: "N",
            14: "O",
            15: "P",
            16: "Q",
            17: "R",
            18: "S",
            19: "T",
            20: "U",
            21: "V",
            22: "W",
            23: "X",
            24: "Y",
            25: "Z",
        }
        return switcher.get(arg, "nothing")
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
