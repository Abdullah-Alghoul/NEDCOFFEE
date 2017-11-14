# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
logger = logging.getLogger('report_aeroo')
from openerp.report.report_sxw import rml_parse
import time
from datetime import datetime
from datetime import timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.date_from = False
        self.date_to = False
        self.sum_100 = 0.0
        self.sum_150 = 0.0
        self.sum_200 = 0.0
        self.sum_300 = 0.0
        self.sum_400 = 0.0
        self.sum_p = 0.0
        self.sum_b = 0.0
        self.sum_o = 0.0
        self.sum_k = 0.0
        self.localcontext.update({
            'get_vietname_datetime': self.get_vietname_datetime,
            'days_in_months':self.days_in_months,
            'convert_to_dd_month':self.convert_to_dd_month,
            'check_none': self.check_none,
            'get_company_phone': self.get_company_phone,
            'get_company_website': self.get_company_website,
            'get_value_rule_employee': self.get_value_rule_employee,
            'get_data' : self.get_data,
            'get_month_year': self.get_month_year,
            'get_timesheet_line': self.get_timesheet_line,
            'get_timesheet_line_ot': self.get_timesheet_line_ot,
            'get_sum_leaves': self.get_sum_leaves,
            'sum_hours': self.sum_hours,
            'sum_ot': self.sum_ot,
            'get_sum':self.get_sum,
        })
        
    def get_sum(self):
        res = []
        return {'sum_100': self.sum_100,
                'sum_150':self.sum_150,
                'sum_200':self.sum_200,
                'sum_300': self.sum_300,
                'sum_400': self.sum_400,
                'sum_p': self.sum_p,
                'sum_b': self.sum_b,
                'sum_o' : self.sum_o,
                'sum_k': self.sum_k
                }

    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.date_from = wizard_data['date_from']
        self.date_to = wizard_data['date_to']
        return True

    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d-%m-%Y')

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

    def days_in_months(self):
        if not self.date_from and not self.date_to:
            self.get_header()
        res = []
        date_from = datetime.strptime(self.date_from,DATE_FORMAT)
        date_to = datetime.strptime(self.date_to,DATE_FORMAT)
        day_temp = date_from
        while day_temp <= date_to:
            res.append(datetime.strftime(day_temp,'%d-%m-%Y'))
            day_temp = day_temp + timedelta(days=1)
        return res

    def convert_to_dd_month(self, date):
        date = datetime.strftime(datetime.strptime(date,'%d-%m-%Y'),'%d-%b')
        return date

    def get_data(self):
        self.get_header()
        legal_vals = []
        hr_team_ids = self.pool.get('hr.team').search(self.cr,self.uid,[])
        for hr_team_id in hr_team_ids:
            hr_team_obj = self.pool.get('hr.team').browse(self.cr,self.uid,hr_team_id)
            employee_line_ids = self.pool.get('hr.employee').search(self.cr,self.uid,[('hr_team_id','=',hr_team_id)])
            res = []
            for employee_line_id in employee_line_ids:
                employee_obj = self.pool.get('hr.employee').browse(self.cr,self.uid,employee_line_id)
                dic = {
                                    'emp_code' : employee_obj.code,
                                    'emp_id' : employee_obj.id,
                                    'employee' : employee_obj.name,
                        }
                res.append(dic)
            if not res:
                continue
            team_item = {'team_name': hr_team_obj.name,
                         'emp_list':res}
            legal_vals.append(team_item)
        return legal_vals

    def get_month_year(self):
        if not self.date_to:
            self.get_header()
        return datetime.strftime(datetime.strptime(self.date_to,DATE_FORMAT),'%d-%m-%Y')[3:10]

    def get_timesheet_line(self, date, employee_id):
        date = datetime.strftime(datetime.strptime(date,'%d-%m-%Y'),DATE_FORMAT)
        sql = '''SELECT real_worked FROM general_hr_timesheet hr join general_hr_timesheet_lines hrl on hrl.hr_timesheet_id = hr.id
                        WHERE hr.state = 'approve'
                        AND hr.work_date = '%s'
                        AND hrl.employee_id = %s''' %(date, employee_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            if line['real_worked']:
                return line['real_worked']
        usertz_vs_utctz = self.pool.get('res.users').get_diff_hours_usertz_vs_utctz(self.cr, self.uid) or 7
        leave = self.was_on_leave(employee_id, date, usertz_vs_utctz)
        if leave:
            if datetime.strptime(date, DATE_FORMAT).weekday() == 6:
                return 0
            if leave[0] and leave[0].holiday_status_id:
                if leave[0].holiday_status_id.leave_type_code=='A':
                    return 'P'
                elif leave[0].holiday_status_id.leave_type_code=='U':
                    return 'K'
                elif leave[0].holiday_status_id.leave_type_code=='S':
                    return 'O'
                if leave[0].holiday_status_id.leave_type_code=='R':
                    return 'B'
        return 0

    def get_timesheet_line_ot(self, date, employee_id, rate):
        date = datetime.strftime(datetime.strptime(date,'%d-%m-%Y'),DATE_FORMAT)
        sql = '''SELECT ot_worked FROM general_hr_timesheet hr join general_hr_timesheet_lines hrl on hrl.hr_timesheet_id = hr.id
                        WHERE hr.state = 'approve'
                        AND hr.work_date = '%s' 
                        AND hrl.employee_id = %s AND ot_rate = %s''' %(date, employee_id,rate)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            return line['ot_worked'] or 0
        return 0

    def sum_hours(self, employee_id):
        if not self.date_from or not self.date_to:
            self.get_header()
        if not self.date_from or not self.date_to:
            return 0
        sql = '''SELECT sum(real_worked) sum_real FROM general_hr_timesheet hr join general_hr_timesheet_lines hrl on hrl.hr_timesheet_id = hr.id
                        WHERE  hr.state = 'approve'
                        AND hr.work_date >= '%s' AND hr.work_date <= '%s'
                        AND hrl.employee_id = %s''' % (self.date_from, self.date_to, employee_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            self.sum_100 += line['sum_real'] or 0
            return line['sum_real'] or 0
        return 0

    def sum_ot(self, employee_id, rate):
        if not self.date_from or not self.date_to:
            self.get_header()
        if not self.date_from or not self.date_to:
            return 0
        sql = '''SELECT sum(ot_worked) sum_ot FROM general_hr_timesheet hr join general_hr_timesheet_lines hrl on hrl.hr_timesheet_id = hr.id
                        WHERE  hr.state = 'approve'
                        AND hr.work_date >= '%s' AND hr.work_date <= '%s'
                        AND hrl.employee_id = %s AND ot_rate = %s''' % (self.date_from, self.date_to, employee_id,rate)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            if rate==150:
                self.sum_150 += line['sum_ot'] or 0
            if rate==200:
                self.sum_200 += line['sum_ot'] or 0
            if rate==300:
                self.sum_300 += line['sum_ot'] or 0
            if rate==400:
                self.sum_400 += line['sum_ot'] or 0
            return line['sum_ot'] or 0
        return 0

    def get_sum_leaves(self, employee_id,type):
        usertz_vs_utctz = self.pool.get('res.users').get_diff_hours_usertz_vs_utctz(self.cr, self.uid) or 7
        if not self.date_from or not self.date_to:
            self.get_header()
        if not self.date_from or not self.date_to:
            return 0
        date_from = datetime.strptime(self.date_from, DATE_FORMAT)
        date_to = datetime.strptime(self.date_to, DATE_FORMAT)
        day_temp = date_from
        days = 0
        while day_temp <= date_to:
            if day_temp.weekday()== 6:
                day_temp = day_temp + timedelta(days=1)
                continue
            leave = self.was_on_leave(employee_id, day_temp, usertz_vs_utctz)
            if leave:
                if leave[0] and leave[0].holiday_status_id:
                    if leave[0].holiday_status_id.leave_type_code == type:
                        days +=1
            day_temp = day_temp + timedelta(days=1)
        if type =='A':
            self.sum_p += days
        if type =='R':
            self.sum_b += days
        if type =='S':
            self.sum_o += days
        if type =='U':
            self.sum_k += days
        return days

    def was_on_leave(self,employee_id, day, usertz_vs_utctz, context=None):
        res = False
        if type(day) is not str:
            day = day.strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.cr.execute("""SELECT id, to_char((date_from + interval '%(usertz_vs_utctz)s hour')::date, 'DD/MM/YYYY') date_from,
        to_char((date_to + interval '%(usertz_vs_utctz)s hour')::date, 'DD/MM/YYYY') date_to FROM hr_holidays WHERE state = 'validate' AND type = 'remove'
        AND %(date)s >= (date_from + interval '%(usertz_vs_utctz)s hour')::date AND %(date)s <= (date_to + interval '%(usertz_vs_utctz)s hour')::date
        AND %(employee_id)s = employee_id""",
                   {'date': day, 'usertz_vs_utctz': usertz_vs_utctz, 'employee_id': employee_id})
        holiday_ids = self.cr.fetchall()  # [x[0] for x in cr.fetchall()]
        if holiday_ids and holiday_ids[0]:
            res = [self.pool.get('hr.holidays').browse(self.cr, self.uid, holiday_ids[0][0], context=context), holiday_ids[0][1],
                   holiday_ids[0][2]]
        return res