# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
import time
from openerp.tools.translate import _

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class generate_allocation_request(osv.osv_memory):
    _name = 'generate.allocation.request'
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'wizard_generate_allocation_request_employees', 'wizard_id', 'employee_id', "Employees", required=True),
        'number_days': fields.float("Days", required=True),
        'allocation_date': fields.date('Allocation Date', required=True),
        'type': fields.selection([
            ('1', 'No duplicate'),
            ('2', 'Duplicate'),
            ], 'Type', required=True),
        'transfer_old_leave': fields.boolean('Transfer Old Leave'),
    }
    
    _defaults = {
         'allocation_date': time.strftime("%Y-%m-%d"),
         'type': '1',
         'number_days': 12,
         'transfer_old_leave': False
    }
    
    def generate_allocation_request(self, cr, uid, ids, context=None):
        context = context or {}
        if context.get('active_id',False):
            leave_type_id = context['active_id']
        else:
            return True
        
        new_allocation_ids = []
        leave_type_pool = self.pool.get('hr.holidays.status')
        hr_holidays_pool = self.pool.get('hr.holidays')        
        this = self.browse(cr, uid, ids[0])
        if this.number_days <= 0 and not this.transfer_old_leave:
            raise UserError(_('Days must be greater than 0!'))
        for employee in this.employee_ids:
            if this.type == '1':
                exist_allocation_ids = hr_holidays_pool.search(cr, uid, [('employee_id','=',employee.id),
                                                                         ('type','=','add'),
                                                                         ('holiday_status_id','=',leave_type_id),
                                                                         ('state','=','validate')])
                if len(exist_allocation_ids):
                    continue
            
            if this.transfer_old_leave and employee.remaining_leaves <= 0:
                #THANH: When there is no remaining leave for this employee, go next to other employee
                continue
                
            leave_type = leave_type_pool.browse(cr, uid, leave_type_id)
            name = leave_type.name or ''
            name += ' (' + employee.name + ')' or ''
            vals = {
                  'name':name,
                  'holiday_status_id':leave_type_id,
                  'employee_id':employee.id, 
                  'type':'add',
                  'date_from': this.allocation_date,
                  'number_of_days_temp':this.number_days,
                  'transfer_old_leave': False,
                  #THANH: do not send email when automatically creating allocation
                  'no_send_email': True,
                  }
            
            #THANH: calculate bonus day by joining_date
            if leave_type.legal_leaves:
                if employee.worked_years >= leave_type.from_worked_years and leave_type.number_of_year:
                    worked_years = int(employee.worked_years) #THANH: worked years = 5.6 => rounding 5
                    if leave_type.rounding_worked_years:
                        worked_years = round(employee.worked_years, 0)  #THANH: worked years = 5.6 => rounding 6 and 5.4 => rounding 5
#                     year_number = worked_years - leave_type.from_worked_years #THANH: from_worked_years = 5, worked_years = 8 => year_number = 3
#                     bonus_days = (year_number / leave_type.number_of_year) * leave_type.bonus_days
                    bonus_days = (worked_years / leave_type.number_of_year) * leave_type.bonus_days
                    vals['number_of_days_temp'] += bonus_days
                    
            if this.transfer_old_leave:
                vals['number_of_days_temp'] = employee.remaining_leaves
                vals['transfer_old_leave'] = True
                    
            new_id = hr_holidays_pool.create(cr, uid, vals)
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'confirm')
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'validate')
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'second_validate')
            new_allocation_ids.append(new_id)
            
        if len(new_allocation_ids):
            leave_type_pool.write(cr, uid, leave_type_id, {'allocation_ids': [(6, 0, new_allocation_ids)]})
#             data_obj = self.pool.get('ir.model.data')
#             model, action_id = data_obj.get_object_reference(cr, uid, 'hr_holidays', 'open_allocation_holidays')
#             action = self.pool.get(model).read(cr, uid, action_id, context=context)
#             action['domain'] = "[('id', 'in', %s)]" % new_allocation_ids
#             action['context'] = "{'default_type':'add','search_default_my_leaves':0}"
            return True
        
        return {'type': 'ir.actions.act_window_close'}
    
generate_allocation_request()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: