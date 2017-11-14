# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 ISA s.r.l. (<http://www.isa.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

from datetime import datetime, timedelta
import copy

def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]

class Parser(report_sxw.rml_parse):
    
    
    def __init__(self, cr, uid, name, context):
        self.total_overtimes = {}
        self.totals_by_type = {}
        self.totals = {}
        self.context = context
                
        # import pdb; pdb.set_trace()
        
        self.overt_type = self._get_overtime_type_by_orm(cr, uid, context)
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_overtime_by_month':self.get_overtime_by_month,
            'get_days':self.get_days,
            'get_overtime_by_type':self.get_overtime_by_type,
            'get_overtime_type':self.get_overtime_type,
            'get_totals_by_type':self.get_totals_by_type,
            'get_date':self.get_date,
            'get_wizard_params':self.get_wizard_params,
            'get_emps':self.get_employees,
        })
    
    def get_employees(self):
        # import pdb; pdb.set_trace()
        sql_string = '''
            select emp.id,res.name
            from hr_employee emp
            inner join resource_resource res on emp.resource_id=res.id
            where res.active=true and emp.department_id is not null
            and emp.id in (%s)
            order by res.name
        '''
        id_string = ','.join(str(n) for n in self.context['active_ids'])
        sql = sql_string % (id_string)
        self.cr.execute(sql)
        emps = self.cr.dictfetchall()
        return emps
    
    def get_wizard_params(self, month, year):
        self.month = month
        self.year = year
        
    def get_overtime_by_type(self, overt_type):
        # import pdb; pdb.set_trace()
        if(self.total_overtimes.has_key(overt_type)):
            return self.total_overtimes[overt_type]
        return 0
        
    def get_totals_by_type(self, overt_type):
        # import pdb; pdb.set_trace()
        return self.totals[overt_type]
    
    
    def _get_overtime_type_by_orm(self, cr, uid, context):
        hrs = self.pool.get('hr.overtime.type')
        hrs_list = hrs.search(cr, uid, [("active", "=", True)])
        orm_types = hrs.read(cr, uid, hrs_list, ['id', 'name'], context)
        return orm_types
    
    def get_overtime_type(self):
        return self.overt_type
    
    def get_overtime_by_month(self, emp_id):
        
        # emp_id=21
                
        # fisso il mese che poi verra recuperate/calcolate con un wizard
        last_day_month = lengthmonth(self.year, self.month)
        first_date = datetime(self.year, self.month, 1)
        last_date = datetime(self.year, self.month, last_day_month)
        
        interval = self._get_interval_days(first_date, last_date)
        
        ref_range = {}
        for i in interval:
            ref_range[i] = 0
        
        tot_range = {}
        for k in self._build_totals_dict():
            tot_range[k] = copy.copy(ref_range)
        
        sql = '''
            select overt.number_of_hours_temp, overt.overtime_type_id,overt_type.name,
            overt.date_from, overt.date_to
            from hr_employee as emp 
            inner join hr_overtime as overt on emp.id = overt.employee_id
            inner join hr_overtime_type as overt_type on overt_type.id = overt.overtime_type_id
            where 
            (
            (EXTRACT(YEAR FROM (overt.date_from))=%s and 
            EXTRACT(MONTH FROM (overt.date_from))=%s)
            or
            (EXTRACT(YEAR FROM (overt.date_to))=%s and 
            EXTRACT(MONTH FROM (overt.date_to))=%s)
            )
            and emp.id = %s and state='validate'
            order by overt.date_from, overt_type.name
            '''
           
        # self.cr.execute(sql, (first_date.strftime('%Y-%m-%d %H:%M:%S'), last_date.strftime('%Y-%m-%d %H:%M:%S'), emp_id))
        self.cr.execute(sql, (self.year, self.month, self.year, self.month, emp_id))                
        # variabile da tornare: lista bidimensionale con tutti gli utenti e tutti i giorni.
        managed_overtime = []
        
        overtimes = self.cr.dictfetchall()
        
        for overtime in overtimes:
                        
            date_to = datetime.strptime(overtime['date_to'], '%Y-%m-%d %H:%M:%S')
            date_from = datetime.strptime(overtime['date_from'], '%Y-%m-%d %H:%M:%S')
            overt_interval = self._get_interval_days(datetime.date(date_from), datetime.date(date_to))
            
            overt_range = {}
            for i in overt_interval:
                overt_range[i] = 0
            
            # hol_working_range=self._get_working_days(hol_range,hol['holiday_status_id'])
            
            emp_overt_hours4days = self._get_emp_overt_hours4days(emp_id, float(overtime['number_of_hours_temp']), overt_range)
           
            for k, v in emp_overt_hours4days.items():
                if (k in tot_range[overtime['overtime_type_id']]):
                    tot_range[overtime['overtime_type_id']][k] += v
        
        totals = self._build_totals_dict()
        total_overtimes = {}    
        for k in tot_range:
            keys_days = sorted(tot_range[k].keys())
            total_overtimes[k] = []
            for day in keys_days:
                total_overtimes[k].append(tot_range[k][day])
                totals[k] += tot_range[k][day]
        
        # import pdb; pdb.set_trace()
        self.total_overtimes = total_overtimes
        self.totals = totals
        # import pdb; pdb.set_trace()
        
    def _get_interval_days(self, date_from, date_to):
        # date_from=datetime.strptime(date_from_str,'%Y-%m-%d')
        # date_to=datetime.strptime(date_to_str,'%Y-%m-%d')
        days = (date_to - date_from).days + 1
        interval = []
        for i in range(days):
            date_act = date_from + timedelta(days=i)
            interval.append(date_act.strftime('%Y-%m-%d'))
        return interval    
    
    def get_days(self):
        last_day = lengthmonth(self.year, self.month)
        days = []
        # import pdb; pdb.set_trace()
        for i in range(1, last_day + 1, 1):
            days.append(i)
        return days
    
    def _build_totals_dict(self):
        totals = {}
        overtime_type = self.get_overtime_type()
        for type in overtime_type:
            totals[type['id']] = 0
        return totals
    
    def get_date(self):
        date = datetime(self.year, self.month, 1)
        return date.strftime("%B %Y")
        
    def _get_emp_overt_hours4days(self, emp_id, overt_hours, working_days):
        
        num_days = len(working_days)
        hours_for_day = overt_hours / num_days
        for k in working_days.keys():
            working_days[k] = hours_for_day
        return working_days
    
