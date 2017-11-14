# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.exceptions import UserError, AccessError

from openerp.tools.translate import _

class hr_overtime_type(osv.osv):
    _name = "hr.overtime.type"
    _description = "Overtime Type"
    _columns = {
        'name': fields.char('Description', required=True, size=64),
        'rate': fields.float('Rate (%)', digits=(16, 2), required=True),
        'double_validation': fields.boolean('Apply Double Validation', help="If its True then its overtime type have to be validated by second validator"),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the overtime type without removing it."),
    }
    
    _defaults = {
        'rate': 0.0,
        'double_validation': False,
        'active': True,
    }
    
hr_overtime_type()

class hr_overtime(osv.osv):
    _name = "hr.overtime"
    _description = "Overtime"
    _order = "date_from asc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
            'hr_overtime.mt_overtime_approved': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'validate',
            'hr_overtime.mt_overtime_refused': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'refuse',
            'hr_overtime.mt_overtime_confirmed': lambda self, cr, uid, obj, ctx = None: obj['state'] == 'confirm',
        },
    }
    
    def _get_ot_type(self, cr, uid, context=None):
        ids = self.pool.get('hr.overtime.type').search(cr, uid, [], context=context)
        return ids and ids[0] or False
    
    def _employee_get(self, cr, uid, context=None):
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    def _compute_number_of_hours(self, cr, uid, ids, name, args, context=None):
        result = {}
        for hol in self.browse(cr, uid, ids, context=context):
            result[hol.id] = hol.number_of_hours_temp
        return result

    _columns = {
        'name': fields.char('Description', required=True, size=64),
        'state': fields.selection([('draft', 'Draft'), ('confirm', 'Waiting Approval'), ('refuse', 'Refused'),
            ('validate1', 'Waiting Second Approval'), ('validate', 'Approved'), ('cancel', 'Cancelled')],
            'State', readonly=True, help='When the overtim request is created the state is \'Draft\'.\n It is confirmed by the user and request is sent to admin, the state is \'Waiting Approval\'.\
            If the admin accepts it, the state is \'Approved\'. If it is refused, the state is \'Refused\'.'),
        'user_id':fields.related('employee_id', 'user_id', type='many2one', relation='res.users', string='User', store=True),
        'date_from': fields.date('Start Date', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}),
        'date_to': fields.date('End Date', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}),
        
        'employee_id': fields.many2one('hr.employee', "Employee", select=True, invisible=False, readonly=True, states={'draft':[('readonly', False)]}),
        'manager_id': fields.many2one('hr.employee', 'First Approval', invisible=False, readonly=True),
        'notes': fields.text('Reasons', readonly=True, states={'draft':[('readonly', False)]}),
        'number_of_hours_temp': fields.float('Number of Hours', readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}),
        'number_of_hours': fields.function(_compute_number_of_hours, method=True, string='Number of Hours', store=True),
        'department_id':fields.related('employee_id', 'department_id', string='Department', type='many2one', relation='hr.department', readonly=True, store=True),
        'manager_id2': fields.many2one('hr.employee', 'Second Approval', readonly=True, help='This area is automaticly filled by the user who validate the leave with second level (If Leave type need second validation)'),
        'overtime_type_id': fields.many2one("hr.overtime.type", "Overtime Type", required=True, readonly=True, states={'draft':[('readonly', False)]}),
        'double_validation': fields.related('overtime_type_id', 'double_validation', type='boolean', relation='hr.overtime.type', string='Apply Double Validation'),
        'batch_id': fields.many2one('hr.overtime.batch', 'Batch', ondelete='cascade'),
    }
    _defaults = {
        'employee_id': _employee_get,
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        # Thanh
        'overtime_type_id': _get_ot_type,
    }
    _sql_constraints = [
        ('date_check', "CHECK ( number_of_hours_temp > 0 )", "The number of hours must be greater than 0 !"),
        ('date_check2', "CHECK (date_from <= date_to)", "The start date must be before the end date !")
    ]

    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'refuse']:
                raise osv.except_osv(_('Warning!'), _('You cannot delete a overtime which is not in draft state !'))
        return super(hr_overtime, self).unlink(cr, uid, ids, context)

    def onchange_date_from(self, cr, uid, ids, date_to, date_from, context=None):
        result = {}
        if not date_to:
            result['value'] = {
                'date_to': date_from,
            }
        return result
    
    def onchange_date_to(self, cr, uid, ids, date_to, date_from, context=None):
        result = {}
        result['value'] = {
#             'number_of_hours_temp': 0,
        }
        return result
    
    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
        })
        return True

    def overtime_validate(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.overtime_first_validate_notificate(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state':'validate1', 'manager_id': manager})

    def overtime_validate2(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        self.write(cr, uid, ids, {'state':'validate'})
        data_holiday = self.browse(cr, uid, ids)
        for record in data_holiday:
            if record.double_validation:
                self.write(cr, uid, [record.id], {'manager_id2': manager})
            else:
                self.write(cr, uid, [record.id], {'manager_id': manager})
        return True

    def overtime_cancel(self, cr, uid, ids, context=None):
        self.signal_workflow(cr, uid, ids, 'cancel')
        return True

    def overtime_confirm(self, cr, uid, ids, context=None):
        for record in self.browse(cr, uid, ids, context=context):
            if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
        return self.write(cr, uid, ids, {'state': 'confirm'})
    
    def overtime_refuse(self, cr, uid, ids, context=None):
        obj_emp = self.pool.get('hr.employee')
        ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
        manager = ids2 and ids2[0] or False
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.state == 'validate1':
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id': manager})
            else:
                self.write(cr, uid, [holiday.id], {'state': 'refuse', 'manager_id2': manager})
        self.overtime_cancel(cr, uid, ids)
        return True
    
    def _needaction_domain_get(self, cr, uid, context=None):
        emp_obj = self.pool.get('hr.employee')
        empids = emp_obj.search(cr, uid, [('parent_id.user_id', '=', uid)], context=context)
        dom = ['&', ('state', '=', 'confirm'), ('employee_id', 'in', empids)]
        # if this user is a hr.manager, he should do second validations
        if self.pool.get('res.users').has_group(cr, uid, 'base.group_hr_manager'):
            dom = ['|'] + dom + [('state', '=', 'validate1')]
        return dom

    def overtime_first_validate_notificate(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            self.message_post(cr, uid, [obj.id],
                _("Request approved, waiting second validation."), context=context)
            
    def show_wizard_import_overtime(self, cr, uid, ids, context=None):

        if context is None:
            context = {}
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False
        })
        return {
            'name': _('Import Overtime'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.import.overtime',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
            'nodestroy': True,
            }
            
hr_overtime()
