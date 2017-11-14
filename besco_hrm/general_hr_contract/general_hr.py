# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID
from lxml import etree
from openerp.exceptions import UserError

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    _columns = {
        'resigned_date': fields.date('Resigned Date'),
    }
    
#     def run_update(self, cr, uid, use_new_cursor=False, company_id = False, context=None):
#         emp_ids = self.pool.get('hr.employee').search(cr, uid, [('resigned_date','!=',False)])
#         for i in emp_ids:
#             emp_obj = self.pool.get('hr.employee').browse(cr, uid, i)
#             emp_obj.toggle_active()
    
    @api.multi
    def toggle_active(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """
        for record in self:
            if record and not record.resigned_date:
                 raise UserError(_("You must be set Resign Date."))
            hr_contract_ids = self.env['hr.contract'].search([('company_id', '=', self.address_id.id), ('employee_id', '=', self.id), ('state', 'in', ('trial','open','pending'))])
            if hr_contract_ids:
                for hr_contract_obj in hr_contract_ids:
                    hr_contract_obj.write({'expire_date': record.resigned_date, 'user_approve_id': self.env.user.id, 'state': 'close', 'history_checked': True})
                    
            record.active = not record.active
            
    def write(self, cr, uid, ids, vals, context=None):
        employee_history_pool = self.pool.get('hr.employee.history')
        result = False
        for line in self.browse(cr, uid, ids):
            employee_history_vals = {}
#             if vals.get('parent_id',False):
#                 employee_history_vals.update({'parent_id':line.parent_id.id or False})
            if vals.get('work_email',False): 
                email = vals.get('work_email')
                sql = '''
                    select id from hr_employee where work_email = '%s'
                '''%(email)
                cr.execute(sql)
                for line in cr.fetchall():
                    if line:
                        raise UserError(_("Your email was existed.")) 
            if vals.get('department_id',False):
                employee_history_vals.update({'department_id':line.department_id.id or False})
            if vals.get('job_id',False):
                employee_history_vals.update({'job_id':line.job_id.id  or False})
            
            if vals.get('joining_date',False):
                employee_history_vals.update({'joining_date':line.joining_date or False})
            if vals.get('worked_years',False):
                employee_history_vals.update({'worked_years':line.worked_years or False})
                
            if vals.get('address_id',False):
                employee_history_vals.update({'address_id':line.address_id.id or False})
            if vals.get('resigned_date',False):
                employee_history_vals.update({'resigned_date':vals.get('resigned_date',False)})
            
            if employee_history_vals:
                employee_history_vals.update({'employee_id':line.id})
                employee_history_pool.create(cr, uid, employee_history_vals)
            result = super(hr_employee, self).write(cr, uid, ids, vals, context)
        return result
    
class hr_employee_history(osv.osv):
    _inherit = 'hr.employee.history'
    _columns = {
        'resigned_date': fields.date('Resigned Date', readonly=True),
    }