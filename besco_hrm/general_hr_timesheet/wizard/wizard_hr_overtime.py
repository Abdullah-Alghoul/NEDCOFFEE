# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizard_hr_overtime(models.TransientModel):
    _name = 'wizard.hr.overtime'
    
    @api.depends('rate', 'number_of_hours_temp')
    def _compute_hours(self):
        result = {}
        for wizard in self:
            calculated_hours = number_of_hours = 0.0
            calculated_hours = round(wizard.rate * wizard.number_of_hours_temp / 100, 2)
            number_of_hours = wizard.number_of_hours_temp
            wizard.update({'number_of_hours': number_of_hours, 'calculated_hours': calculated_hours})
    
    line_id = fields.Many2one('general.hr.timesheet.lines', string='Timesheet Line')
    name = fields.Char('Description')
    employee_id = fields.Many2one('hr.employee', "Employee")
    
    date_from = fields.Date('Start Date')
    date_to = fields.Date('End Date')
        
    user_id = fields.Many2one('res.users', string='User')
    department_id = fields.Many2one('hr.department', string='Department')

    notes = fields.Text(string='Reasons')
    number_of_hours_temp = fields.Float('Number of Hours')
    number_of_hours = fields.Float(compute='_compute_hours', string='Number of Hours', readonly=True, store=True)
    overtime_type_id = fields.Many2one("hr.overtime.type", "Overtime Type")
    rate = fields.Float(string='Rate (%)', digits=(16, 2))
    calculated_hours = fields.Float(compute='_compute_hours', string='Calculated Hours', readonly=True, store=True)
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            line_obj = self.env["general.hr.timesheet.lines"].browse(active_id)
            
            number_of_hours_temp = hours_temp = 0.0
            self.env.cr.execute('''SELECT sum(number_of_hours_temp) hours_temp 
                FROM hr_overtime WHERE hr_timesheet_line_id = %s AND state not in ('draft','cancel')  ''' % (line_obj.id))
            result = self.env.cr.dictfetchall()
            hours_temp = result and result[0] and result[0]['hours_temp'] or 0.0
            overtime= line_obj.real_worked - line_obj.standard_worked
            if hours_temp > overtime:
                number_of_hours_temp = 0.0
            else:
                number_of_hours_temp = overtime - hours_temp
            start_date = end_date =False  
            res_user = self.env['res.users']
            if line_obj.sign_in:
                start_date = str(res_user._convert_user_datetime(line_obj.sign_in))[0:10]
            else:
                start_date = str(res_user._convert_user_datetime(line_obj.hr_timesheet_id.work_date+' 00:00:00'))[0:10]
            if line_obj.sign_out:
                end_date =str(res_user. _convert_user_datetime(line_obj.sign_out))[0:10]
            else:
                end_date = str(res_user._convert_user_datetime(line_obj.hr_timesheet_id.work_date+' 00:00:00'))[0:10]
            
            overtime_type_id = self.env["hr.overtime.type"].search([], limit=1)
            overtime_type_obj = self.env["hr.overtime.type"].browse(overtime_type_id.id)
            res = {'line_id': active_id, 'employee_id': line_obj.employee_id.id or False,'date_from':start_date or False,'date_to':end_date or False,
                'overtime_type_id': overtime_type_obj.id or False, 'rate': overtime_type_obj.rate or 0.0,
                'user_id': line_obj.employee_id.user_id.id or self.env.uid or False,
                'department_id': line_obj.employee_id.department_id.id or False, 'number_of_hours_temp': number_of_hours_temp}
        return res
    
    @api.multi
    def create_hr_overtime(self):
        orvertime = self.env['hr.overtime']
        day_ids = orvertime.search([('date_from', '<=', self.date_to), ('date_to', '>=', self.date_from), ('employee_id', '=', self.employee_id.id)])
        if day_ids:
            raise UserError(_("You can not have 2 leaves that overlaps on same day"))
        
        line_obj = self.env["general.hr.timesheet.lines"].browse(self.line_id.id)
        
        number_of_hours_temp = hours_temp = 0.0
        self.env.cr.execute('''SELECT sum(number_of_hours_temp) hours_temp 
            FROM hr_overtime WHERE hr_timesheet_line_id = %s AND state not in ('draft','cancel') ''' % (line_obj.id))
        result = self.env.cr.dictfetchall()
        hours_temp = result and result[0] and result[0]['hours_temp'] or 0.0
        overtime= line_obj.real_worked - line_obj.standard_worked
        if hours_temp > line_obj.ot_worked:
            number_of_hours_temp = 0.0
        else:
            number_of_hours_temp = overtime - hours_temp
        if round(self.number_of_hours_temp,2) > round(number_of_hours_temp,2):
            raise UserError(_("New number of OT is over than Current number of OT!"))
        
        if self.number_of_hours <= 0:
            raise UserError(_("The number of hours must be greater than 0"))
        line_obj.update({'ot_worked': self.number_of_hours_temp})
        res={'hr_timesheet_line_id': self.line_id.id or False, 'employee_id': self.employee_id.id or False,
            'overtime_type_id': self.overtime_type_id.id or False, 'rate': self.rate or 0.0,'user_id': self.user_id.id or False,
            'department_id': self.department_id.id or False,'calculated_hours': self.calculated_hours or 0.0,'number_of_hours_temp': self.number_of_hours_temp or 0.0,
            'number_of_hours': self.number_of_hours or 0.0, 'date_from': self.date_from or False, 'date_to': self.date_to or 0.0,
            'notes': self.notes or False, 'name': self.name or self.employee_id.name or False, 'double_validation': self.overtime_type_id.double_validation or False }
        new_id = orvertime.create(res)
        return True
    
    @api.multi
    @api.onchange('overtime_type_id')
    def onchange_overtime_type_id(self):
        if not self.overtime_type_id:
            self.update({'rate': 0.0})
        self.update({'rate': self.overtime_type_id.rate})
      
    @api.multi
    @api.onchange('date_from', 'date_to')  
    def onchange_date(self):
        if (self.date_from and self.date_to) and (self.date_from > self.date_to):
            raise UserError(_('The start date must be anterior to the end date.'))
        self.update({"date_to": self.date_from or False})
    
        
