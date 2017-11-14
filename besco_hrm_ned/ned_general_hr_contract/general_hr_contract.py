# -*- coding: utf-8 -*-
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
DATE_FORMAT = "%Y-%m-%d"
from openerp import netsvc
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import AccessError, UserError

from openerp import api
from lxml import etree
from openerp import SUPERUSER_ID

class hr_contract_type(osv.osv):
    _inherit = 'hr.contract.type'
    
    _columns = {
        'number_of_remind_time': fields.integer('Number of Remind Time')
    }
    
class hr_contract(osv.osv):
    _inherit = 'hr.contract'
    
    _columns = {
        'check_remind': fields.boolean('Is Remind')
    }
    
#     @api.model
#     def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
#         context = self._context
#         ids = []
#         res = super(hr_contract, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
#         if view_type in ['form']:
#             doc = etree.XML(res['arch'])
#              
#             for node in doc.xpath("//field[@name='employee_id']"):
#                 
# #                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_68z"):
# #                     employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0068Z')])
# #                     node.set('domain', "[('id','in',"+str(employee_ids)+")]")
#                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_76z"):
#                     employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0076Z')])
#                     node.set('domain', "[('id','in',"+str(employee_ids)+")]")
#                 
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res
    
    @api.model
    def run_check_remind(self,ids=None):
        contract_objs = self.env['hr.contract'].search([('state','!=','close')])
        today = datetime.strptime(datetime.now().strftime("%Y-%m-%d"), DATE_FORMAT).date()
        for i in contract_objs:
            if i.date_end:
                date_end = datetime.strptime(i.date_end, DATE_FORMAT).date()
                if (date_end - today).days <= i.type_id.number_of_remind_time and (date_end - today).days > 0:
                    i.write({'history_checked': True,'check_remind': True})
                else:
                    i.write({'history_checked': True,'check_remind': False})
            if i.trial_date_end:
                trial_date_end = datetime.strptime(i.trial_date_end, DATE_FORMAT).date()
                if (trial_date_end - today).days <= i.type_id.number_of_remind_time and (trial_date_end - today).days > 0:
                    i.write({'history_checked': True,'check_remind': True})
                else:
                    i.write({'history_checked': True,'check_remind': False})        
                    
    def create(self, cr, uid, vals, context=None):
        if vals.get('date_start', False):
            date_start = vals.get('date_start', False)
            
        if vals.get('trial_date_start', False):
            trial_date_start = vals.get('trial_date_start', False)
            
        if vals.get('date_end', False):
            date_end = vals.get('date_end', False)
            
        if vals.get('trial_date_end', False):
            trial_date_end = vals.get('trial_date_end', False)
        
        if vals.get('name', 'New'):
            if vals.get('date_start', False):
                year = vals.get('date_start', False)[0:4]
            else:
                year = vals.get('trial_date_start', False)[0:4]
            
            employee_id = vals.get('employee_id', False)
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            struct_salary_id = False
            struct_salary_id = vals.get('struct_id', False)
            employee.struct_salary_id = struct_salary_id
            code = employee.code+'/HR/'+year
            vals.update({'name' : code})
        return super(hr_contract, self).create(cr, uid, vals, context=context)
                  
class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    _columns = {
        'struct_salary_id': fields.many2one('hr.payroll.structure','Salary Structure')
    }
    
    @api.model
    def edit_struct_salary_id(self,ids=None):
        Today = datetime.now().date()
        employee_pool = self.env['hr.employee']
        query = """select id from hr_employee where struct_salary_id is not null"""
        self.env.cr.execute(query)
        for i in self.env.cr.fetchall():
            emp_obj = employee_pool.browse(i)
            contract_obj = self.env['hr.contract'].search([('state','in',('trial','open')), ('employee_id','=',emp_obj.id)])
            emp_obj.struct_salary_id = contract_obj.struct_id.id
    
    @api.multi
    def set_struct_salary_id(self, struct_salary_id):
        payroll_structure_obj = self.env['hr.payroll.structure'].browse(struct_salary_id)
        self.struct_salary_id = payroll_structure_obj.id
