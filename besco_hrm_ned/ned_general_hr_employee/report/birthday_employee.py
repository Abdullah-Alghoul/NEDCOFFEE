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

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.date = False
        self.total = 0.0
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_title': self.get_title,
            'get_employee': self.get_employee,
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
        self.date = wizard_data['date'] or False
        return True
    
    def get_title(self):
        return self.get_vietname_date(False)[3:11]
    
    def get_employee(self):
        self.get_header()
        res = []
        emp_pool = self.pool.get('hr.employee')
        sql = """SELECT id FROM hr_employee WHERE EXTRACT(MONTH FROM birthday) = %s AND resigned_date IS NULL"""%self.get_vietname_date(self.date)[3:5]
        self.cr.execute(sql)
        for i in self.cr.fetchall():
            emp_obj = emp_pool.browse(self.cr, self.uid, i)
            res.append({'employee_name': emp_obj.name_related,
                        'employee_code': emp_obj.code,
                        'job': emp_obj.job_id.name,
                        'birthday': self.get_vietname_date(emp_obj.birthday),
                        })
            self.total += 1
        return res
    
    
