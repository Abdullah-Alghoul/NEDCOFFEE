# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
import time
from openerp.tools.translate import _
from openerp import api, fields, models, _, SUPERUSER_ID

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from lxml import etree

class hr_payment_leaves(models.Model):
    _name = 'hr.payment.leaves'
    
    name = fields.Char('Document No.', required=True, default="NEW" )
    leave_type_id= fields.Many2one('hr.holidays.status',string ='Leave Type', domain=[('limit', '=', False)] ,required=True)
    #remaining_leave_payment = fields.Float('Remaining Leave Payment',required=True)
    effective_date = fields.Date('Effective Date',required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('hr.payment.leaves'),required=True)
    employee_holidays_ids = fields.One2many('hr.payment.leaves.lines','hr_payment_leaves_id',string = 'Employee Holidays')
    user_approve_id = fields.Many2one('res.users', 'User Approve', readonly=True, select=True, copy=False)
    state = fields.Selection([('draft', 'Draft'),('waiting', 'Waiting Approval'),('approve', 'Approved'),('cancel', 'Canceled'),('refuse', 'Refuse')],
        string='Status', readonly=True, select=True, copy=False, default='draft')
    rule_input = fields.Integer('Input')
    
    _defaults = {
         'effective_date': lambda *a: str(datetime.now()),
    }
    
    @api.multi
    def button_load_employee(self):
        if self.leave_type_id:
            self.env.cr.execute('''DELETE FROM hr_payment_leaves_lines WHERE hr_payment_leaves_id = %s''' % (self.id))
            holiday_obj = self.env['hr.holidays']
            employee_ids = holiday_obj.search([('holiday_status_id', '=', self.leave_type_id.id),('type','=','add')])
            for empl in employee_ids:
                if self.env['ir.model.access'].check_groups("ned_general_hr_security.group_hr_manager_76z") and empl.employee_id.insurance_code_id.name == 'TZ0076Z':
                    holiday_ids = holiday_obj.search([('employee_id', '=', empl.employee_id.id),
                                                                    ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                    ('holiday_status_id', '=', self.leave_type_id.id)
                                                                    ])
                    remaining_leaves =0
                    for holiday in holiday_ids:
                        if holiday.type == 'add':
                            remaining_leaves += holiday.number_of_days_temp
                        elif holiday.type == 'remove':  # number of days is negative
                            remaining_leaves -= holiday.number_of_days_temp
                    if remaining_leaves > 0 and empl.employee_id.active:
                        self.env['hr.payment.leaves.lines'].create({'employee_id':empl.employee_id.id,
                                                                    'remaining_leaves':remaining_leaves,
                                                                    'hr_payment_leaves_id':self.id,
                                                                    'allocated_days':remaining_leaves,
                                                                    })
                elif self.env['ir.model.access'].check_groups("ned_general_hr_security.group_hr_manager_68z") and empl.employee_id.insurance_code_id.name == 'TZ0068Z':
                    holiday_ids = holiday_obj.search([('employee_id', '=', empl.employee_id.id),
                                                                    ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                    ('holiday_status_id', '=', self.leave_type_id.id)
                                                                    ])
                    remaining_leaves =0
                    for holiday in holiday_ids:
                        if holiday.type == 'add':
                            remaining_leaves += holiday.number_of_days_temp
                        elif holiday.type == 'remove':  # number of days is negative
                            remaining_leaves -= holiday.number_of_days_temp
                    if remaining_leaves > 0 and empl.employee_id.active:
                        self.env['hr.payment.leaves.lines'].create({'employee_id':empl.employee_id.id,
                                                                    'remaining_leaves':remaining_leaves,
                                                                    'hr_payment_leaves_id':self.id,
                                                                    'allocated_days':remaining_leaves,
                                                                    })
        return True
    
    @api.multi
    def set_to_draft(self):
        self.state = 'draft'
    
    @api.multi
    def button_confirm(self):
        if self.state == 'draft':
            self.write({'state': 'waiting'})
            if self.employee_holidays_ids:
                for line in self.employee_holidays_ids:
                    vals = {
                          'name': 'Payment ' + self.leave_type_id.name,
                          'holiday_status_id':self.leave_type_id.id,
                          'employee_id':line.employee_id.id, 
                          'type':'remove',
                          'date_from': self.effective_date,
                          'date_to': self.effective_date,
                          'number_of_days_temp':line.allocated_days,
                          'transfer_old_leave': False,
                          'no_send_email': True,
                          'check_payment_leaves':True,
                          }
                    id = self.env['hr.holidays'].create(vals)
                    line.hr_holidays_id= id
    @api.multi
    def button_approve(self):
        if self.state == 'waiting':
            self.write({'state': 'approve','user_approve_id': self.env.uid})
            if self.employee_holidays_ids:
                rule_input_ids = self.env['hr.rule.input'].search([('code','=','TTPT')])
                if rule_input_ids:
                    res={
                        'hr_salary_rule_code': 'BDKTT',
                         'name':'TTPT ' + self.effective_date,
                         'date_from':self.effective_date,
                         'company_id':self.company_id.id,
                         }
                    rule_input_id = self.env['rule.input'].create(res)
                    self.rule_input = rule_input_id.id
                    for line in self.employee_holidays_ids:
                        contract_obj = self.env['hr.contract'].search([('employee_id','=',line.employee_id.id)],order='id desc',limit=1)
                        if contract_obj:
                            vals = {
                                  'employee_id':line.employee_id.id,
                                  'name':rule_input_ids.id,
                                  'value':line.amount,
                                  'hr_salary_rule_code':rule_input_ids.input_id.code,
                                  'rule_id':rule_input_ids.input_id.id,
                                  'contract_id':contract_obj.id,
                                  'rule_input_id':rule_input_id.id,
                                  }
                            self.env['rule.input.line'].create(vals)
                        # Approve Leave
                        for line in self.employee_holidays_ids:
                            line.hr_holidays_id.signal_workflow('validate')
                            line.hr_holidays_id.signal_workflow('second_validate')
                            
    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
        if self.employee_holidays_ids:
            for line in self.employee_holidays_ids:
                self.env.cr.execute('''DELETE FROM hr_holidays WHERE id = %s''' % (line.hr_holidays_id.id))
        if self.rule_input:
            rule_input_obj = self.env['rule.input'].browse(self.rule_input)
            rule_input_obj.unlink()
    
class hr_payment_leaves_lines(models.Model):
    _name = 'hr.payment.leaves.lines'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        ids = []
        res = super(hr_payment_leaves_lines, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ['form']:
            doc = etree.XML(res['arch'])
             
            for node in doc.xpath("//field[@name='employee_id']"):
                if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_76z"):
                    employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0076Z')])
                    node.set('domain', "[('id','in',"+str(employee_ids)+")]")
                
            xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
    hr_payment_leaves_id= fields.Many2one('hr.payment.leaves',string= 'Hr Payment Leave')
    employee_id= fields.Many2one('hr.employee',string= 'Employees',domain=[('salary_manager_ids', '=', False)],required=True)
    remaining_leaves = fields.Float(compute='get_holidays', string='Remaining Leaves', store=True)
    net_salary = fields.Float(compute='get_holidays', string='Net Salary', store=True)
    salary_per_day = fields.Float(compute='get_holidays', string='Net Salary per Day', store=True)
    allocated_days = fields.Float('Allocated Days')
    amount= fields.Float(compute='get_holidays',string='Amount', store=True)
    leave_type_id= fields.Many2one(related='hr_payment_leaves_id.leave_type_id',string ='Leave Type', domain=[('limit', '=', False)] ,required=True)
    remaining_leaves_after = fields.Float(compute='get_holidays',string='Remaining Leaves After', store=True)
    hr_holidays_id = fields.Many2one('hr.holidays',string='holiday')
    
    @api.depends('employee_id','allocated_days')
    def get_holidays(self):
        for line in self:
            remaining_leaves =0
            if line.leave_type_id and line.employee_id:
                holiday_ids = self.env['hr.holidays'].search([('employee_id', '=', line.employee_id.id),
                                                                ('state', 'in', ['confirm', 'validate1', 'validate']),
                                                                ('holiday_status_id', '=', line.leave_type_id.id)
                                                                ])
                for holiday in holiday_ids:
                    if holiday.type == 'add':
                        if holiday.state == 'validate':
                            remaining_leaves += holiday.number_of_days_temp
                    elif holiday.type == 'remove':  # number of days is negative
                        remaining_leaves -= holiday.number_of_days_temp
            line.remaining_leaves = remaining_leaves
            allocated_days =0
            if line.allocated_days !=0:
                allocated_days = line.allocated_days
            if line.allocated_days != allocated_days:
                line.allocated_days =remaining_leaves
            if line.allocated_days:
#                 hr_contract_obj = self.env['hr.contract'].search(self.env.cr, SUPERUSER_ID, [('employee_id','=',line.employee_id.id)])
                contract_obj = self.env['hr.contract'].search([('employee_id','=',line.employee_id.id)],order='id desc',limit=1)
#                 hr_contract_obj = self.env['hr.attendance'].get_active_contracts(line.employee_id.id, line.hr_payment_leaves_id.effective_date)
#                 if len(hr_contract_obj) == 0:
#                     raise UserError(_('You has not permission with this person or has not Contract running in %s')%line.hr_payment_leaves_id.effective_date)
#                 contract_obj = self.env['hr.contract'].browse(hr_contract_obj[0])
                line.amount = contract_obj.wage / 26 * line.allocated_days
                line.net_salary = contract_obj.wage
                line.salary_per_day = contract_obj.wage / 26
                line.remaining_leaves_after = line.remaining_leaves - line.allocated_days
        return True
    
    @api.multi
    def print_report(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_exist_holidays'}
    
    @api.model
    @api.multi          
    @api.onchange('allocated_days')      
    def rase_allocated_days(self):
        if self.allocated_days:
            if self.allocated_days > self.remaining_leaves:
                self.allocated_days = self.remaining_leaves
                warning = {
                    'title': _('Warning!'),
                    'message': _('Days allocated bigger days payment leaves.'),
                }
                return {'warning': warning}   
