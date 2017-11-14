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
import pytz
DATEOFFSET = 693594

class general_hr_attendance_import(osv.osv):
    _name = 'hr.attendance.import'
    
    _columns = {
        'name': fields.char('name'),
        'start_date': fields.date('Date From', readonly=True),
        'end_date': fields.date('Date To', readonly=True),
        'user_import_id': fields.many2one('res.users', 'User Import', readonly=True),
        'import_date': fields.datetime('Import Date', readonly=True),
        
        'file': fields.binary('File', help='Choose file Excel'),
        'file_name':  fields.char('Filename', 100, readonly=True),
        
        'hr_attendance_ids': fields.one2many('hr.attendance', 'hr_attendance_import_id', string='HR Attendance'),
        'hr_attendance_import_line_ids': fields.one2many('hr.attendance.import.line', 'hr_attendance_import_id', string='HR Attendance'),
        'company_id': fields.many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('general.hr.timesheet'),required=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('read', 'Read File'),
            ('waiting', 'Waiting for Import'),
            ('error', 'Error'),
            ('done', 'Done')
            ], string='Status', readonly=True, select=True, copy=False, default='draft'),
    }
    
    _defaults = {
#         'start_date': lambda *a: time.strftime('%Y-%m-01'),
#         'end_date': lambda *a: str(datetime.datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
        'import_date': lambda *a: str(datetime.datetime.now()),
        'user_import_id':lambda self, cr, uid, ctx=None: uid
    }
    
    @api.multi
    def edit_error(self):
        self.state = 'waiting'
    
    def check_null(self, string):
        if len(string) == 0:
            return 0.0
        else: return string
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = str(record.import_date)
            name = 'Import Attendance - ' + name[8:10]+'/'+name[5:7]+'/'+name[0:4]
            res.append((record.id, name))
        return res
    
    def add_line(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        this.state = 'read'
        cr.execute("""DELETE FROM hr_attendance_import_line WHERE hr_attendance_import_id = %s"""%this.id)
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise UserError(_(str(e)))
        if sh:
            for row in range(sh.nrows):
                if sh.cell(row,0).value =='Code':
                    flag = True
                    continue
                if flag==True:
                    employee_code = sh.cell(row,0).value
                    date = sh.cell(row,2).value
                    time_in = sh.cell(row,3).value
                    time_out = sh.cell(row,4).value 
                    schedule = sh.cell(row,5).value 
                    date_in = date_out = False
                    error_log = ''
                    res_user = self.pool.get('res.users')

                    if time_in:
                        date_in = res_user._convert_datetime_to_utc(cr, uid, str(datetime.date.fromordinal(DATEOFFSET + int(date))) + ' ' + str(datetime.timedelta(time_in)))
                    else:
                        date_in = res_user._convert_datetime_to_utc(cr, uid, str(datetime.date.fromordinal(DATEOFFSET + int(date))) + ' 00:00:00')
                    if time_out:
                        date_out = res_user._convert_datetime_to_utc(cr, uid, str(datetime.date.fromordinal(DATEOFFSET + int(date))) + ' ' + str(datetime.timedelta(time_out)))
                    else:
                        date_out = res_user._convert_datetime_to_utc(cr, uid, str(datetime.date.fromordinal(DATEOFFSET + int(date))) + ' 00:00:00')
#                     if not time_in or not time_out:
#                         note = 'Swipe one way'
#                     if not time_in and not time_out:
#                         note = 'No Record'
#                     if error_log != '':
#                         is_error = True
                    import_line = {'code': employee_code,
                                   'date': date,
#                                    'time_in_file': time_in,
#                                    'time_out_file': time_out,
                                   'time_in': date_in,
                                   'time_out': date_out,
                                   'hr_attendance_import_id': this.id,
                                   'schedule_name': schedule, 
                                   'is_error': True,
                                   }
                    self.pool.get('hr.attendance.import.line').create(cr, uid, import_line)
                    continue
                
    def reset_to_draft(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        this.state = 'draft'
        
    def create_response_and_send_mail(self, cr, uid, ids, partner_id, content, auto_commit=False, context=None):
        """ Create one mail by recipients and replace __URL__ by link with identification token """
        # post the message
        if context is None:
            context = {}
        mail_mail_obj = self.pool.get('mail.mail')   
        values = {
            'model': None,
            'res_id': None,
            'subject': 'Your Attendance has problem!',
            'body': content,
            'body_html': content.replace("(No Record)", '<h4 style="color:rgb(255,0,0);display: inline;">(No Record)</h4>'),
            'parent_id': None,
            'auto_delete': True,
        }
        if partner_id:
            values['recipient_ids'] = [(4, partner_id)]
        else:
            values['email_to'] = 'test@besco.vn'
        mail_id = mail_mail_obj.create(cr, uid, values, context=context)
        mail_mail_obj.send(cr, uid, [mail_id], auto_commit=auto_commit, context=context)
            
    def perdelta(self, start, end):
        curr = start
        while curr < end:
            yield curr
            curr += timedelta(days=1)
            
    def merge_datetime(self, date, time):
        #date: datetime with date
        #time: float
        res_user = self.env['res.users']
        result = res_user._convert_datetime_to_utc(str(date)[0:10] + ' ' + str(int(time)) + ':00:00')
        if (time - int(time)) != 0:
            min = (time - int(time)) * 60
            result = res_user._convert_datetime_to_utc(str(date)[0:10] + ' ' + str(int(time)) + ':' + str(int(min)) +  ':00')
        return result
    
    @api.model
    def cron_attendance_import(self,ids=None):
        self.read_file(ids)
    
    def select_holidays(self, emp_id, date_select, contract_ids):
        res = []
        sql_single = """SELECT date_from, date_to, holiday_status_id, id FROM hr_holidays WHERE '%s' BETWEEN to_char(date_from, 'yyyy-mm-dd') AND to_char(date_to, 'yyyy-mm-dd') AND employee_id = %s AND number_of_days_temp = 1"""%(str(date_select), emp_id)
        self.env.cr.execute(sql_single)        
        single = self.env.cr.fetchall()
        
        employee_obj = self.env['hr.employee'].browse(emp_id)
        if single:
            holiday_status = self.env['hr.holidays.status'].browse(single[0][2])
            res = {'date_from': datetime.datetime.strptime(single[0][0], DATETIME_FORMAT),
                    'date_to': datetime.datetime.strptime(single[0][1], DATETIME_FORMAT),
                    'holiday_status_id': single[0][2],
                    'hr_holidays_id': single[0][3],
                    'long_date': False,
                    'is_reason': holiday_status.reason,
                    }
            return res
        sql_multi = """SELECT date_from, date_to, holiday_status_id, id FROM hr_holidays WHERE '%s' BETWEEN to_char(date_from, 'yyyy-mm-dd') AND to_char(date_to, 'yyyy-mm-dd') AND employee_id = %s AND number_of_days_temp > 1"""%(str(date_select), emp_id)
        self.env.cr.execute(sql_multi)        
        multi = self.env.cr.fetchall()
        if multi:
            for i in multi:
                res.append({'date_from': i[0],
                            'date_to': i[1],
                            'holiday_status_id': i[2],
                            'hr_holidays_id': i[3],
                            })
            #Get time_in/time_out in Working Time
            dayofweek = str(int(date_select.strftime("%w")) - 1) 
            res_user = self.env['res.users']
            user_obj = self.env['res.users'].browse(self.env.user.id)
#            
            contract_obj = self.env['hr.contract'].browse(contract_ids)
            resource_calendar_pool = self.env['resource.calendar'].browse(contract_obj.working_hours.id)
            resource_calendar_attendance_ids = self.env['resource.calendar.attendance'].search([('calendar_id', '=', resource_calendar_pool.id), ('dayofweek','=',dayofweek)])
            if len(resource_calendar_attendance_ids) > 0:
                resource_calendar_attendance_obj = self.env['resource.calendar.attendance'].browse(resource_calendar_attendance_ids[0].id)
            else: 
                raise UserError(_("Contract '%s' of employee: '%s-%s' has not Working Schedule or date (%s) in file Import is out of Working Time.")%(contract_obj.name, employee_obj.code ,employee_obj.name, str(date_select)))
            
            time_in = resource_calendar_attendance_obj.hour_from
            time_out = resource_calendar_attendance_obj.hour_to
            
            #get holiday_status
            holiday_status = self.env['hr.holidays.status'].browse(res[0]['holiday_status_id'])
            
            #Leave > 1
            date_from = datetime.datetime.strptime(str(res[0]['date_from']), DATETIME_FORMAT)
            date_to = datetime.datetime.strptime(str(res[0]['date_to']), DATETIME_FORMAT)
            
            date_from_for = datetime.datetime.strptime(str(res[0]['date_from'])[0:10], DATE_FORMAT)
            date_to_for = datetime.datetime.strptime(str(res[0]['date_to'])[0:10], DATE_FORMAT)
            list_date = []
            for i in self.perdelta(date_from_for, date_to_for):
                list_date.append(i.strftime('%Y-%m-%d'))
            if len(list_date) == 1:
                res = {str(date_from_for)[0:10]: {'date_from': date_from.strftime(DATETIME_FORMAT),
                                                  'date_to': self.merge_datetime(date_from_for, time_out),
                                                  'long_date': False,
                                                  'is_reason': holiday_status.reason,
                                                  'hr_holidays_id': res[0]['hr_holidays_id']
                                                  },
                        str(date_to_for)[0:10]: {'date_from': self.merge_datetime(date_to_for, time_in),
                                                  'date_to': date_to.strftime(DATETIME_FORMAT),
                                                  'long_date': False,
                                                  'is_reason': holiday_status.reason,
                                                  'hr_holidays_id': res[0]['hr_holidays_id']
                                                  }
                       }
                a=res[str(date_select)]
                return res[str(date_select)] 
            elif len(list_date) > 1:
                date_from_for
                date_to_for
                if str(date_select) == str(date_from_for)[0:10]:
                    return {'date_from': date_from.strftime(DATETIME_FORMAT),
                            'date_to': self.merge_datetime(date_from_for, time_out),
                            'long_date': True,
                            'is_reason': holiday_status.reason,
                            'hr_holidays_id': res[0]['hr_holidays_id']
                            }
                elif str(date_select) == str(date_to_for)[0:10]:
                    return {'date_from': self.merge_datetime(date_to_for, time_in),
                            'date_to': date_to.strftime(DATETIME_FORMAT),
                            'long_date': True,
                            'is_reason': holiday_status.reason,
                            'hr_holidays_id': res[0]['hr_holidays_id']
                            }
                else:
                    return {'date_from': self.merge_datetime(date_select, time_in),
                            'date_to': self.merge_datetime(date_select, time_out),
                            'long_date': True,
                            'is_reason': holiday_status.reason,
                            'hr_holidays_id': res[0]['hr_holidays_id']
                            }
            
        return False
    
    def read_file(self, cr, uid, ids, context=None):
        active_tz = pytz.timezone("Asia/Saigon")
        this = self.browse(cr, uid, ids[0])
        res_user = self.pool.get('res.users')
        date_from = date_to = False
        for row in this.hr_attendance_import_line_ids:
            print row
            date_from = date_to = datetime.date.fromordinal(DATEOFFSET + int(row.date))
            break
        context_get_contract = {'attendance_import': True}
        for row in this.hr_attendance_import_line_ids:
            print row
            if row.is_error:
                employee_code = row.code
                date = str(res_user._convert_user_datetime(cr, uid, row.time_in))[0:10]
                if str(res_user._convert_user_datetime(cr, uid, row.time_in)).split(' ')[1] == '00:00:00+07:00':
                    time_in = False
                else:
                    time_in = row.time_in
                if str(res_user._convert_user_datetime(cr, uid, row.time_out)).split(' ')[1] == '00:00:00+07:00':
                    time_out = False
                else:
                    time_out = row.time_out
                    
                error_log = ''

#                 date_import_line = datetime.date.fromordinal(DATEOFFSET + int(row.date))
                date_import_line = datetime.datetime.strptime(date, DATE_FORMAT).date()
                
                if date_import_line < date_from:
                    date_from = date_import_line
                if date_import_line > date_to:
                    date_to = date_import_line
                
                sql_emp = """SELECT id FROM hr_employee WHERE code = '%s'"""%employee_code
                cr.execute(sql_emp)
                employee_ids = cr.fetchone()
                if not employee_ids:
                    error_log = "- Employee do not exists."
                    row.write({'error_log': error_log, 'status': 'fail'})
                    continue
                
                if time_in and time_out and time_in == time_out:
                    error_log += "- Time In must be different Time Out."
                
                employee_obj = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
                
                #check Resigned 
                if employee_obj.resigned_date and datetime.datetime.strptime(employee_obj.resigned_date, DATE_FORMAT).date() <= date_import_line:
                    if error_log != '':
                        error_log += "\n- Employee was resigned on %s."%str(date_import_line)
                    else:
                        error_log += "- Employee was resigned on %s."%str(date_import_line)
                #get Contract (just only Trial/Official)
                dayofweek = str(int(date_import_line.strftime("%w")) - 1)
                contract_ids = self.pool.get('hr.attendance').get_active_contracts(cr, uid, ids, employee_obj.id, date_import_line, context=context_get_contract)
                if contract_ids == 'error':
                    if error_log != '':
                        error_log += "\n- Too many active contracts on %s."%(str(date_import_line))
                    else:
                        error_log += "- Too many active contracts on %s."%(str(date_import_line))
                if not contract_ids:
                    if error_log != '':
                        error_log += "\n- Employee has not Contract on %s."%str(date_import_line)
                    else: 
                        error_log += "- Employee has not Contract on %s."%str(date_import_line)
                if row.schedule_name:
                    resource_calendar_ids = self.pool.get('resource.calendar').search(cr, uid, [('name', '=', row.schedule_name)])
                    if len(resource_calendar_ids) > 0:
#                         resource_calendar_attendance_obj = self.pool.get('resource.calendar.attendance').browse(cr, uid, resource_calendar_attendance_ids[0])
                        resource_calendar_pool = self.pool.get('resource.calendar').browse(cr, uid, resource_calendar_ids[0])
                        resource_calendar_attendance_ids = self.pool.get('resource.calendar.attendance').search(cr, uid, [('calendar_id', '=', resource_calendar_pool.id), ('dayofweek','=',dayofweek)])
                        if len(resource_calendar_attendance_ids) == 0:
                            if error_log != '':
                                error_log += "\n- Date (%s) in file Import is out of Working Time."%(str(date_import_line))
                            else: 
                                error_log += "- Date (%s) in file Import is out of Working Time."%(str(date_import_line))
                    else: 
                        if error_log != '':
                            error_log += "\n- Priority Working Schedule is not exist"
                        else: 
                            error_log += "- Priority Working Schedule is not exist"
                            
                elif len(contract_ids) == 1:
                    contract_obj = self.pool.get('hr.contract').browse(cr, uid, contract_ids)
                    resource_calendar_pool = self.pool.get('resource.calendar').browse(cr, uid, contract_obj.working_hours.id)
                    resource_calendar_attendance_ids = self.pool.get('resource.calendar.attendance').search(cr, uid, [('calendar_id', '=', resource_calendar_pool.id), ('dayofweek','=',dayofweek)])
                    if len(resource_calendar_attendance_ids) > 0:
                        resource_calendar_attendance_obj = self.pool.get('resource.calendar.attendance').browse(cr, uid, resource_calendar_attendance_ids[0])
                    else: 
                        if error_log != '':
                            error_log += "\n- Contract '%s' of this employee has not Working Schedule or date (%s) in file Import is out of Working Time."%(contract_obj.name,str(date_import_line))
                        else: 
                            error_log += "- Contract '%s' of this employee has not Working Schedule or date (%s) in file Import is out of Working Time."%(contract_obj.name,str(date_import_line))
                
                #check duplicate
                cr.execute("""SELECT * FROM hr_attendance WHERE to_char(name, 'yyyy-mm-dd') = '%s' AND employee_id = %s AND schedule_id = %s AND (action='sign_in' OR action='action')"""%(str(date_import_line), employee_obj.id,resource_calendar_pool.id))
                result = cr.fetchone()
                if result:
                    if error_log != '':
                        error_log += "\n- Employee has attendance on %s."%str(date_import_line)
                    else: 
                        error_log += "- Employee has attendance on %s."%str(date_import_line)
                
                if error_log != '':
                    row.write({'employee_name': employee_obj.name, 'error_log': error_log, 'status': 'fail'})
                    continue
                row.write({'employee_name': employee_obj.name, 'is_error': False, 'status': 'done'})
                
                #merge with LEAVE
                res_holiday = this.select_holidays(employee_obj.id, date_import_line, contract_ids)
                res_holiday = False
                #END merge
                contract_obj = self.pool.get('hr.contract').browse(cr, uid, contract_ids)
                if contract_obj.no_attendance:
                    if not time_in and not time_out:
                        time_in = resource_calendar_attendance_obj.hour_from
                        end_datetime = resource_calendar_attendance_obj.hour_to
                        note_with_name = ''
                        if employee_obj.work_email:
                            account_name = employee_obj.work_email.split('@')
                            note_with_name = ' - ' + account_name[0] + ' - '
                        attendance_line_in = {
                            'employee_id': employee_ids[0],
                            'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                            'end_datetime': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(end_datetime)) + ':00:00'),
                            'action': 'action',
                            'notes': note_with_name + 'No Record',
                            'color': 'red',
                            'duplicate_with_leave': False,
                            'schedule_id': resource_calendar_pool.id
                        }
                        hr_attendance_id = self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)
                        partner = employee_obj.user_id.partner_id
                        content = "Your attendance has problem (No Record) in " + str(date_import_line) + ". Please review your Attendances or your Leaves. Contact with your Manager if you need."
                        this.create_response_and_send_mail(partner.id, content)
                        continue
                    time_in = resource_calendar_attendance_obj.hour_from
                    attendance_line_in = {
                        'employee_id': employee_ids[0],
                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                        'action': 'sign_in',
                        'color': 'white',
                        'schedule_id': resource_calendar_pool.id
                    }
                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)
                    time_out = resource_calendar_attendance_obj.hour_to
                    attendance_line_out = {
                        'employee_id': employee_ids[0],
                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                        'action': 'sign_out',
                        'color': 'white'
                    }
                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                else:
                    if not res_holiday:
                        if not time_in and not time_out:
                            time_in = resource_calendar_attendance_obj.hour_from
                            end_datetime = resource_calendar_attendance_obj.hour_to
                            note_with_name = ''
                            if employee_obj.work_email:
                                account_name = employee_obj.work_email.split('@')
                                note_with_name = ' - ' + account_name[0] + ' - '
                            attendance_line_in = {
                                'employee_id': employee_ids[0],
                                'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                'end_datetime': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(end_datetime)) + ':00:00'),
                                'action': 'action',
                                'notes': note_with_name + 'No Record',
                                'color': 'red',
                                'duplicate_with_leave': False,
                                'schedule_id': resource_calendar_pool.id
                            }
                            hr_attendance_id = self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)
#                                 this.send_mail(hr_attendance_id, employee_ids[0])
                            partner = employee_obj.user_id.partner_id
                            content = "Your attendance has problem (No Record) in " + str(date_import_line) + ". Please review your Attendances or your Leaves. Contact with your Manager if you need."
                            this.create_response_and_send_mail(partner.id, content)
                            continue
                        if not time_in:
#                                 time_in = resource_calendar_attendance_obj.hour_from
                            time_in = 0.0
                            attendance_line_in = {
                                'employee_id': employee_ids[0],
                                'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                'attendance_once_sign': True,
                                'action': 'sign_in',
                                'notes': 'Swipe one way',
                                'color': 'cyanosis',
                                'duplicate_with_leave': False,
                                'schedule_id': resource_calendar_pool.id
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                            attendance_line_out = {
                                'employee_id': employee_ids[0],
                                'name': time_out,
                                'action': 'sign_out',
                                'color': 'cyanosis',
                                'duplicate_with_leave': False
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                            continue
                        if not time_out:
                            attendance_line_in = {
                                'employee_id': employee_ids[0],
                                'name': time_in,
                                'attendance_once_sign': True,
                                'action': 'sign_in',
                                'notes': 'Swipe one way',
                                'color': 'cyanosis',
                                'duplicate_with_leave': False
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

#                                 time_out = resource_calendar_attendance_obj.hour_to
                            time_out = 23.9
                            attendance_line_out = {
                                'employee_id': employee_ids[0],
                                'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                                'action': 'sign_out',
                                'color': 'cyanosis',
                                'duplicate_with_leave': False
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                            continue
                        if time_in and time_out:

                            attendance_line_in = {
                                'employee_id': employee_ids[0],
                                'name': time_in,
                                'action': 'sign_in',
                                'color': 'white',
                                'duplicate_with_leave': False,
                                'schedule_id': resource_calendar_pool.id
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                            attendance_line_out = {
                                'employee_id': employee_ids[0],
                                'name': time_out,
                                'action': 'sign_out',
                                'color': 'white','duplicate_with_leave': False
                            }
                            self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                            continue
                    else:
                        if res_holiday['long_date']:
                            if res_holiday['is_reason']:
                                hr_holidays_obj = self.pool.get('hr.holidays').browse(cr, uid, res_holiday['hr_holidays_id'])
                                if not time_in and not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_holiday['date_from'],
                                        'action': 'sign_in',
                                        'color': 'white',
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name,
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_holiday['date_to'],
                                        'action': 'sign_out',
                                        'color': 'white',
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_in:
#                                         time_in = resource_calendar_attendance_obj.hour_from
                                    time_in = 0.0
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    time_out = 23.9
#                                         time_out = resource_calendar_attendance_obj.hour_to
                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if time_in and time_out:

                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'action': 'sign_in',
                                        'color': 'orange',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name,
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'orange',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                            else:
                                hr_holidays_obj = self.pool.get('hr.holidays').browse(cr, uid, res_holiday['hr_holidays_id'])
                                if not time_in and not time_out:
                                    continue
                                if not time_in:
                                    time_in = 0.0
#                                         time_in = resource_calendar_attendance_obj.hour_from
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    time_out = 23.9
#                                         time_out = resource_calendar_attendance_obj.hour_to
                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if time_in and time_out:

                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'action': 'sign_in',
                                        'color': 'orange',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name,
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'orange',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                        else: # nửa ngày
                            if res_holiday['is_reason']:
                                hr_holidays_obj = self.pool.get('hr.holidays').browse(cr, uid, res_holiday['hr_holidays_id'])
                                if not time_in and not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_holiday['date_from'],
                                        'action': 'sign_in',
                                        'color': 'white',
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name,
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_holiday['date_to'],
                                        'action': 'sign_out',
                                        'color': 'white',
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_in:
                                    time_in = 0.0
#                                         time_in = resource_calendar_attendance_obj.hour_from
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    time_out = 23.9
#                                         time_out = resource_calendar_attendance_obj.hour_to
                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if time_in and time_out:
                                    sign_in = time_in
                                    sign_out = time_out
                                    if sign_in > str(res_holiday['date_from']):
                                        sign_in = res_holiday['date_from']
                                    if sign_out < str(res_holiday['date_to']):
                                        sign_out = res_holiday['date_to']

                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': sign_in,
                                        'action': 'sign_in',
                                        'color': 'white',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name,
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': sign_out,
                                        'action': 'sign_out',
                                        'color': 'white',
                                        'duplicate_with_leave': True,
                                        'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' with reason: ' + hr_holidays_obj.reason_id.name
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                            else:
                                hr_holidays_obj = self.pool.get('hr.holidays').browse(cr, uid, res_holiday['hr_holidays_id'])
                                if not time_in and not time_out:
                                    time_in = resource_calendar_attendance_obj.hour_from
                                    end_datetime = resource_calendar_attendance_obj.hour_to
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                        'end_datetime': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(end_datetime)) + ':00:00'),
                                        'action': 'action',
                                        'notes': 'No Record. ' + 'Leave type: ' + hr_holidays_obj.holiday_status_id.name + ' in ' + str(hr_holidays_obj.hours) + ' hour(s)',
                                        'color': 'red',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    hr_attendance_id = self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)
                                    partner = employee_obj.user_id.partner_id
                                    content = "Your attendance has problem (No Record) in " + str(date_import_line) + ". Please review your Attendances or your Leaves. Contact with your Manager if you need."
                                    this.create_response_and_send_mail(partner.id, content)
                                    continue
                                if not time_in:
                                    time_in = 0.0
#                                         time_in = resource_calendar_attendance_obj.hour_from
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_in)) + ':00:00'),
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': time_out,
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if not time_out:
                                    attendance_line_in = {
                                        'employee_id': employee_ids[0],
                                        'name': time_in,
                                        'attendance_once_sign': True,
                                        'action': 'sign_in',
                                        'notes': 'Swipe one way',
                                        'color': 'cyanosis',
                                        'schedule_id': resource_calendar_pool.id
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                    time_out = 23.9
#                                         time_out = resource_calendar_attendance_obj.hour_to
                                    attendance_line_out = {
                                        'employee_id': employee_ids[0],
                                        'name': res_user._convert_datetime_to_utc(cr, uid, str(date_import_line) + ' ' + str(int(time_out)) + ':00:00'),
                                        'action': 'sign_out',
                                        'color': 'cyanosis'
                                    }
                                    self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
                                if time_in and time_out:
                                    sign_in = time_in
                                    sign_out = time_out

                                    if sign_in >= str(res_holiday['date_to']):
                                        attendance_line_in = {
                                            'employee_id': employee_ids[0],
                                            'name': sign_in,
                                            'action': 'sign_in',
                                            'color': 'white',
                                            'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name,
                                            'schedule_id': resource_calendar_pool.id
                                        }
                                        self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                        attendance_line_out = {
                                            'employee_id': employee_ids[0],
                                            'name': sign_out,
                                            'action': 'sign_out',
                                            'color': 'white',
                                            'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name
                                        }
                                        self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    else:
                                        attendance_line_in = {
                                            'employee_id': employee_ids[0],
                                            'name': sign_in,
                                            'action': 'sign_in',
                                            'color': 'orange',
                                            'duplicate_with_leave': True,
                                            'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name,
                                            'schedule_id': resource_calendar_pool.id
                                        }
                                        self.pool.get('hr.attendance').create(cr, uid, attendance_line_in)

                                        attendance_line_out = {
                                            'employee_id': employee_ids[0],
                                            'name': sign_out,
                                            'action': 'sign_out',
                                            'color': 'orange',
                                            'duplicate_with_leave': True,
                                            'notes_leave': 'Leave type: ' + hr_holidays_obj.holiday_status_id.name
                                        }
                                        self.pool.get('hr.attendance').create(cr, uid, attendance_line_out)
                                    continue
        this.state = 'done'  
        this.start_date = date_from
        this.end_date = date_to       
        return True
    
class hr_attendance(osv.osv):
    _inherit = 'hr.attendance'
    
    _columns = {
        'hr_attendance_import_id': fields.many2one('hr.attendance.import', 'HR Attendance Import'),
    }
    
    def create(self, cr, uid, vals, context=None):
        return super(hr_attendance, self).create(cr, uid, vals, context=context)
    
class general_hr_attendance_import_line(osv.osv):
    _name = 'hr.attendance.import.line'
    _order = 'error_log asc, employee_id asc, time_in asc'
    
    _columns = {
        'code': fields.char('Code'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'schedule_name': fields.char('Priority Working Schedule'),
        'schedule_id': fields.many2one('resource.calendar', 'Priority Working Schedule'),
        'employee_name': fields.char('Employee'),
        'date':fields.float('Date'),
        'time_in_file': fields.float('Time In'),
        'time_out_file': fields.float('Time Out'),
        'time_in': fields.datetime('Time In'),
        'time_out': fields.datetime('Time Out'),
        'note': fields.char('Note'),
        'state': fields.selection([('waiting', 'Waiting'), ('done', 'Done')], 'State'),
        'error_log': fields.char('Log', readonly=True),
        'hr_attendance_import_id': fields.many2one('HR Attendance Import'),
        'is_error': fields.boolean('Is Error'),
        'status': fields.selection([
            ('fail', 'Fail'),
            ('done', 'Done')
            ], string='Status', readonly=True),
    } 