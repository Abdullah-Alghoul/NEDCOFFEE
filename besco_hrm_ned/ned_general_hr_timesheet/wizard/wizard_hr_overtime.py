# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizard_hr_overtime(models.TransientModel):
    _inherit = 'wizard.hr.overtime'
    
#     @api.model
#     def default_get(self, fields):
#         res = {}
#         vars = []
#         active_id = self._context.get('active_id')
#         if active_id:
#             line_obj = self.env["general.hr.timesheet.lines"].browse(active_id)
#             
#             number_of_hours_temp = hours_temp = 0.0
#             self.env.cr.execute('''SELECT sum(number_of_hours_temp) hours_temp 
#                 FROM hr_overtime WHERE hr_timesheet_line_id = %s AND state != 'draft' ''' % (line_obj.id))
#             result = self.env.cr.dictfetchall()
#             hours_temp = result and result[0] and result[0]['hours_temp'] or 0.0
#             if hours_temp > line_obj.ot_worked:
#                 number_of_hours_temp = hours_temp - line_obj.ot_worked
#             else:
#                 number_of_hours_temp = line_obj.ot_worked - hours_temp
#             
#             overtime_type_id = self.env["hr.overtime.type"].search([], limit=1)
#             overtime_type_obj = self.env["hr.overtime.type"].browse(overtime_type_id.id)
#             
#             res = {'line_id': active_id, 'employee_id': line_obj.employee_id.id or False,
#                 'overtime_type_id': overtime_type_obj.id or False, 'rate': overtime_type_obj.rate or 0.0,
#                 'user_id': line_obj.employee_id.user_id.id or self.env.uid or False,
#                 'department_id': line_obj.employee_id.department_id.id or False, 'number_of_hours_temp': number_of_hours_temp,
#                 'date_from': line_obj.hr_timesheet_id.work_date or False, 'date_to': line_obj.hr_timesheet_id.work_date}
#         return res
    
    
        
