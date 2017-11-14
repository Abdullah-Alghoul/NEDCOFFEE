# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
import time

class generate_allocation_request(osv.osv_memory):
    _name = 'generate.allocation.request'
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'wizard_generate_allocation_request_employees', 'wizard_id', 'employee_id', "Employees", required=True),
        'number_days': fields.float("Days", required=True),
        'allocation_date': fields.date('Allocation date', required=True),
        'type': fields.selection([
            ('1', 'No duplicate'),
            ('2', 'Duplicate'),
            ], 'Type', required=True),
    }
    
    _defaults = {
                 'allocation_date': time.strftime("%Y-%m-%d"),
                 'type': '1',
                 }
    
    def generate_allocation_request(self, cr, uid, ids, context=None):
        context = context or {}
        if context.get('active_id', False):
            leave_type_id = context['active_id']
        else:
            return True
        new_allocation_ids = []
        employee_pool = self.pool.get('hr.employee')
        leave_type_pool = self.pool.get('hr.holidays.status')
        hr_holidays_pool = self.pool.get('hr.holidays')        
        this = self.browse(cr, uid, ids[0])
        if this.number_days <= 0:
            raise osv.except_osv(_('Error!'), _('Days must be greater than 0!'))
        for employee_id in this.employee_ids:
            if this.type == '1':
                exist_allocation_ids = hr_holidays_pool.search(cr, uid, [('employee_id', '=', employee_id.id),
                                                                         ('type', '=', 'add'),
                                                                         ('holiday_status_id', '=', leave_type_id),
                                                                         ('state', '=', 'validate')])
                if len(exist_allocation_ids):
                    continue
                    
            leave_type = leave_type_pool.browse(cr, uid, leave_type_id)
            name = leave_type.name or ''
            name += ' (' + employee_pool.browse(cr, uid, employee_id.id).name + ')' or ''
            vals = {
                  'name':name,
                  'holiday_status_id':leave_type_id,
                  'employee_id':employee_id.id,
                  'type':'add',
                  'date_from': this.allocation_date,
                  'number_of_days_temp':this.number_days,
                  }
            new_id = hr_holidays_pool.create(cr, uid, vals)
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'confirm')
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'validate')
            hr_holidays_pool.signal_workflow(cr, uid, [new_id], 'second_validate')
            new_allocation_ids.append(new_id)
            
        if len(new_allocation_ids):
            data_obj = self.pool.get('ir.model.data')
            model, action_id = data_obj.get_object_reference(cr, uid, 'hr_holidays', 'open_allocation_holidays')
            action = self.pool.get(model).read(cr, uid, action_id, context=context)
            action['domain'] = "[('id', 'in', %s)]" % new_allocation_ids
            action['context'] = "{'default_type':'add','search_default_my_leaves':0}"
            return action
        
        return {'type': 'ir.actions.act_window_close'}
    
generate_allocation_request()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
