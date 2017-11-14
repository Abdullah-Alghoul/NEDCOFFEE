import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from openerp import tools, SUPERUSER_ID, api
from openerp.exceptions import AccessError, UserError

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"
    @api.multi
    def unlink(self):
        for line in self:
            timesheet_lines_id=self.env['general.hr.timesheet.lines'].search(['|',('sign_in_id','=',line.id),('sign_out_id','=',line.id)],limit=1)
            timesheet_id = self.env['general.hr.timesheet'].search([('id','=',timesheet_lines_id.hr_timesheet_id.id)])
            if timesheet_id.state in ['approve','waiting']:
                raise UserError(_("Can not unlink."))
        return super(hr_attendance, self).unlink()
    @api.multi
    def write(self,vals):
        for line in self:
            timesheet_lines_id=self.env['general.hr.timesheet.lines'].search(['|',('sign_in_id','=',line.id),('sign_out_id','=',line.id)],limit=1)
            timesheet_id = self.env['general.hr.timesheet'].search([('id','=',timesheet_lines_id.hr_timesheet_id.id)])
            if timesheet_id.state in ['approve','waiting']:
                raise UserError(_("Can not write."))
            self.env.cr.execute('''SELECT NAME FROM hr_attendance WHERE ID = %s; '''% (line.id))
            result = self.env.cr.dictfetchall()
            if result:
                if vals.get('name', False):
                    if str(vals['name']) != result[0]['name']:
                        if line.action=='sign_in':
                            vals.update({'attendance_once_sign':False,'name':str(vals['name'])})
                        elif line.action=='sign_out':
                            self.env.cr.execute('''UPDATE hr_attendance SET attendance_once_sign ='f'  WHERE sign_out_id = %s; '''% (line.id))
        return super(hr_attendance, self).write(vals)
        