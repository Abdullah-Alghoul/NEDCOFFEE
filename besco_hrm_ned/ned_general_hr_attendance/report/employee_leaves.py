# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp.exceptions import UserError
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
        self.employee_id = False
        self.year = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_year': self.get_year,
            'get_last_year': self.get_last_year,
            'get_employee_id': self.get_employee_id, 
            'get_employee_name': self.get_employee_name,
            'get_employee_code': self.get_employee_code,
            'get_employee_job': self.get_employee_job,
            'get_anual_leaves_transfer': self.get_anual_leaves_transfer, 
            'get_anual_leaves': self.get_anual_leaves,
            'get_total_anual_leaves': self.get_total_anual_leaves,
            'get_manager': self.get_manager,
            'get_days_used': self.get_days_used,
            'get_hr_admin': self.get_hr_admin,
            'get_all_leaves': self.get_all_leaves,
            'check_annual': self.check_annual,
            'check_sick': self.check_sick,
            'check_maternity': self.check_maternity,
            'check_unpaid': self.check_unpaid,
            'check_paid': self.check_paid,
            'check_replacement': self.check_replacement
        })
        
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
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.employee_id = wizard_data['employee_id'] and wizard_data['employee_id'][0] or False
        self.year = wizard_data['year'] or False
        return True
    
    def get_year(self):
        if not self.year:
            self.get_header()
        return self.year or False
    
    def get_last_year(self):
        if not self.year:
            self.get_header()
        year = self.year
        last_year = int(year) - 1 or 0
        return last_year
    
    def get_employee_id(self):
        if not self.employee_id:
            self.get_header()
        return self.employee_id
    
    def get_employee_name(self):
        if not self.employee_id:
            self.get_header()
        employee_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, self.employee_id)
        name_related = employee_obj.name_related or False
        return name_related
    
    def get_employee_code(self):
        if not self.employee_id:
            self.get_header()
        employee_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, self.employee_id)
        code = employee_obj.code or False
        return code
    
    def get_employee_job(self):
        if not self.employee_id:
            self.get_header()
        employee_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, self.employee_id)
        job = employee_obj.job_id.name_vn or False
        return job
    
    def get_anual_leaves_transfer(self):
        days = 0
        if not self.employee_id:
            self.get_header()
        if not self.year:
            self.get_header()
        if not self.employee_id or not self.year:
            raise UserError('An Error Occured, please contact Administrator for supporting!')
        sql = '''SELECT hh.number_of_days_temp
                FROM hr_holidays hh join hr_holidays_status hhs on hh.holiday_status_id = hhs.id
                WHERE hh.type = 'add' AND hhs.active is TRUE
                    AND hh.state = 'validate'
                    AND hhs.legal_leaves is TRUE
                    AND transfer_old_leave is TRUE  
                    AND hh.employee_id = %s
                    AND to_char(hhs.valid_from_date,'YYYY') = '%s' 
                    AND to_char(hhs.valid_to_date,'YYYY') = '%s'
                '''%(self.employee_id,self.year,self.year)
        self.cr.execute(sql)
        result = self.cr.dictfetchall()
        days = result and result[0] and result[0]['number_of_days_temp'] or 0.0
        return days
    
    def get_anual_leaves(self):
        days = 0
        if not self.employee_id:
            self.get_header()
        if not self.year:
            self.get_header()
        last_year = self.get_last_year()
        
        sql = '''SELECT hh.number_of_days_temp
                FROM hr_holidays hh join hr_holidays_status hhs on hh.holiday_status_id = hhs.id
                WHERE hh.type = 'add' AND hhs.active is TRUE
                     AND hh.state = 'validate'
                    AND hhs.legal_leaves is TRUE
                    AND transfer_old_leave is False  
                    AND hh.employee_id = %s
                    AND to_char(hhs.valid_from_date,'YYYY') = '%s' 
                    AND to_char(hhs.valid_to_date,'YYYY') = '%s'
                '''%(self.employee_id,self.year,self.year)
        self.cr.execute(sql)
        result = self.cr.dictfetchall()
        days = result and result[0] and result[0]['number_of_days_temp'] or 0.0
        return days
    
    def get_total_anual_leaves(self):
        days = 0
        if not self.employee_id:
            self.get_header()
        if not self.year:
            self.get_header()
        last_year = self.get_last_year()
        
        sql = '''SELECT sum(hh.number_of_days_temp) number_of_days_temp
            FROM hr_holidays hh join hr_holidays_status hhs on hh.holiday_status_id = hhs.id
            WHERE hh.type = 'add' AND hhs.active is TRUE
                AND hhs.legal_leaves is TRUE
                AND hh.state = 'validate'
                AND hh.employee_id = %s
                AND to_char(hhs.valid_from_date,'YYYY') = '%s' 
                AND to_char(hhs.valid_to_date,'YYYY') = '%s'
        '''%(self.employee_id,self.year,self.year)
        self.cr.execute(sql)
        result = self.cr.dictfetchall()
        days = result and result[0] and result[0]['number_of_days_temp'] or 0.0
        return days
    
    def get_manager(self, manager_id):
        name_related = ''
        if manager_id:
            employee_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, manager_id)
            name_related = employee_obj.name_related or ''
        return name_related
    
    def get_days_used(self, employee_id, date_from, year):
        days = 0
        if employee_id and date_from and year:
            sql='''SELECT sum(hh.number_of_days_temp) number_of_days_temp
                FROM hr_holidays hh join hr_holidays_status hhs on hh.holiday_status_id = hhs.id
                WHERE hh.type = 'remove' 
                    AND hh.employee_id = %s
                    AND hh.date_from <= '%s' 
                    AND to_char(hh.date_from,'YYYY') = '%s'
                    AND hh.state = 'validate' 
            '''%(employee_id, date_from, year)
            self.cr.execute(sql)
            result = self.cr.dictfetchall()
            days = result and result[0] and result[0]['number_of_days_temp'] or 0.0
        return days
    
    def get_hr_admin(self):
        admin_hr = ''
        admin_ids = self.pool.get('hr.employee').search(self.cr, self.uid, [('admin_hr','=',True)])
        for admin_id in admin_ids:
            if len(admin_hr)>1:
                admin_hr += ','
            admin_hr += self.pool.get('hr.employee').browse(self.cr,self.uid,admin_id).name_related
        return admin_hr
    
    def get_all_leaves(self):
        res = []
        if not self.employee_id:
            self.get_header()
        if not self.year:
            self.get_header()
        total_anual_leaves = self.get_total_anual_leaves() or 0
        sql='''SELECT
                        to_char(hh.create_date,'DD-MM-YYYY') create_date,
                        hh.date_from date_from,
                        hh.date_to date_to,
                        to_char(hh.date_from,'YYYY') h_year,
                        hh.number_of_days_temp days,
                        he.name_related name_related,
                        hh.manager_id manager_id,
                        hh.manager_id2 manager_id2, hhs.legal_leaves legal_leaves,
                        hhs.id holiday_status_id,
                        hh.report_note report_note
                FROM    hr_holidays hh join hr_holidays_status hhs
                        on
                            hh.holiday_status_id = hhs.id
                            join hr_employee he on he.id = hh.employee_id
                        WHERE hh.employee_id = %s
                        AND to_char(hh.date_from,'YYYY') = '%s'
                        AND hh.type = 'remove'
                        AND hh.state = 'validate'
                ORDER BY date_from
        '''%(self.employee_id,self.year)
        self.cr.execute(sql)
#         total = self.get_anual_leaves() or 0
#         print total
        for line in self.cr.dictfetchall():
            end_balance = 0 
            if line['legal_leaves'] == True:
                days_used = self.get_days_used(self.employee_id, line['date_from'], line['h_year']) or 0
                end_balance = total_anual_leaves - line['days']
                total_anual_leaves = total_anual_leaves - line['days']
            manager = self.get_manager(line['manager_id'] or line['manager_id2'] or False) or False
            admin_hr = self.get_hr_admin() or ''
                
            res.append({
                        'create_date': line['create_date'] or False,
                        'report_note': line['report_note'] or '',
                        'date_from': line['date_from'] or False,
                        'date_to': line['date_to'] or False,
                        'days': line['days'] or 0,
                        'name_related': line['name_related'] or '', 
                        'manager': manager,
                        'end_balance': total_anual_leaves,  
                        'admin_hr': admin_hr,
                        'holiday_status_id': line['holiday_status_id'] or False
                        })
        return res
        
    def check_annual(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'A':
            tick = 'X'
        return tick
     
    def check_sick(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'S':
            tick = 'X'
        return tick
     
    def check_maternity(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'M':
            tick = 'X'
        return tick
     
    def check_unpaid(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'U':
            tick = 'X'
        return tick
     
    def check_paid(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'P':
            tick = 'X'
        return tick
     
    def check_replacement(self,holiday_status_id):
        tick = False
        holiday_status_obj = self.pool.get('hr.holidays.status').browse(self.cr,self.uid,holiday_status_id)
        if holiday_status_obj.leave_type_code == 'R':
            tick = 'X'
        return tick
