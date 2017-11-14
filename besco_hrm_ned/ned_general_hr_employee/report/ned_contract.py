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
from openerp import SUPERUSER_ID
from datetime import datetime
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
        self.type = False
        self.localcontext.update({
            #'roman_numberal': self.roman_numberal,
            'get_line':self.get_line,
            'get_date':self.get_date
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.type = wizard_data['type'] and wizard_data['type'][1] or False
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    
    def get_line(self):
        emp_ids = []
        
        check_68z = self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_68z")
        check_76z = self.pool.get('ir.model.access').check_groups(self.cr, self.uid, "ned_general_hr_security.group_hr_manager_76z")
        if check_76z:
            contract_ids = self.pool.get('hr.contract').search(self.cr, SUPERUSER_ID, [('employee_id.insurance_code_id.name','=','TZ0076Z')])
            for line in contract_ids:
                emp_ids.append(line)
        if check_68z:
            sql ='''
                SELECT id from hr_contract
            '''
            self.cr.execute(sql)
            for line in self.cr.dictfetchall():
                emp_ids.append(line['id'])
        return self.pool.get('hr.contract').browse(self.cr,self.uid,emp_ids)
            
            
        