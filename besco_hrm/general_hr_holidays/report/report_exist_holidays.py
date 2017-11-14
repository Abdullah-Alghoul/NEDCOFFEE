# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
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
        self.lead_planned_revenue = 0.0
        self.opp_planned_revenue = 0.0
        self.total_order = 0.0
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_items': self.get_items,
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
        return date.strftime('%d-%m-%Y')
    
    def get_items(self, employee_holidays_ids, leave_type_id):
        res = []
        for i in employee_holidays_ids:
            if self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_76z") and i.employee_id.insurance_code_id.name == 'TZ0076Z':
                contract_ids = self.pool.get('hr.contract').search(self.cr, self.uid, [('employee_id','=',i.employee_id.id)],order='id desc',limit=1)
                if contract_ids:
                    contract_obj = self.pool.get('hr.contract').browse(self.cr, self.uid, contract_ids[0])
                    sql_add ="""select sum(number_of_days) from hr_holidays where employee_id=%s and type='add' and holiday_status_id=%s"""%(i.employee_id.id, leave_type_id.id)
                    self.cr.execute(sql_add)
                    temp1 = self.cr.fetchone()
                    total_allocate_day = temp1[0]
                    sql_remove = """select sum(number_of_days) from hr_holidays where employee_id=%s and type='remove' and holiday_status_id=%s"""%(i.employee_id.id, leave_type_id.id)
                    self.cr.execute(sql_remove)
                    temp2 = self.cr.fetchone()
                    use_allocate_day = temp2[0]
                    res.append({'employee': i.employee_id.name_related,
                                'today': self.get_vietname_date(False),
                                'job': i.employee_id.job_id.name_vn,
                                'emp_code': i.employee_id.code,
                                'net': contract_obj.wage,
                                'net_per_day': contract_obj.wage / 26,
                                'date_from': self.get_vietname_date(leave_type_id.valid_from_date),
                                'date_to': self.get_vietname_date(leave_type_id.valid_to_date),
                                'total_allocate_day': total_allocate_day or 0,
                                'use_allocate_day': (use_allocate_day or 0) * (-1),
                                'remaining_leaves':i.remaining_leaves or 0,
                                'allocated_days': i.allocated_days or 0,
                                'amount': i.amount or 0,
                                'remaining_leaves_after': i.remaining_leaves_after or 0
                                })
            elif self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_68z") and i.employee_id.insurance_code_id.name == 'TZ0068Z':
                contract_ids = self.pool.get('hr.contract').search(self.cr, self.uid, [('employee_id','=',i.employee_id.id)],order='id desc',limit=1)
                if contract_ids:
                    contract_obj = self.pool.get('hr.contract').browse(self.cr, self.uid, contract_ids[0])
                    sql_add ="""select sum(number_of_days) from hr_holidays where employee_id=%s and type='add' and holiday_status_id=%s"""%(i.employee_id.id, leave_type_id.id)
                    self.cr.execute(sql_add)
                    temp1 = self.cr.fetchone()
                    total_allocate_day = temp1[0]
                    sql_remove = """select sum(number_of_days) from hr_holidays where employee_id=%s and type='remove' and holiday_status_id=%s"""%(i.employee_id.id, leave_type_id.id)
                    self.cr.execute(sql_remove)
                    temp2 = self.cr.fetchone()
                    use_allocate_day = temp2[0]
                    res.append({'employee': i.employee_id.name_related,
                                'today': self.get_vietname_date(False),
                                'job': i.employee_id.job_id.name_vn,
                                'emp_code': i.employee_id.code,
                                'net': contract_obj.wage,
                                'net_per_day': contract_obj.wage / 26,
                                'date_from': self.get_vietname_date(leave_type_id.valid_from_date),
                                'date_to': self.get_vietname_date(leave_type_id.valid_to_date),
                                'total_allocate_day': total_allocate_day or 0,
                                'use_allocate_day': (use_allocate_day or 0) * (-1),
                                'remaining_leaves':i.remaining_leaves or 0,
                                'allocated_days': i.allocated_days or 0,
                                'amount': i.amount or 0,
                                'remaining_leaves_after': i.remaining_leaves_after or 0
                                })
        return res 
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
