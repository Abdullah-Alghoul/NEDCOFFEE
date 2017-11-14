# -*- coding:utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import api, tools


class hr_contract(osv.osv):
    _inherit = 'hr.contract'
    
    def _get_default_working_hours(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        calendar_ids = self.pool.get('resource.calendar').search(cr, uid, [('company_id', '=', company_id)], context=context)
        return calendar_ids and calendar_ids[0] or False
    
    _columns = {    
        # THANH: Will be removed
        'other_wage': fields.float('Basic Wage', digits=(16, 2), required=False, help='Use this field to calculate Insurances'),
        
        # Set Working Schedule to be required - Relating to calculate Default Working Days
        'working_hours': fields.many2one('resource.calendar', 'Working Schedule'),
        
        # Overtime Section
        'overtime_rate': fields.float('Amount by an Hour', digits=(16, 0), required=True, compute='_get_overtime_rate', store=True),
        'hours_by_day': fields.float('Hours by day', digits=(16, 2), required=True),
        'days_by_month': fields.float('Days by month', digits=(16, 0), required=True),
        
        # Setting Salary Rules
        'contract_salary_rule_ids': fields.one2many('hr.contract.salary.rule', 'contract_id', 'Salary Rules'),
        
        }
    
    _defaults = {
        'overtime_rate': 0.0,
        'hours_by_day': 8,
        'days_by_month': 26,
        
        'working_hours': _get_default_working_hours,
    }
    
    # Toan: calculator overtime_rate
    @api.one 
    @api.depends('hours_by_day', 'days_by_month', 'wage')
    def _get_overtime_rate(self):
        if self.hours_by_day == 0 or self.days_by_month == 0:
            self.overtime_rate = 0
        else:
            self.overtime_rate = self.wage / self.days_by_month / self.hours_by_day
hr_contract()

class hr_contract_salary_rule(osv.osv):
    _name = 'hr.contract.salary.rule'
    _description = 'Contract Salary Rules'
    _order = 'sequence'
    
    def _onchange_salary_rule(self, cr, uid, ids, context=None):
        # direct access to the m2m table is the less convoluted way to achieve this (and is ok ACL-wise)
        cr.execute('''SELECT id FROM hr_contract_salary_rule
        WHERE salary_rule_id in (%s)
        ''' % (','.join(map(str, ids))))
        return [i[0] for i in cr.fetchall()]
    
    _columns = {
        'contract_id': fields.many2one('hr.contract', 'Contract', required=True, ondelete='cascade'),
        'salary_rule_id': fields.many2one('hr.salary.rule', 'Rule', required=True),
        'sequence': fields.related('salary_rule_id', 'sequence', type='integer', readonly=True,
               store={
                'hr.contract.salary.rule': (lambda self, cr, uid, ids, c={}: ids, ['salary_rule_id'], 10),
                'hr.salary.rule': (_onchange_salary_rule, ['sequence'], 10)},
               string='Sequence'),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Payroll'), required=True),
    }
hr_contract_salary_rule()