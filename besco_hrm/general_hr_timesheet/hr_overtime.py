# -*- coding: utf-8 -*-
from openerp.osv import fields, osv 
from openerp.exceptions import UserError, AccessError
from openerp import api
from openerp.tools.translate import _

class hr_overtime(osv.osv):
    _inherit = "hr.overtime"
    _columns = {
    'state_timesheet': fields.char('State TimeSheet'),
    }
    
    def onchange_date_from(self, cr, uid, ids, date_to, date_from, employee_id=None):
        result = {}
        if date_from:
            line_obj = self.pool.get('general.hr.timesheet.lines')
            line_ids=line_obj.search(cr,uid,[('employee_id','=',employee_id),('work_date','=',date_from )])
            if line_ids:
                for line_id in line_obj.browse(cr, uid, line_ids,context=None) :
                    overtime= line_id.real_worked - line_id.standard_worked
                    if overtime >0 :
                        overtime = overtime
                    else:
                        overtime =0.0
                    res_user = self.pool.get('res.users')
                    end_date = str(res_user._convert_user_datetime(cr,uid,line_id.sign_in))[0:10]
                    result['value'] = {
                    'date_to': end_date,
                    'number_of_hours_temp':overtime,
                    }
            else:
                result['value'] = {
                    'date_to': date_from,
                    'number_of_hours_temp':0.0,
                    }
        return result
    
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'refuse']:
                raise osv.except_osv(_('Warning!'), _('You cannot delete a overtime which is not in draft state !'))
            line_obj = self.pool.get('general.hr.timesheet.lines')
            line_ids=line_obj.search(cr,uid,[('employee_id','=',rec.employee_id.id),('work_date','=',rec.date_from )])
            if line_ids:
                for line_id in line_obj.browse(cr, uid, line_ids,context=None) :
                    line_obj.write(cr,uid,line_ids,{'ot_worked': 0.0},context=context)
        return super(hr_overtime, self).unlink(cr, uid, ids, context)

    def overtime_confirm(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
            
            line_obj = self.pool.get('general.hr.timesheet.lines')
            line_ids=line_obj.search(cr,uid,[('employee_id','=',record.employee_id.id),('work_date','=',record.date_from )])
            if line_ids:
                for line_id in line_obj.browse(cr, uid, line_ids,context=None) :
                    overtime= line_id.real_worked - line_id.standard_worked
                    if overtime >0 :
                        overtime = overtime
                    else:
                        overtime =0.0
                    if round(record.number_of_hours_temp,2) > round(overtime,2):
                        raise UserError(_("New number of OT is over than Current number of OT!"))
                    line_obj.write(cr,uid,line_ids,{'ot_worked': record.number_of_hours_temp},context=context)
                    vals={'state': 'confirm','hr_timesheet_line_id':line_id.id or False,'hr_timesheet_id':line_id.hr_timesheet_id.id or False}
            else:
                vals={'state': 'confirm'}
        return self.write(cr, uid, ids, vals)
    def write(self, cr, uid, ids,vals, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            line_obj = self.pool.get('general.hr.timesheet.lines')
            line_ids=line_obj.search(cr,uid,[('employee_id','=',record.employee_id.id),('work_date','=',record.date_from )])
            if line_ids:
                for line_id in line_obj.browse(cr, uid, line_ids,context=None) :
                    overtime= line_id.real_worked - line_id.standard_worked
                    if overtime >0 :
                        overtime = overtime
                    else:
                        overtime =0.0
                    if round(record.number_of_hours_temp,2) > round(overtime,2):
                        raise UserError(_("New number of OT is over than Current number of OT!"))
                    line_obj.write(cr,uid,line_ids,{'ot_worked': record.number_of_hours_temp},context=context)
        return super(hr_overtime, self).write(cr, uid, ids, vals, context)