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

class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.type = False
        self.start_date = False
        self.end_date = False
        self.localcontext.update({
            #'roman_numberal': self.roman_numberal,
            'get_line':self.get_line,
            'get_start_date': self.get_start_date,
            'get_end_date': self.get_end_date,
            'get_date':self.get_date,
            'get_payslip_obj': self.get_payslip_obj,
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.start_date = wizard_data['date_from'] or False
        self.end_date = wizard_data['date_to'] or False
        return True
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_start_date(self):
        if not self.start_date:
            self.get_header()
        return self.get_date(self.start_date)
    
    def get_end_date(self):
        if not self.end_date:
            self.get_header()
        return self.get_date(self.end_date)
    
    def get_payslip_obj(self, employee_id):
        kpcd = tnct = tntt = sum_reduction_dependents = 0
        sql ='''
            SELECT id from hr_payslip WHERE employee_id = %s AND to_char(date_from, 'YYYY-MM-DD') >= '%s' AND to_char(date_to, 'YYYY-MM-DD') <= '%s'
        '''%(employee_id, self.start_date, self.end_date)
        self.cr.execute(sql)
        payslip_id = self.cr.fetchone()
        if not payslip_id:
            return {'sum_reduction_dependents': sum_reduction_dependents,
                    'tnct': tnct,
                    'tntt': tntt,
                    'kpcd': kpcd * (-1)
                    } 
        else:
            for i in payslip_id:
                payslip_obj = self.pool.get('hr.payslip').browse(self.cr, self.uid, i)
                emp_obj = self.pool.get('hr.employee').browse(self.cr, self.uid, employee_id)
                if payslip_obj:
                    sum_reduction_dependents += payslip_obj.contract_id.structure_id.reduction_dependents * emp_obj.dependant_of_taxpayer + payslip_obj.contract_id.structure_id.reduction_yourself
                    tnct += payslip_obj.contract_id.gross_salary
                    tntt += payslip_obj.contract_id.gross_salary
                    for j in payslip_obj.line_ids:
                        if j.code == 'KPCD':
                            kpcd += j.total
                        if j.code == 'BDKTT':
                            tnct += j.total
                            tntt += j.total
            return {'sum_reduction_dependents': sum_reduction_dependents,
                    'tnct': tnct,
                    'tntt': tntt,
                    'kpcd': kpcd * (-1)
                    }  

    def get_line(self):
        res = []
        emp_ids = []
        sql ='''
            SELECT emp.id, emp.name_related, emp.tin, emp.identification_id 
            FROM hr_employee emp , hr_contract ct
            WHERE resigned_date IS NULL
            AND emp.id  = ct.employee_id AND ct.taxable_salary >0
            ORDER BY emp.code
        '''
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            res.append({'name': line['name_related'],
                        'tin': line['tin'],
                        'identification_id': line['identification_id'],
                        'tnct': self.get_payslip_obj(line['id'])['tnct'],
                        'sum_reduction_dependents': self.get_payslip_obj(line['id'])['sum_reduction_dependents'],
                        'kpcd': self.get_payslip_obj(line['id'])['kpcd'],
                        })
        return res
    
