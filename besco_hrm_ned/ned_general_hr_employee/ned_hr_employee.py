# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import openerp
from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.modules.module import get_module_resource
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _order = 'id asc' 

    _columns = {
        'insurance_number':fields.char('Insurance Number'),
        'insurance_code_id' : fields.many2one('insurance.code', 'Insurance Code', required=True),
        'cease': fields.boolean('Cease'),
        'admin_hr': fields.boolean('Is Admin HR'),
        'technique_id': fields.many2one('hr.recruitment.technique', 'Technique'),
        'family_code':fields.char('Family code'),
#         'native_village' : fields.char('Native Village')
        'registration_book_number':fields.char('Registration Book Number'),
    }
    
    @api.model
    def cal_worked_year_ned(self,ids=None):
        print 'cal_worked_year_ned'
        Today = datetime.now().date()
        employee_pool = self.env['hr.employee']
        query = """select id from hr_employee where joining_date is not null"""
        self.env.cr.execute(query)
        for i in self.env.cr.fetchall():
            emp_obj = employee_pool.browse(i)
            if emp_obj.joining_date:
                temp = emp_obj.joining_date
                Fromday = datetime.strptime(emp_obj.joining_date, DEFAULT_SERVER_DATE_FORMAT).date()
                emp_obj.write({'joining_date': False})
                emp_obj.write({'joining_date': temp})
                    
    @api.multi
    def check_duplicate_employee(self, identification_id):
        active_employee_ids = False
        if identification_id:  
            sql = """SELECT name_related FROM hr_employee WHERE identification_id = '%s'"""%identification_id
            self.env.cr.execute(sql)
            active_employee_ids = self.env.cr.fetchone()
        if active_employee_ids:
            raise UserError(_("Your data was duplicated Identification No with '%s'.")%active_employee_ids[0])
        else:
            return False
        
    def create(self, cr, uid, vals, context=None):
        if vals.get('identification_id', False):
            sql = """SELECT name_related FROM hr_employee WHERE identification_id = '%s'"""%vals.get('identification_id', False)
            cr.execute(sql)
            active_employee_ids = cr.fetchone()
            if active_employee_ids:
                raise UserError(_("Your data was duplicated Identification No with '%s'.")%active_employee_ids[0])
        system_sequence_obj = self.pool.get('system.sequence')
        code = system_sequence_obj.get_current_sequence(cr, 'employee_code')
        vals.update({'code': code})
        return super(hr_employee, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        employee_history_pool = self.pool.get('hr.employee.history')
        for line in self.browse(cr, uid, ids):
            if vals.get('identification_id', False):
                line.check_duplicate_employee(vals.get('identification_id', False))
            employee_history_vals = {}
            if vals.get('parent_id', False):
                employee_history_vals.update({'parent_id':vals.get('parent_id') or False})
            if vals.get('department_id', False):
                employee_history_vals.update({'department_id':vals.get('department_id') or False})
            if vals.get('job_id', False):
                employee_history_vals.update({'job_id':vals.get('job_id') or False})
            if vals.get('user_id', False):
                employee_history_vals.update({'user_id':vals.get('user_id') or False})
            if vals.get('effective_date', False):
                employee_history_vals.update({'effective_date':vals.get('effective_date') or False})
            if vals.get('worked_years', False):
                employee_history_vals.update({'worked_years':vals.get('worked_years') or False})
            if vals.get('create_date', False):
                employee_history_vals.update({'create_date':vals.get('create_date') or False})
            if employee_history_vals:
                employee_history_vals.update({'employee_id':line.id})
                employee_history_pool.create(cr, uid, employee_history_vals)
        return super(hr_employee, self).write(cr, uid, ids, vals, context)
class RecruitmentTechinque(osv.osv):
    _name = "hr.recruitment.technique"
    _columns = {
        'name': fields.char('Name')
    }

class insurance_code(osv.osv):
    _name = 'insurance.code'
    _columns = {
        'name' : fields.char('Code'),
    }

class hr_employee_dependent(osv.osv):
    _inherit = "hr.employee.dependent"
    
    _columns = {
        'is_household_head': fields.boolean('Is Head Of a Household'),
        'social_insurance_code': fields.char('Social Insurance Code'),
    }
