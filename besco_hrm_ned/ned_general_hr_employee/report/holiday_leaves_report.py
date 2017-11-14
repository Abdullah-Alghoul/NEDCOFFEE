# -*- coding: utf-8 -*-
import logging
from pychart.tick_mark import Null
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.start_date = False
        self.end_date = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_start_date': self.get_start_date,
            'get_end_date': self.get_end_date,
            'get_company_name': self.get_company_name,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'get_partner_address': self.get_partner_address,
            'calculate_monthdelta': self.calculate_monthdelta,
            'get_data' : self.get_data,
            'get_total_legal_days' : self.get_total_legal_days,
            'get_used_days' : self.get_used_days,
            'get_remain_days' : self.get_remain_days,
            'get_onleave_days' : self.get_onleave_days,
            'get_set_years' : self.get_set_years,
            'get_total_cut' : self.get_total_cut,
        })
    
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
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.start_date = wizard_data['start_date'] or False
        self.end_date = wizard_data['end_date'] or False
        return True
    
    def get_start_date(self):
        if not self.start_date:
            self.get_header()
        return self.start_date
    
    def get_end_date(self):
        if not self.end_date:
            self.get_header()
        return self.end_date
    
    def get_set_years(self):
        res = []
        if not self.start_date: 
            self.get_header()
        if not self.end_date:
            self.get_header()
        end_year = datetime.strptime(self.end_date, DATE_FORMAT).year
        start_year = datetime.strptime(self.start_date, DATE_FORMAT).year
        for year in range(int(start_year),int(end_year)+1):
            res.append({'year': year})
        return res
    
    def get_data(self):
        self.get_header()
        legal_vals = []
        employee_line_ids = self.pool.get('hr.employee').search(self.cr,self.uid,[(1,'=',1)])
        for employee_line_id in employee_line_ids:
            employee_obj = self.pool.get('hr.employee').browse(self.cr,self.uid,employee_line_id)
            legal_vals.append({
                                'emp_code' : employee_obj.code,
                                'emp_id' : employee_obj.id,
                                'employee' : employee_obj.name,
                                'join_date' : employee_obj.joining_date,
                                'job' :employee_obj.job_id.name_vn,
                            })                     
        return legal_vals
            
    def get_days(self,emp_id,year):
        res = []
        used_days = self.get_used_days(emp_id,year)
        remain = self.get_remain_days(emp_id,year)
        onleave = self.get_onleave_days(emp_id, year)
        total_days = self.get_total_legal_days(emp_id, year)
        res.append({
                    'used' : used_days,
                    'remain' : remain,
                    'onleave' : onleave,
                    'total' : total_days
                    })
        return res
     
    def get_used_days(self,emp_id,year):
        sql = '''SELECT SUM(hr_holidays.number_of_days) FROM hr_holidays, hr_holidays_status
                        WHERE EXTRACT(YEAR FROM hr_holidays.date_from) = %s
                        AND hr_holidays.type='remove'
                        AND hr_holidays.state='validate'
                        AND hr_holidays.holiday_status_id = hr_holidays_status.id
                        AND hr_holidays_status.leave_type_code='A'
                        AND hr_holidays.employee_id=%s'''%(year,emp_id)
        self.cr.execute(sql)
        day = self.cr.fetchone()
        if day is None:
            return 0
        else:
            if day[0] is None:
                return 0
            else:
                return day[0] * (-1)
     
    def get_remain_days(self,emp_id,year):
        total_days = self.get_total_legal_days(emp_id, year)
        used_days = self.get_used_days(emp_id,year)
        if total_days is None:
            total_days =0.0;
        if used_days is None:
            used_days =0.0;    
        return total_days - used_days
     
    def get_onleave_days(self,emp_id,year):
        sql = '''SELECT hr_holidays.number_of_days FROM hr_holidays, hr_holidays_status
                        WHERE EXTRACT(YEAR FROM hr_holidays.date_from) = %s
                        AND hr_holidays.type='add'
                        AND hr_holidays.holiday_status_id = hr_holidays_status.id
                        AND hr_holidays_status.leave_type_code='T'
                        AND hr_holidays.employee_id=%s'''%(year,emp_id)
        self.cr.execute(sql)
        day = self.cr.fetchone()
        if not day:
            return 0
        return day[0]
     
    def get_total_legal_days(self,emp_id,year):
        sql = '''SELECT SUM(hr_holidays.number_of_days) FROM hr_holidays, hr_holidays_status
                        WHERE EXTRACT(YEAR FROM hr_holidays.date_from) = %s
                        AND hr_holidays.type='add'
                        AND hr_holidays.state='validate'
                        AND hr_holidays.holiday_status_id = hr_holidays_status.id
                        AND hr_holidays_status.leave_type_code='A'
                        AND hr_holidays.employee_id=%s'''%(year,emp_id)
        self.cr.execute(sql)
        day = self.cr.fetchone()
        if not day:
            return 0
        return day[0]
     
    def get_total_cut(self, emp_id):
        years = self.get_set_years()
        days =0
        for year in years:
            days += self.get_onleave_days(emp_id,year['year'])
        return days
    
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
         
    def calculate_monthdelta(self,str1,str2):
        date1 = datetime.strptime(str1,"%Y-%m-%d")
        date2 = datetime.strptime(str2,"%Y-%m-%d")
        def is_last_day_of_the_month(date):
            days_in_month = calendar.monthrange(date.year,date.month)[1]
            return date.day == days_in_month
        imaginary_day_2 = 31 if is_last_day_of_the_month(date2) else date2.day
        monthdelta = (
            (date2.month - date1.month) +
            (date2.year - date1.year) * 12 +
            (-1 if date1.day > imaginary_day_2 else 0)
            )
        return monthdelta
 
    def get_company_website(self):
        self.cr.execute("SELECT partner_id FROM res_company")
        temp = self.cr.fetchone()
        res_partner = self.pool.get('res.partner').browse(self.cr,self.uid,temp[0])
        return res_partner.website
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
