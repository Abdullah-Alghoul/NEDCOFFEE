# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

import time

from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import datetime
import base64

from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook, xldate_as_tuple

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

DATEOFFSET = 693594

class employee_import(osv.osv):
    _name = "employee.import"
    
    _columns = {        
        'file': fields.binary('File', help='Choose file Excel'),
        'file_name':  fields.char('Filename', 100, readonly=True),
    }
    
    
    def read_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents=recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            for row in range(sh.nrows):
                if sh.cell(row, 0).value == u'Tên nhân viên':
                    flag = True
                    continue
                if flag == True:
                    em_name = sh.cell(row, 0).value
                    country = sh.cell(row, 1).value
                    id_number = int(sh.cell(row, 2).value)
                    id_date = sh.cell(row, 3).value
                    id_place = sh.cell(row, 4).value
                    birth_date = sh.cell(row, 5).value
                    email = sh.cell(row, 6).value
                    department = sh.cell(row, 7).value
                    job_name = sh.cell(row, 8).value
                    gender = sh.cell(row, 9).value
                    birth_place = sh.cell(row, 10).value
                    address = sh.cell(row, 11).value
                    country_ids = self.pool.get('res.country').search(cr, uid, [('name', '=', country)])
                    country_id = country_ids[0]
                    department_ids = self.pool.get('hr.department').search(cr, uid, [('name', '=', department)])
                    department_id = department_ids[0]
                    job_ids = self.pool.get('hr.job').search(cr, uid, [('name', '=', job_name)])
                    job_id = job_ids[0]
                    
                    res_employee_information_line = { 
                        'name': em_name,
                        'country_id': country_id,
                        'identification_id': id_number,
                        'identification_date_issue': str(datetime.date.fromordinal(DATEOFFSET + int(id_date))),
                        'identification_place_issue': id_place,
                        'birthday': str(datetime.date.fromordinal(DATEOFFSET + int(birth_date))),
                        'work_email': email,
                        'department_id': department_id,
                        'job_id': job_id,
                        'gender': gender,
                        'place_of_birth': birth_place,
                        'notes': address
                    }
                    self.pool.get('hr.employee').create(cr, uid, res_employee_information_line)
    
        return True
