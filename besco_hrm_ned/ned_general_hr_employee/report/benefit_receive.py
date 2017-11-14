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
from datetime import datetime, timedelta
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
        self.code = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_header':self.get_header,
            'get_sick_employee':self.get_sick_employee,
            'roman_numberal': self.roman_numberal,
            'get_code': self.get_code,
            'get_sum_day': self.get_sum_day,
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
    
    def get_sum_day(self, date_from, date_to):
        days = (date_to - date_from).days + 1
        print "get_sunday"
        print date_from
        print date_to
        sunday = 0
        print "===I===="
        for i in range(days):
            
            date_act = date_from + timedelta(days=i)
            print date_act
            print date_act.weekday()
            if date_act.weekday() == 6:
                sunday += 1
        return sunday 
    
    def get_sick_employee(self, code):
        if not self.date_from:
            self.get_header()
        reason_res = []
        employee_res = []
        sql = '''SELECT DISTINCT name, reason_code FROM hr_holidays_reason WHERE id IN (
                        SELECT reason_id FROM hr_holidays 
                        WHERE date_from BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD') 
                        AND date_to  BETWEEN to_date('%s', 'YYYY-MM-DD') AND to_date('%s', 'YYYY-MM-DD') 
                        AND type = 'remove')
                        AND hr_holidays_status_id = (
                        SELECT id from hr_holidays_status
                        WHERE leave_type_code ='%s')''' % (self.date_from, self.date_to, self.date_from, self.date_to, code)
        self.cr.execute(sql)
        reasons = self.cr.fetchall()
        if reasons:
            for reason in reasons:
                if employee_res:
                    employee_res = []
                sql = '''SELECT employee_id,date_from,date_to FROM hr_holidays WHERE
                                reason_id = (SELECT id FROM hr_holidays_reason WHERE reason_code = '%s')
                                ''' % reason[1]
                self.cr.execute(sql)
                employees = self.cr.fetchall()
                if employees:
                    for employee in employees:
                        sum_day = (datetime.strptime(employee[2], DATETIME_FORMAT) - datetime.strptime(employee[1], DATETIME_FORMAT)).days + 1
                        print self.get_sum_day(datetime.strptime(employee[2], DATETIME_FORMAT), datetime.strptime(employee[1], DATETIME_FORMAT))
                        employee_res.append({
                            'emp': self.pool.get('hr.employee').browse(self.cr, self.uid, employee[0]).name,
                            'insurance': self.pool.get('hr.employee').browse(self.cr, self.uid, employee[0]).insurance_number,
                            'date_from': employee[1],
                            'date_to': employee[2],
                            'sum': sum_day - self.get_sum_day(datetime.strptime(employee[1], DATETIME_FORMAT), datetime.strptime(employee[2], DATETIME_FORMAT)),
                        })
                reason_res.append({
                    'reason': reason[0],
                    'employee_res': employee_res})
        return reason_res
    
    def  roman_numberal(self, input) :
        if input < 1 or input > 3999:
            return False
        s = ""
        while (input >= 1000) :
            s += "M" 
            input -= 1000       
        while (input >= 900) :
            s += "CM" 
            input -= 900 
        while (input >= 500):
            s += "D" 
            input -= 500 
        while (input >= 400):
            s += "CD" 
            input -= 400 
        while (input >= 100):
            s += "C" 
            input -= 100 
        while (input >= 90):
            s += "XC" 
            input -= 90 
        while (input >= 50):
            s += "L" 
            input -= 50 
        while (input >= 40):
            s += "XL" 
            input -= 40 
        while (input >= 10):
            s += "X" 
            input -= 10 
        while (input >= 9):
            s += "IX" 
            input -= 9 
        while (input >= 5):
            s += "V" 
            input -= 5 
        while (input >= 4):
            s += "IV" 
            input -= 4 
        while (input >= 1):
            s += "I" 
            input -= 1 
        return s 

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
    
