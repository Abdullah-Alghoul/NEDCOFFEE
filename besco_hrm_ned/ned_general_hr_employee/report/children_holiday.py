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
        self.company_price = 0.0
        self.union_price = 0.0
        self.total_children = 0.0
        self.total_company_price = 0.0
        self.total_union_price = 0.0
        self.total = 0.0
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_title': self.get_title,
            'get_note': self.get_note,
            'get_employee': self.get_employee,
            'get_children': self.get_children,
            'get_total': self.get_total,
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
        self.company_price = wizard_data['company_price'] or False
        self.union_price = wizard_data['union_price'] or False
        return True
    
    def get_title(self):
        return '01/06/' + self.get_vietname_date(False)[6:11]
    
    def get_note(self):
        note = int(self.get_vietname_date(False)[6:11]) - 15
        return note
    
    def get_total(self):
        return {'total_children': self.total_children,
                'total_company_price': self.total_company_price,
                'total_union_price': self.total_union_price,
                'total': self.total
                }
    
    def get_employee(self):
        self.get_header()
        res = []
        emp_pool = self.pool.get('hr.employee')
        now = datetime.now()
        date = str(now.year)+'-06-01'
        
        sql = """SELECT id FROM hr_employee WHERE id IN(
                SELECT DISTINCT emp_id 
                                 FROM ( SELECT de.employee_id AS emp_id, e.department_id AS dep_id FROM hr_employee_dependent AS de, hr_employee AS e
                                        WHERE EXTRACT(YEAR FROM de.birthday) >= %s 
                                        ) a) and (resigned_date > '%s' or resigned_date is null) 
                                        
                ORDER BY hr_employee.department_id"""%(self.get_note(),date)
        self.cr.execute(sql)
        for i in self.cr.fetchall():
            emp_obj = emp_pool.browse(self.cr, self.uid, i)
            self.cr.execute("""SELECT count(*) FROM hr_employee_dependent WHERE EXTRACT(YEAR FROM birthday) >= %s AND employee_id = %s"""%(self.get_note(),i[0]))
            number_of_child = self.cr.fetchone()
            res.append({'employee_name': emp_obj.name_related,
                        'employee_id': i[0],
                        'job': emp_obj.department_id.name,
                        'number_of_child': number_of_child[0],
                        'money': number_of_child[0] * (self.company_price + self.union_price),
                        })
            self.total_children += number_of_child[0]
            self.total += number_of_child[0] * (self.company_price + self.union_price)
        return res
    
    def get_children(self, employee_id):
        res = []
        sql = """SELECT name AS name, EXTRACT(YEAR FROM birthday) AS birthday FROM hr_employee_dependent WHERE EXTRACT(YEAR FROM birthday) >= %s AND employee_id = %s"""%(self.get_note(),employee_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            res.append({'name': i['name'],
                        'birthday': i['birthday'],
                        'company': self.company_price,
                        'union': self.union_price,
                        'money': self.company_price + self.union_price
                        })
            self.total_company_price += self.company_price
            self.total_union_price += self.union_price
        return res
    
