# -*- coding: utf-8 -*-
from operator import itemgetter

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil import relativedelta
import time

import base64
from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook, xldate_as_tuple
from _sqlite3 import Row
from errno import EROFS
from _ast import Store
from docutils.nodes import Invisible
from lxml import etree

class general_hr_timesheet(models.Model):
    _name = 'general.hr.timesheet'
    _description = 'BESCO HR Timesheet'
    _order = "state ASC, work_date DESC"

    @api.model
    def _default_hr_team_id(self): 
        user_id = self._uid
        hr_team_id = False
        if user_id != 1:
            employee_id = self.env['res.users'].browse(user_id).employee_id.id or False
            hr_team_id = self.env['hr.team'].search([('employee_id','=',employee_id)], limit=1)
        return hr_team_id 
    
    @api.depends('work_date')
    def _compute_date(self):
        for timesheets in self:
            work_date = datetime.strptime(timesheets.work_date, '%Y-%m-%d').date()
            day = float(work_date.strftime('%d'))
            if day > 5:
                start_date = str(work_date + relativedelta.relativedelta(day=6)) or False
                end_date = str(work_date + relativedelta.relativedelta(months=+1, day=7)) or False
            else:
                start_date = str(work_date + relativedelta.relativedelta(months=-1, day=6)) or False
                end_date = str(work_date + relativedelta.relativedelta(day=7)) or False
                
            timesheets.update({'start_date': datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) or False,
                               'end_date': datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) or False})
            
    @api.depends('work_date')
    def _compute_dayofweek(self):
        for timesheet in self:
            self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (timesheet.work_date))
            result = self.env.cr.dictfetchall()
            dayofweek = result and result[0] and result[0]['dayofweek'] or False
            dayofweek = int(dayofweek - 1)
            timesheet.dayofweek = str(dayofweek)
            timesheet.work_date_to= timesheet.work_date
        
    @api.depends('hr_timesheet_line.hr_overtime_ids')
    def _compute_overtime(self):
        for timesheet in self:
            ot_requests = []
            for line in timesheet.hr_timesheet_line:
                for ot in line.hr_overtime_ids:
                    if ot.state != 'cancel':
                        ot_requests.append(ot.id)
            timesheet.update({'ot_count': len(ot_requests),'hr_overtime_ids': ot_requests})
            
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        ids = []
        res = super(general_hr_timesheet, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ['form']:
            doc = etree.XML(res['arch'])
             
            for node in doc.xpath("//field[@name='hr_team_id']"):
                
                if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "general_hr.group_employee_coach"):
                    employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('user_id.id','=',self.env.user.id)])
                    node.set('domain', "[('employee_id','in',"+str(employee_ids)+")]")
                
            xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
#         if view_type in ['tree']:
#             doc = etree.XML(res['arch'])
#             for node in doc.xpath("//field[@name='hr_team_id']"):
#                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "general_hr.group_employee_coach"):
#                     hr_team_ids = self.pool.get('hr.team').search(self.env.cr, SUPERUSER_ID, [('employee_id.user_id.id','=',self.env.user.id)])
#                     node.set('domain', "[('hr_team_id','in',"+str(hr_team_ids)+")]")
#                 
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
        print res
        return res
    
    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]}, default="New")
    work_date = fields.Date(string='Working Date', default=fields.Datetime.now, required=True, readonly=True, states={'draft': [('readonly', False)]})
    dayofweek = fields.Selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')],
                                 string='Day of Week', store=True, compute="_compute_dayofweek", default='0')
    
    type_timesheet = fields.Selection([('hour','Hour(s)'),('day','Day(s)')],
        string="Type of Timesheet", required=True, readonly=True, states={'draft': [('readonly', False)]}, default='hour')
    
#     type_timesheet = fields.Selection([('hour','Hour(s)'),('day','Day(s)'),('productivity'),('Productivity')],
#         string="Type of Timekeeping", required=True, readonly=True, states={'draft': [('readonly', False)]}, default='hour')

    state = fields.Selection([('draft', 'Draft'),('waiting', 'Waiting Approval'),('approve', 'Approved'),('cancel', 'Canceled'),('refuse', 'Refuse')],
        string='Status', readonly=True, select=True, copy=False, default='draft')
    
    start_date = fields.Date(compute='_compute_date', string='Date From', store=True,invisible=True)
    end_date = fields.Date(compute='_compute_date', string='Date To', store=True,invisible=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('general.hr.timesheet'),required=True)
    
    user_import_id = fields.Many2one('res.users', 'User Import', readonly=True, select=True, copy=False)
    user_approve_id = fields.Many2one('res.users', 'User Approve', readonly=True, select=True, copy=False)
    
    import_date = fields.Date('Import Date', readonly=True, copy=False)
    file = fields.Binary('File', help='Choose file Excel', readonly=True, states={'draft': [('readonly', False)]})
    file_name = fields.Char('Filename', readonly=True)
    
    hr_team_id = fields.Many2one('hr.team', string="HR TimeSheets Team", readonly=True, states={'draft': [('readonly', False)]}, default=_default_hr_team_id)
    
    hr_timesheet_line = fields.One2many('general.hr.timesheet.lines', 'hr_timesheet_id', string='Employee Timesheet Lines', readonly=True, states={'draft': [('readonly', False)]})
#     hr_timesheet_manager_lines_ids = fields.One2many('general.hr.timesheet.lines.manager', 'hr_timesheet_id', string='Manager Timesheet Lines', readonly=True, states={'draft': [('readonly', False)]})
    
    ot_count = fields.Integer(compute="_compute_overtime", string="OT Requests", store=True)
    hr_overtime_ids = fields.One2many('hr.overtime', 'hr_timesheet_id', string='Orvertime')
    force_working_time = fields.Many2one('resource.calendar',string='Working Time', required=True)
    work_date_to = fields.Date(string='Working Date To', default=fields.Datetime.now, required=True, readonly=True)
    
    @api.constrains('work_date')
    def _check_work_date(self):
        for timesheet in self:
            timesheet_ids = self.search([('work_date','=',timesheet.work_date),('id','!=',timesheet.id),('hr_team_id','=',timesheet.hr_team_id.id),('state','in',('waiting','approve')),('force_working_time','=',self.force_working_time.id)])
            if timesheet_ids:
                raise UserError(_("Working Date (%s) was exist.")%(timesheet.work_date))
            return True
    
    @api.multi
    def unlink(self):
        for timesheet in self:
            if timesheet.state not in ('draft', 'refuse'):
                raise UserError(_('You cannot delete this Employee Timesheet which is not in draft state.'))
        return super(general_hr_timesheet, self).unlink()
    
    @api.multi
    def button_confirm(self):
        if self.state == 'draft':
            timesheet_ids = self.search([('work_date','=',self.work_date),('id','!=',self.id),('state','=','waiting'),('hr_team_id','=',self.hr_team_id.id),('force_working_time','=',self.force_working_time.id)])
            if timesheet_ids:
                raise UserError(_("Working Date (%s) was exist.")%(self.work_date))
            
        if self.state == 'waiting':
            timesheet_ids = self.search([('work_date','=',self.work_date),('id','!=',self.id),('state','=','approve'),('hr_team_id','=',self.hr_team_id.id)])
            if timesheet_ids:
                raise UserError(_("Working Date (%s) was exist.")%(self.work_date))
            
        if not self.hr_timesheet_line:
            raise UserError(_('You cannot confirm this Employee Timesheet.'))
        
        for line in self.hr_timesheet_line:
            for orvertime in line.hr_overtime_ids:
                orvertime.update({'state':'validate'})
                orvertime.update({'state_timesheet':'approve'})
        self.write({'state': 'waiting'})
    
    @api.multi 
    def button_approve(self):
        self.button_confirm()
        timesheet_ids = self.search([('work_date','=',self.work_date),('id','!=',self.id),('state','=','approve'),('hr_team_id','=',self.hr_team_id.id),('force_working_time','=',self.force_working_time.id)])
        if timesheet_ids:
                raise UserError(_("Working Date (%s) was exist.")%(self.work_date))
        for line in self.hr_timesheet_line:
            for orvertime in line.hr_overtime_ids:
                orvertime.update({'state':'validate'})
                orvertime.update({'state_timesheet':'approve'})
        self.write({'state': 'approve', 'user_approve_id': self.env.uid})
    
    @api.multi
    def button_cancel(self):
        for line in self.hr_timesheet_line:
            for orvertime in line.hr_overtime_ids:
                orvertime.update({'state':'confirm'})
                orvertime.update({'state_timesheet':'draft'})
        self.write({'state': 'cancel'})
        
    @api.multi
    def button_refuse(self):
        for line in self.hr_timesheet_line:
            for orvertime in line.hr_overtime_ids:
                orvertime.update({'state':'confirm'})
                orvertime.update({'state_timesheet':'draft'})
        self.write({'state': 'draft'})
        
    @api.multi
    def button_set_to_draft(self):
        for line in self.hr_timesheet_line:
            for orvertime in line.hr_overtime_ids:
                orvertime.update({'state':'confirm'})
                orvertime.update({'state_timesheet':'draft'})
        self.write({'state': 'draft'})
        
    @api.onchange('hr_team_id')
    def onchange_force_woking_time(self):
        if self.hr_team_id:
            for line in self.hr_team_id.member_ids[0]:
                contract_ids=self.env['hr.contract'].search([('employee_id','=',line.id)],limit=1)
                self.update({'force_working_time': contract_ids.working_hours.id})
            if self._origin.id:
                self.env.cr.execute('''DELETE FROM general_hr_timesheet_lines WHERE hr_timesheet_id = %s''' % (self._origin.id))        
    
    #Minh
#     @api.multi
#     def button_ot_batches(self):
#         for line in self.hr_timesheet_line:
#             if line.real_worked - line.standard_worked > 0:
#                 tt_ot_wordked = line.real_worked - line.standard_worked
#                 overtime_type_ids= self.env['resource.calendar.overtime.type'].search([('calendar_id','=',line.shift_id.id)])
#                 if overtime_type_ids:
#                     for overtime_type in overtime_type_ids:
#                         if overtime_type.limit <= tt_ot_wordked:
#                             overtime= overtime_type.limit
#                         else:
#                             overtime= tt_ot_wordked
#                         overtime_type_id = overtime_type.overtime_type_id.id
#                         rates=self.env['hr.overtime.type'].search([('id','=',overtime_type_id)],limit=1)
#                         rate= rates.rate
#                         calculated_hours=round(rate * overtime / 100, 2)
#                         department_ids =self.env['hr.employee'].search([('id','=',line.employee_id.id)],limit=1)
#                         department_id=department_ids.department_id.id
#                         res_user = self.env['res.users']
#                         start_date = res_user._convert_user_datetime(line.sign_in)
#                         end_date =res_user. _convert_user_datetime(line.sign_out)
#                         
#                         res={'hr_timesheet_line_id': line.id or False, 'employee_id': line.employee_id.id or False,
#                         'overtime_type_id': overtime_type_id or False, 'rate': rate or 0.0,
#                         'department_id': department_id or False,'calculated_hours': calculated_hours or 0.0,'number_of_hours_temp': overtime or 0.0,
#                         'date_from': start_date or False, 'date_to': end_date or 0.0,
#                         'name': line.employee_id.name or False}
#                         hr_overtime_ids=self.env['hr.overtime'].search([('employee_id','=',line.employee_id.id),('hr_timesheet_line_id','=',line.id),('hr_timesheet_id','=',line.hr_timesheet_id.id)])
#                         if hr_overtime_ids:
#                             hr_overtime_ids.update(res)
#                         else :
#                             self.env['hr.overtime'].create(res)
#                         tt_ot_wordked = tt_ot_wordked - overtime_type.limit
#                         if tt_ot_wordked < 0:
#                             break 
#         return True   
    @api.multi
    def button_real_worked(self):
        if self.hr_timesheet_line:
            for i in self.hr_timesheet_line:
                i.real_worked = 8.0
        else:
            return True
        
    @api.multi
    def button_load_employee(self):
        res_user = self.env['res.users']
        work_date = datetime.strptime(self.work_date, '%Y-%m-%d').date()
        self.name = self.hr_team_id.name + ' - ' + str(work_date.strftime('%d/%m/%Y'))
        timesheet_line = []
        standard_worked = 0.0
        if self.hr_team_id:
            attendance_obj = self.env['hr.attendance']
            #self.env.cr.execute('''DELETE FROM general_hr_timesheet_lines WHERE hr_timesheet_id = %s''' % (self.id))
            if self.force_working_time:
                shift_ids = self.env['resource.calendar'].search([('id', '=', self.force_working_time.id)], limit=1)
            else:
                for line in self.hr_team_id.member_ids[0]:
                    contract_ids=self.env['hr.contract'].search([('employee_id','=',line.id)],limit=1)
                    shift_ids = self.env['resource.calendar'].search([('id', '=', contract_ids.working_hours.id)], limit=1)
            self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (self.work_date))
            result = self.env.cr.dictfetchall()
            dayofweek = result and result[0] and result[0]['dayofweek'] or False
            dayofweek = int(dayofweek - 1)
            type_day = 'normal'
            holiday_day_line = self.env['hr.holiday.day.line']
            if dayofweek == 6:
                holiday_ids = holiday_day_line.search([('date','=',self.work_date),('company_id','=',self.company_id.id)])
                if holiday_ids:
                    type_day = 'holiday'
                else:
                    type_day = 'sunday'
            else:
                holiday_ids = holiday_day_line.search([('date','=',self.work_date),('company_id','=',self.company_id.id)])
                if holiday_ids:
                    type_day = 'holiday'
            attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',shift_ids.id),('dayofweek','=',str(dayofweek))], limit=1)
            if type_day == 'holiday':
                standard_worked = 0.0
            else:
                if attendance_id.hour_to > attendance_id.hour_from:
                    standard_worked = attendance_id.hour_to - attendance_id.hour_from - shift_ids.break_hours
                    self.work_date_to = self.work_date
                elif attendance_id.hour_to < attendance_id.hour_from:
                    work_date = datetime.strptime(self.work_date, '%Y-%m-%d')
                    date = attendance_id.hour_from - attendance_id.hour_to
                    standard_worked = date -(date - 12)*2 - shift_ids.break_hours
                    self.work_date_to=str(work_date + relativedelta.relativedelta(days=+1))
                
            rate= attendance_id.rate
            for line in self.hr_team_id.member_ids:
                #Minh 
                if self.force_working_time.id:
                    force_working_time=self.force_working_time.id
                else :
                    force_working_time = 0
                duration=0.0
                timesheet_lines_obj=self.env['general.hr.timesheet.lines']
                self.env.cr.execute('''SELECT SIGN_OUT_ID,ID,DURATION,END_DATETIME FROM hr_attendance WHERE date(timezone('UTC',name::timestamp)) ='%s' and EMPLOYEE_ID='%s' and ACTION='sign_in' and attendance_once_sign ='f' and schedule_id= %s ; '''% (self.work_date,line.id,force_working_time))
                result = self.env.cr.dictfetchall()
                if result:
                    duration=result[0]['duration']
                    sign_in_id=result[0]['id']
                    sign_out_id=result[0]['sign_out_id']
                    overtime = 0.0
                    employee_obj = self.env['hr.employee'].browse(line.id)
                    hr_overtime_ids=self.env['hr.overtime'].search([('employee_id','=',line.id),('date_from','=',self.work_date),('hr_timesheet_id','=',self.id)])
                    if hr_overtime_ids:
                        overtime=hr_overtime_ids.number_of_hours_temp
                    timesheet_line_ids = timesheet_lines_obj.search([('employee_id','=',line.id),('work_date','=',self.work_date),('sign_in_id','=',sign_in_id),('sign_out_id','=',sign_out_id)])
                    if timesheet_line_ids:
                        if len(timesheet_line_ids) > 1:
                            raise UserError(_("Employee '%s' was duplicated.")%employee_obj.name_related)
                        timesheet_line_ids.update({'employee_id': line.id or False, 'company_id': self.company_id.id or False,'type_day': type_day, 
                        'hr_timesheet_id': self.id ,'work_date': self.work_date or False,'type_timesheet': self.type_timesheet or False,
                        'standard_worked': standard_worked, 'target': 0,'shift_id': shift_ids.id or False ,'real_worked':duration,'rate':rate or False,'sign_in_id':sign_in_id,'sign_out_id':sign_out_id or False,'ot_worked':overtime})
                    else:
                        self.env['general.hr.timesheet.lines'].create({'employee_id': line.id or False, 'company_id': self.company_id.id or False, 
                            'hr_timesheet_id': self.id ,'work_date': self.work_date or False,'type_timesheet': self.type_timesheet or False,'type_day': type_day,
                           'standard_worked': standard_worked, 'target': 0,'shift_id': shift_ids.id or False ,'real_worked':duration,'rate':rate or False,'sign_in_id':sign_in_id,'sign_out_id':sign_out_id or False,'ot_worked':overtime})
                else :
                    timesheet_line_ids = timesheet_lines_obj.search([('employee_id','=',line.id),('work_date','=',self.work_date)]) 
                    if timesheet_line_ids:
                        if len(timesheet_line_ids) > 1:
                            raise UserError(_("Employee '%s' was duplicated.")%employee_obj.name_related)
                        timesheet_line_ids.update({'employee_id': line.id or False, 'company_id': self.company_id.id or False, 
                                'hr_timesheet_id': self.id ,'work_date': self.work_date or False,'type_timesheet': self.type_timesheet or False,'type_day': type_day,
                                'standard_worked': standard_worked, 'target': 0,'shift_id': shift_ids.id or False,'rate':rate or False,'real_worked':duration})
                    else :            
                        self.env['general.hr.timesheet.lines'].create({'employee_id': line.id or False, 'company_id': self.company_id.id or False, 
                                'hr_timesheet_id': self.id ,'work_date': self.work_date or False,'type_timesheet': self.type_timesheet or False,'type_day': type_day,
                                'standard_worked': standard_worked, 'target': 0,'shift_id': shift_ids.id or False,'rate':rate or False,'real_worked':duration})
                        
        return True
     
    @api.v7
    def action_import(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        job_now = this.job_id
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents=recordlist)
            lst_sheet = excel.sheet_names()
            sh = excel.sheet_by_index(0)
            if len(lst_sheet) > 1:
                sh2 = excel.sheet_by_index(1)
        except Exception, e:
            raise UserError(_str(e))
        if sh:
            this_emp_code = ''
            this_line_id = 0
            num_of_rows = sh.nrows
            num_of_cols = sh.ncols
            for row in range(num_of_rows):
                if sh.cell(row, 0).value == u'STT':
                    flag = True
                    continue
                if row == 8:
                    continue
                if flag == True:
                    emp_code = sh.cell(row, 1).value
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code', '=', emp_code)])
                    if not len(employee_ids):
                        raise UserError(_("Employee '%s' does not exist in system" % (emp_code)))
                    employee_obj = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
                    if employee_obj.job_id[0] == job_now[0]:
                        emp_code = sh.cell(row, 1).value
                        if emp_code != this_emp_code:
                            this_emp_code = emp_code
                            
                            product_name = sh.cell(row, 8).value
                            product_uom = sh.cell(row, 9).value
                            target = sh.cell(row, 10).value
                            quantity = sh.cell(row, 11).value 
                            other_support = sh.cell(row, 12).value
                             
                            employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code', '=', emp_code)])
                            product_ids = self.pool.get('product.product').search(cr, uid, [('name', '=', product_name)])
                            product_uom_ids = self.pool.get('product.uom').search(cr, uid, [('name', '=', product_uom)])
                            
                            if this.timesheet_type == 'day':
                                standard_worked_days = sh.cell(row, 4).value
                                real_worked_days = sh.cell(row, 5).value
                                general_hr_timesheet_lines = { 
                                    'employee_id': employee_ids[0],
                                    'standard_worked_days': standard_worked_days,
                                    'real_worked_days': real_worked_days,
                                    'product_id': product_ids[0],
                                    'uom': product_uom_ids[0],
                                    'target': int(target),
                                    'quantity': int(quantity),
                                    'other_support': other_support,
                                    'timesheet_type': 'day',
                                    'hr_timesheet_id': this.id,
                                }
                            else:
                                standard_worked_hours = sh.cell(row, 6).value
                                real_worked_hours = sh.cell(row, 7).value

                                general_hr_timesheet_lines = { 
                                    'employee_id': employee_ids[0],
                                    'standard_worked_hours': standard_worked_hours,
                                    'real_worked_hours': real_worked_hours,
                                    'product_id': product_ids[0],
                                    'uom': product_uom_ids[0],
                                    'target': int(target),
                                    'quantity': int(quantity),
                                    'other_support': other_support,
                                    'timesheet_type': 'hour',
                                    'hr_timesheet_id': this.id,
                                    
                                }
                            self.pool.get('general.hr.timesheet.lines').create(cr, uid, general_hr_timesheet_lines)
#         if len(lst_sheet) > 1:
#             flag = False
#             this_emp_code = ''
#             num_of_rows = sh2.nrows
#             num_of_cols = sh2.ncols
#             for row in range(num_of_rows):
#                 if sh2.cell(row, 0).value == u'STT':
#                     flag = True
#                     row
#                     continue
#                 if row == 8:
#                     continue
#                 if flag == True:
#                     row
#                     emp_code = sh2.cell(row, 1).value
#                     employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code', '=', emp_code)])
#                     if not len(employee_ids):
#                         raise UserError(_("Employee '%s' does not exist in system" % (emp_code)))
#                     employee_obj = self.pool.get('hr.employee').browse(cr, uid, employee_ids[0])
#                     job = sh2.cell(row, 3).value
#                     if employee_obj.job_id[0] == job_now[0]:
#                         product_name = sh2.cell(row, 4).value
#                         product_uom = sh2.cell(row, 5).value
#                          
#                         quantity = sh2.cell(row, 6).value
#                         other_support = sh2.cell(row, 7).value
#                          
#                         general_hr_timesheet_lines_manager_fu = { 
#                             'employee_id': employee_ids[0],
#                             'product_id': product_ids[0],
#                             'uom': product_uom_ids[0],
#                             'quantity': quantity,
#                             'other_support': other_support,
#                             'hr_timesheet_id': this.id,
#                         }
#                         self.pool.get('general.hr.timesheet.lines.manager').create(cr, uid, general_hr_timesheet_lines_manager_fu)
        self.write({'user_import_id': uid, 'user_import_id': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True
    
    @api.multi
    def action_hr_overtime(self):
        action = self.env.ref('hr_overtime.open_ask_overtime')
        result = action.read()[0]
        ot_requests = []
        for line in self.hr_timesheet_line:
            for ot in line.hr_overtime_ids:
                if ot.state != 'cancel':
                    ot_requests.append(ot.id)
                    
        if len(ot_requests) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, ot_requests)) + "])]"
        elif len(ot_requests) == 1:
            res = self.env.ref('hr_overtime.edit_overtime_new', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = ot_requests and ot_requests[0] or False
        return result
#     @api.multi
#     def button_approve_ot(self):
#         for line in self.hr_timesheet_line:
#             for orvertime in line.hr_overtime_ids:
#                 if orvertime.state == 'confirm':
#                     orvertime.signal_workflow('validate')
# #         for line in self.hr_timesheet_line:
# #             for ot in line.hr_overtime_ids:
# #                 ot.update({'state':'validate'})
#         return True
    
class hr_overtime(models.Model):
    _inherit = "hr.overtime"
     
    hr_timesheet_line_id = fields.Many2one('general.hr.timesheet.lines', string='Timesheet', copy=False, ondelete='cascade', index=True)
#     hr_timesheet_line_manager_id = fields.Many2one('general.hr.timesheet.lines.manager', string='Timesheet', copy=False, ondelete='cascade', index=True)
    hr_timesheet_id = fields.Many2one(related='hr_timesheet_line_id.hr_timesheet_id', string='Work Date', readonly=True, copy=False, store=True, ondelete='cascade')
    
class general_hr_timesheet_lines(models.Model):
    _name = 'general.hr.timesheet.lines'
    _description = 'Employee Timesheet Lines'
#     
#     @api.depends('work_date','standard_worked','real_worked')
#     def _get_worked(self):
#         for lines in self:
#             ot_worked = salary_worked = salary_ot = 0
#             self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (lines.work_date))
#             result = self.env.cr.dictfetchall()
#             dayofweek = result and result[0] and result[0]['dayofweek'] or False
#             dayofweek = int(dayofweek - 1)
#              
#             type_day = 'normal'
#             holiday_day_line = self.env['hr.holiday.day.line']
# #             if dayofweek == 6:
# #                 holiday_ids = holiday_day_line.search([('date','=',lines.work_date),('company_id','=',lines.company_id.id)])
# #                 if holiday_ids:
# #                     type_day = 'holiday'
# #                 else:
# #                     type_day = 'sunday'
# #             else:
# #                 holiday_ids = holiday_day_line.search([('date','=',lines.work_date),('company_id','=',lines.company_id.id)])
# #                 if holiday_ids:
# #                     type_day = 'holiday'
#             if lines.force_working_time:
#                 shift_ids = self.env['resource.calendar'].search([('id','=',lines.force_working_time.id)], limit=1)
#             else:
#                     contract_ids=self.env['hr.contract'].search([('employee_id','=',lines.employee_id.id)],limit=1)
#                     shift_ids = self.env['resource.calendar'].search([('id', '=', contract_ids.working_hours.id),('unskilled_worker','=',True)], limit=1)
#             if type_day != 'normal':
#                 standard_worked = 0.0
#             else:
#                 attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',shift_ids.id),('dayofweek','=',str(dayofweek))], limit=1)
#                 standard_worked = attendance_id.hour_to - attendance_id.hour_from - shift_ids.break_hours
#             attendance_ids = self.env['resource.calendar.attendance'].search([('calendar_id','=',shift_ids.id),('dayofweek','=',str(dayofweek))], limit=1)    
#             rate=attendance_ids.rate
#             if lines.real_worked > standard_worked:
#                 ot_worked = lines.real_worked - standard_worked
#                 salary_worked = standard_worked*(rate/100)
#             else:
#                 ot_worked = 0.0
#                 salary_worked = lines.real_worked*(rate/100)        
#              
#             lines.update({'standard_worked': standard_worked,'ot_worked': ot_worked, 'salary_worked': salary_worked, 'type_day': type_day,'rate':rate or False ,'shift_id':shift_ids.id or False})
#     
#     @api.model
#     def _default_shift_id(self):
#         company = self.env.user.company_id.id
#         shift_ids = self.env['resource.calendar'].search([('force_working_time', '=', self.force_working_time.id),('unskilled_worker','=',True)], limit=1)
#         return shift_ids
    #Minh
    @api.depends('employee_id','work_date','standard_worked','real_worked')
    def _get_duration(self):
        for lines in self:
            if lines.employee_id:
                schedule_id = 0
                if lines.force_working_time:
                    schedule_id =lines.force_working_time.id
                else:
                    contract_ids=self.env['hr.contract'].search([('employee_id','=',lines.employee_id.id)],limit=1)
                    if contract_ids:
                        schedule_id = contract_ids.working_hours.id
                    else :
                        schedule_id =0
                attendance_obj= self.env['hr.attendance']
                sql_at=('''SELECT SIGN_OUT_ID,NAME,ID,DURATION,END_DATETIME FROM hr_attendance WHERE date(timezone('UTC',name::timestamp)) ='%s' and EMPLOYEE_ID='%s' and ACTION='sign_in' and attendance_once_sign ='f' and schedule_id= %s ; '''% (lines.work_date,lines.employee_id.id,schedule_id))
                self.env.cr.execute(sql_at)
                result = self.env.cr.dictfetchall()
                if result:
                    working=lines.real_worked
                    lines.update({'sign_in_id':result[0]['id']})
                    lines.duration = result[0]['duration']
                    lines.sign_in = result[0]['name']
                    lines.real_worked = result[0]['duration']
                    if working != result[0]['duration'] and str(working) != '0.0':
                        lines.real_worked = working
                    attendance_sign_out_ids =attendance_obj.search([('id','=',result[0]['sign_out_id'])])
                    if attendance_sign_out_ids:
                        lines.sign_out = attendance_sign_out_ids.name
                        lines.update({'sign_out_id':attendance_sign_out_ids.id})
            ot_worked = salary_worked = salary_ot = 0
            self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (lines.work_date))
            result = self.env.cr.dictfetchall()
            dayofweek = result and result[0] and result[0]['dayofweek'] or False
            dayofweek = int(dayofweek - 1)
            type_day = 'normal'
            holiday_day_line = self.env['hr.holiday.day.line']
            if dayofweek == 6:
                holiday_ids = holiday_day_line.search([('date','=',lines.work_date),('company_id','=',lines.company_id.id)])
                if holiday_ids:
                    type_day = 'holiday'
                else:
                    type_day = 'sunday'
            else:
                holiday_ids = holiday_day_line.search([('date','=',lines.work_date),('company_id','=',lines.company_id.id)])
                if holiday_ids:
                    type_day = 'holiday'
            standard_worked = 0.0
            if lines.force_working_time:
                shift_ids = self.env['resource.calendar'].search([('id','=',lines.force_working_time.id)], limit=1)
            else:
                contract_ids=self.env['hr.contract'].search([('employee_id','=',lines.employee_id.id)],limit=1)
                shift_ids = self.env['resource.calendar'].search([('id', '=', contract_ids.working_hours.id)], limit=1)
            if type_day == 'holiday':
                standard_worked = 0.0
            else:
                attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',shift_ids.id),('dayofweek','=',str(dayofweek))], limit=1)
                if attendance_id.hour_to > attendance_id.hour_from:
                    standard_worked = attendance_id.hour_to - attendance_id.hour_from - shift_ids.break_hours
                elif attendance_id.hour_to < attendance_id.hour_from:
                    date = attendance_id.hour_from - attendance_id.hour_to
                    standard_worked = date -(date - 12)*2 - shift_ids.break_hours
            attendance_ids = self.env['resource.calendar.attendance'].search([('calendar_id','=',shift_ids.id),('dayofweek','=',str(dayofweek))], limit=1)    
            rate=attendance_ids.rate   
            if lines.real_worked > standard_worked:
                #ot_worked = lines.real_worked - standard_worked
                salary_worked = standard_worked*(rate/100)
            else:
                #ot_worked = 0.0
                salary_worked = lines.real_worked*(rate/100)        
            overtime = 0.0
            hr_overtime_ids=self.env['hr.overtime'].search([('employee_id','=',lines.employee_id.id),('date_from','=',lines.work_date)])
            if hr_overtime_ids:
                overtime=hr_overtime_ids.number_of_hours_temp
            lines.update({'standard_worked': standard_worked ,'salary_worked': salary_worked, 'type_day': type_day,'rate':rate or False,'shift_id':shift_ids.id or False})

                                     
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    shift_id = fields.Many2one('resource.calendar', string="Shift")
    
#     type_timesheets = fields.Selection([('daily','Daily'),('weekly','Weekly'),('monthly'),('Monthly')],
#         related='hr_timesheet_id.type_timesheets',string="Type of Timesheets", readonly=True, copy=False, store=True, default='daily')
    work_date = fields.Date(related='hr_timesheet_id.work_date', string='Work Date', copy=False, store=True)
    type_day = fields.Selection([('normal','Normal'),('sunday','Sunday'),('holiday','Holidays')],string='Day of Week', store=True, compute="_get_worked", default='normal')
             
    type_timesheet = fields.Selection([('hour','Hour(s)'),('day','Day(s)')],related='hr_timesheet_id.type_timesheet', 
        string="Type of Timesheet", copy=False, store=True, default='hour')
    
    company_id = fields.Many2one(related='hr_timesheet_id.company_id', string='Company', readonly=True, copy=False, store=True)
    force_working_time=fields.Many2one(related='hr_timesheet_id.force_working_time', string='Force Working Time', readonly=True, copy=False, store=True)
#     standard_worked = fields.Float(compute='_get_worked', string='Standard Worked', store=True)
    standard_worked = fields.Float(string='Standard Worked', required=True )
    real_worked = fields.Float('Real Worked')
    
    ot_worked = fields.Float(string='OT', store=True, readonly=True)
    salary_worked = fields.Float(compute='_get_duration', string='100%', store=True)
    
#     overtime_type_id = fields.Many2one("hr.overtime.type", "Overtime Type")
#     salary_ot = fields.Float(compute='_get_worked', string='Salary OT', store=True)
    
    quantity = fields.Integer('Real Quantity')
    target = fields.Integer('Target', required=True) 
    other_support = fields.Float('Other Support')
    
    hr_overtime_ids = fields.One2many('hr.overtime', 'hr_timesheet_line_id', string='Overtimes')
    ot_rate = fields.Float(related='hr_overtime_ids.rate', string='OT Rate (%)', readonly=True, copy=False, store=True)
    
    hr_timesheet_id = fields.Many2one('general.hr.timesheet', 'Employee Timesheet', copy=False, ondelete='cascade', index=True)
    state = fields.Selection([('draft', 'Draft'),('waiting', 'Waiting Approval'),('approve', 'Approved'),('cancel', 'Canceled')],
         related='hr_timesheet_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    #Minh
    sign_in = fields.Datetime(compute='_get_duration', string="Sign In",readonly=True)
    sign_out = fields.Datetime(compute='_get_duration', string="Sign Out",readonly=True)
    duration = fields.Float(compute='_get_duration', string="Attendance",readonly=True)      
    rate= fields.Float(compute='_get_duration',string='Rate %',store=True)
    sign_in_id = fields.Integer(string="Sign In Id")
    sign_out_id = fields.Integer(string="Sign Out Id")
    
    @api.onchange('shift_id')
    def onchange_shift_id(self):
        if not self.shift_id:
            return 
        
        self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (self.work_date))
        result = self.env.cr.dictfetchall()
        dayofweek = result and result[0] and result[0]['dayofweek'] or False
        dayofweek = int(dayofweek - 1)
        
        type_day = 'normal'
        holiday_day_line = self.env['hr.holiday.day.line']
        if dayofweek == 6:
            holiday_ids = holiday_day_line.search([('date','=',self.work_date),('company_id','=',self.company_id.id)])
            if holiday_ids:
                type_day = 'holiday'
            else:
                type_day = 'sunday'
        else:
            holiday_ids = holiday_day_line.search([('date','=',self.work_date),('company_id','=',self.company_id.id)])
            if holiday_ids:
                type_day = 'holiday'
        
        if type_day != 'normal':
            standard_worked = 0.0
        else:
            attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',self.shift_id.id),('dayofweek','=',str(dayofweek))], limit=1)
            standard_worked = attendance_id.hour_to - attendance_id.hour_from 
        self.update({'standard_worked': standard_worked})
        
    
    @api.multi
    def action_hr_overtime(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('general_hr_timesheet.action_wizard_hr_overtime')
        form_view_id = imd.xmlid_to_res_id('general_hr_timesheet.view_wizard_hr_overtime')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
            }
        return result
    
    @api.onchange('employee_id')
    def _check_work_date(self):
        for lines in self:
            timesheet_ids = self.search([('work_date','=',lines.work_date),('employee_id','=',lines.employee_id.id)])
            if timesheet_ids:
                self.employee_id = False
                warning = {
                    'title': _('Warning!'),
                    'message': _('This employees already exist in this form!'),
                }
                return {'warning': warning}
# class general_hr_timesheet_lines_manager(models.Model):
#     _name = 'general.hr.timesheet.lines.manager'
#     _description = 'Manager Timesheet Lines Manager'
#     
#     @api.depends('work_date','standard_worked','real_worked')
#     def _get_worked(self):
#         for lines in self:
#             ot_worked = salary_worked = salary_ot = 0
#             type_day = 'normal'
#             
#             self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (lines.work_date))
#             result = self.env.cr.dictfetchall()
#             dayofweek = result and result[0] and result[0]['dayofweek'] or False
#             dayofweek = int(dayofweek - 1)
#             
#             attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',lines.shift_id.id),('dayofweek','=',str(dayofweek))], limit=1)
#             standard_worked = attendance_id.hour_to - attendance_id.hour_from 
#             
#             if lines.real_worked > standard_worked:
#                 ot_worked = lines.real_worked - standard_worked
#                 salary_worked = standard_worked
#             else:
#                 ot_worked = 0.0
#                 salary_worked = lines.real_worked
#             
#             if dayofweek == 6:
#                 holiday_ids = self.env['hr.holiday.day'].search([('date_from','>=',lines.work_date),('date_to','<=',lines.work_date),('company_id','=',self.company_id.id)])
#                 if holiday_ids:
#                     type_day = 'holiday'
#                 else:
#                     type_day = 'sunday'
#             lines.update({'standard_worked': standard_worked,'ot_worked': ot_worked, 'salary_worked': salary_worked, 'type_day': type_day})
#     
#     @api.model
#     def _default_shift_id(self):
#         company = self.env.user.company_id.id
#         shift_ids = self.env['resource.calendar'].search([('company_id', '=', company),('unskilled_worker','=',True)], limit=1)
#         return shift_ids
#     
#     employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
#     shift_id = fields.Many2one('resource.calendar', string="Shift", domain=[('unskilled_worker','=',True)], default=_default_shift_id)
#     
# #     type_timesheets = fields.Selection([('daily','Daily'),('weekly','Weekly'),('monthly'),('Monthly')],
# #         related='hr_timesheet_id.type_timesheets',string="Type of Timesheets", readonly=True, copy=False, store=True, default='daily')
# 
#     work_date = fields.Date(related='hr_timesheet_id.work_date', string='Work Date', copy=False, store=True)
#     type_day = fields.Selection([('normal','Normal'),('sunday','Sunday'),('holiday','Holidays')],string='Day of Week', store=True, compute="_get_worked", default='normal')
#              
#     type_timesheet = fields.Selection([('hour','Hour(s)'),('day','Day(s)')],related='hr_timesheet_id.type_timesheet', 
#         string="Type of Timesheet", copy=False, store=True, default='hour')
#     
#     company_id = fields.Many2one(related='hr_timesheet_id.company_id', string='Company', readonly=True, copy=False, store=True)
# 
# #     standard_worked = fields.Float(compute='_get_worked', string='Standard Worked', store=True)
#     standard_worked = fields.Float(string='Standard Worked', required=True)
#     real_worked = fields.Float('Real Worked')
#     
#     ot_worked = fields.Float(compute='_get_worked', string='OT', store=True)
#     salary_worked = fields.Float(compute='_get_worked', string='Salary', store=True)
#     
# #     overtime_type_id = fields.Many2one("hr.overtime.type", "Overtime Type")
# #     salary_ot = fields.Float(compute='_get_worked', string='Salary OT', store=True)
#     
#     quantity = fields.Integer('Real Quantity')
#     target = fields.Integer('Target', required=True) 
#     other_support = fields.Float('Other Support')
#     
#     hr_overtime_ids = fields.One2many('hr.overtime', 'hr_timesheet_line_manager_id', string='Overtimes')
#     
#     hr_timesheet_id = fields.Many2one('general.hr.timesheet', 'Employee Timesheet', copy=False, ondelete='cascade', index=True)
#     state = fields.Selection([('draft', 'Draft'),('approve', 'Approve'),('done', 'Done'),('cancel', 'Cancel')],
#          related='hr_timesheet_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
#     
#     @api.onchange('shift_id')
#     def onchange_shift_id(self):
#         if not self.shift_id:
#             return 
#         
#         self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (self.work_date))
#         result = self.env.cr.dictfetchall()
#         dayofweek = result and result[0] and result[0]['dayofweek'] or False
#         dayofweek = int(dayofweek - 1)
#         
#         attendance_id = self.env['resource.calendar.attendance'].search([('calendar_id','=',lines.shift_id.id),('dayofweek','=',str(dayofweek))], limit=1)
#         standard_worked = attendance_id.hour_to - attendance_id.hour_from 
#         self.update({'standard_worked': standard_worked})
#         
#     @api.multi
#     def action_hr_overtime(self):
#         imd = self.env['ir.model.data']
#         action = imd.xmlid_to_object('general_hr_timesheet.action_wizard_hr_overtime')
#         form_view_id = imd.xmlid_to_res_id('general_hr_timesheet.view_wizard_hr_overtime')
#         result = {
#             'name': action.name,
#             'help': action.help,
#             'type': action.type,
#             'views': [[form_view_id, 'form']],
#             'target': action.target,
#             'res_model': action.res_model,
#             }
#         return result
