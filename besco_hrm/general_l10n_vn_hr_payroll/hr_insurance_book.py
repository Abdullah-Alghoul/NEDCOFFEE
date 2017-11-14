# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class hr_insurance_book(osv.osv):
    _name = "hr.insurance.book"
    _columns = {
                'name': fields.char('Number', size=128, required=True),
                'issue_date': fields.date('Issue Date'),
                'issue_place': fields.char('Issue Place', size=500, required=True),
                'employee_id':fields.many2one('hr.employee', 'Employee', required=True, ondelete='cascade', index=True),
                'company_id': fields.related('employee_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True),
                }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Reference must be unique per Company!'),
    ]
    
hr_insurance_book()

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    _columns = {
         'insurance_ids': fields.one2many('hr.insurance.book', 'employee_id', 'Insurances'),
    }
    
