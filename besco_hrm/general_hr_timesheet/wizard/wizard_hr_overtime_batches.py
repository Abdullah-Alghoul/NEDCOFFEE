# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizard_hr_overtime_batches(models.TransientModel):
    _name = 'wizard.hr.overtime.batches'
    
    overtime_type_id = fields.Many2one("hr.overtime.type", "Overtime Type",required=True)
    
    @api.multi
    def button_ot_batches(self):
        active_id = self._context.get('active_id')
        time_sheet_line_ids = self.env['general.hr.timesheet.lines'].search([('hr_timesheet_id','=',active_id)])
        for line in time_sheet_line_ids:
            if line.real_worked - line.standard_worked > 0 and line.ot_worked == 0.0 :
                overtime = line.real_worked - line.standard_worked
                rates=self.env['hr.overtime.type'].search([('id','=',self.overtime_type_id.id)])
                rate= rates.rate
                calculated_hours=round(rate * overtime / 100, 2)
                department_ids =self.env['hr.employee'].search([('id','=',line.employee_id.id)])
                department_id=department_ids.department_id.id
                res_user = self.env['res.users']
                employee_obj = self.env['hr.employee'].browse(line.employee_id.id)
                if line.sign_in:
                    start_date = str(res_user._convert_user_datetime(line.sign_in))[0:10]
                else:
                    start_date = str(res_user._convert_user_datetime(line.hr_timesheet_id.work_date+' 00:00:00'))[0:10]
                if line.sign_out:
                    end_date =str(res_user. _convert_user_datetime(line.sign_out))[0:10]
                else:
                    end_date = str(res_user._convert_user_datetime(line.hr_timesheet_id.work_date+' 00:00:00'))[0:10]
                res={'hr_timesheet_line_id': line.id or False, 'employee_id': line.employee_id.id or False,'company_id': employee_obj.address_id.company_id.id or False,
                        'overtime_type_id': self.overtime_type_id.id or False, 'rate': rate or 0.0,
                        'department_id': department_id or False,'calculated_hours': calculated_hours or 0.0,'number_of_hours_temp': overtime or 0.0,
                        'date_from': start_date or False, 'date_to': end_date or False,
                        'name': line.employee_id.name or False}
                line.update({'ot_worked':overtime})
                hr_overtime_ids=self.env['hr.overtime'].search([('employee_id','=',line.employee_id.id),('hr_timesheet_line_id','=',line.id),('hr_timesheet_id','=',line.hr_timesheet_id.id)])
                if hr_overtime_ids:
                    hr_overtime_ids.update(res)
                else :
                    self.env['hr.overtime'].create(res)
        return True