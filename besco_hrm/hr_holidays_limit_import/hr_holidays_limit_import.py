# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api
import time

from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import datetime
import base64

from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook,xldate_as_tuple
from compiler.syntax import check
from openerp.exceptions import UserError, AccessError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

DATEOFFSET = 693594

class hr_holidays_limit_import(osv.osv):
    _name = 'hr.holidays.limit.import'
    
    _columns = {
        'start_date': fields.date('Date From', required=True),
        'end_date': fields.date('Date To', required=True),
        'user_import_id': fields.many2one('res.users', 'User Import', readonly=True),
        'import_date': fields.date('Import Date', readonly=True),
        
        'file': fields.binary('File', help='Choose file Excel'),
        'file_name':  fields.char('Filename', 100, readonly=True),
        
        'hr_holidays_status_id': fields.many2one('hr.holidays.status', 'Leave Type', required=True),
        
        'hr_holidays_limit_import_line_ids': fields.one2many('hr.holidays.limit.import.line', 'hr_holidays_limit_import_id', string='Holidays Limit'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('read', 'Read File'),
            ('waiting', 'Waiting for Import'),
            ('done', 'Done')
            ], string='Status', readonly=True, select=True, copy=False, default='draft')
    }
    
    _defaults = {
        'start_date': lambda *a: time.strftime('%Y-%m-01'),
        'end_date': lambda *a: str(datetime.datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        'import_date': lambda *a: str(datetime.datetime.now()),
        'user_import_id':lambda self, cr, uid, ctx=None: uid
    }
    
    def add_line(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        this.state = 'read'
        cr.execute("""DELETE FROM hr_holidays_limit_import_line WHERE hr_holidays_limit_import_id = %s"""%this.id)
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise UserError(_('Warning!'), str(e))
        if sh:
            for row in range(sh.nrows):
                if sh.cell(row,0).value =='Code':
                    flag = True
                    continue
                if flag==True:
                    employee_code = sh.cell(row,0).value
                    number_of_dates = sh.cell(row,2).value
                    
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code','=',employee_code)])  
                    if len(employee_ids) == 0:
                        raise UserError(_("Employee: '%s' do not exists.")%employee_code)
                    employee_obj = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
                    holidays_status_obj = self.pool.get('hr.holidays.status').browse(cr, uid, this.hr_holidays_status_id.id)
                    if holidays_status_obj.limit:
                        raise UserError(_("Leave Type must be set Allow to Override Limit is False"))
                    
                    if not number_of_dates:
                        number_of_dates = 0
                    import_line = {'employee_id': employee_obj.id,
                                   'number_of_dates': number_of_dates,
                                   'hr_holidays_limit_import_id': this.id,
                                   }
                    self.pool.get('hr.holidays.limit.import.line').create(cr, uid, import_line)
                    continue
                
    def reset_to_draft(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        this.state = 'draft'
        
    def read_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        this.state = 'done'
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            for row in range(sh.nrows):
                if sh.cell(row,0).value =='Code':
                    flag = True
                    continue
                if flag==True:
                    employee_code = sh.cell(row,0).value
                    number_of_dates = sh.cell(row,2).value
                    
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code','=',employee_code)])
                    hr_holidays_pool = self.pool.get('hr.holidays')
                    employee_obj = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
                    
                    if not number_of_dates:
                        number_of_dates = 0.0
                    
                    if number_of_dates > 0.0:
                        import_line = {
                            'name': 'Annual Leaves (' + employee_obj.name + ')',
                            'holiday_status_id': this.hr_holidays_status_id.id,
                            'employee_id': employee_obj.id, 
                            'type':'add',
                            'date_from': this.import_date,
                            'number_of_days_temp':number_of_dates,
                            'no_send_email': True,
                            'state': 'validate'
                          }
                        new_id = hr_holidays_pool.create(cr, uid, import_line)
                        hr_holidays_obj = hr_holidays_pool.browse(cr, uid, new_id)
                        hr_holidays_obj.write({'state':'validate', 'no_send_email': True})
                    continue

class hr_holidays_limit_import_line(osv.osv):
    _name = 'hr.holidays.limit.import.line'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'number_of_dates': fields.float('Number of Dates'),
        'hr_holidays_limit_import_id': fields.many2one('hr.holidays.limit.import', 'HR Holidays Limit Import'),
    }