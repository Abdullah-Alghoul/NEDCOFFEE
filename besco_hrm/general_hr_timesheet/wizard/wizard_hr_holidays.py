# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_hr_holidays(models.TransientModel):
    _name = 'wizard.hr.holidays'
    
    @api.depends('number_of_days_temp')
    def _compute_number_of_days(self):
        result = {}
        for hol in self:
            if hol.type == 'remove':
                number_of_days_temp = -hol.number_of_days_temp
            else:
                number_of_days_temp = hol.number_of_days_temp
            hol.number_of_days = number_of_days_temp
    
    holiday_status_id = fields.Many2one("hr.holidays.status", string="Leave Type")
    employee_id = fields.Many2one('hr.employee', string="Employee", select=True)
    department_id = fields.Many2one('hr.department', string="Department")
    notes = fields.Text('Reasons')
    
    number_of_days_temp = fields.Float('Allocation', copy=False)
    number_of_days = fields.Float(compute='_compute_number_of_days', string='Number of Days', store=True)
    
    provide_days = fields.Integer('Legal Days')
    number_of_days_temp_manager = fields.Float('Number of days Manager')
    date_from_manager = fields.Datetime('Date from Manager')    
    date_to_manager = fields.Datetime('Date to Manager')
    
    date_from = fields.Datetime(string='Start Date', select=True, copy=False)
    date_to = fields.Datetime(string='End Date', copy=False)
    
    reason_id = fields.Many2one('hr.holidays.reason', string='Reasons')
    reason = fields.Boolean(string='Reason')
    hours = fields.Float(string='Hours')
    regulations = fields.Text(string='Regulations')
    
    holiday_type = fields.Selection([('employee', 'By Employee'), ('category', 'By Employee Tag')], 'Allocation Mode', required=True, default="employee")

    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            line_obj = self.env["general.hr.timesheet.lines"].browse(active_id)
            
            number_of_hours_temp = hours_temp = 0.0
            self.env.cr.execute('''SELECT sum(number_of_hours_temp) hours_temp 
                FROM hr_overtime WHERE hr_timesheet_line_id = %s AND state != 'draft' ''' % (line_id))
            result = self.env.cr.dictfetchall()
            hours_temp = result and result[0] and result[0]['hours_temp'] or 0.0
            if line_obj.timesheet_type == 'hour':
                if hours_temp > line_obj.ot_hours:
                    number_of_hours_temp = hours_temp - line_obj.ot_hours
                else:
                    number_of_hours_temp = line_obj.ot_hours - hours_temp
            elif line_obj.timesheet_type == 'day':
                if hours_temp > line_obj.ot_hours:
                    number_of_hours_temp = hours_temp - line_obj.ot_days
                else:
                    number_of_hours_temp = line_obj.ot_days - hours_temp
            
            overtime_type_id = self.env["hr.overtime.type"].search([], limit=1)
            overtime_type_obj = self.env["hr.overtime.type"].browse(overtime_type_id.id)
            
            res = {'line_id': active_id, 'employee_id': line_obj.employee_id.id or False,
                'overtime_type_id': overtime_type_obj.id or False, 'rate': overtime_type_obj.rate or 0.0,
                'user_id': line_obj.employee_id.user_id.id or self.env.uid or False,
                'department_id': line_obj.employee_id.department_id.id or False, 'number_of_hours_temp': number_of_hours_temp}
        return res
    
