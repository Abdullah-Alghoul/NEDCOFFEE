# -*- coding: utf-8 -*-
from operator import itemgetter

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil import relativedelta
import time

class HrAdvancePayment(models.Model):
    _name = "hr.advance.payment"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    @api.depends('amount','payment_history_ids.state')
    def _amount_paid(self):
        currency = self.env['res.currency']
        for payment in self:
            amount_paid = 0
            for history in payment.payment_history_ids:
                if history.payment:
                    amount_paid += history.payment_amount
            payment.update({'amount_paid': amount_paid})
            
    @api.model
    def _default_currency_id(self):
        currency_id = self.env.user.company_id.currency_id
        return currency_id
    
    name = fields.Char('Reference', size=128, required=True, readonly=True, states={'draft': [('readonly', False)]}, default="New")
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    period = fields.Integer('Period (month)', default=3, required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', 'Department', readonly=True, states={'draft': [('readonly', False)]})
    job_id = fields.Many2one('hr.job', 'Job', readonly=True, states={'draft': [('readonly', False)]})
    
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('hr.advance.payment'), readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    exchange_rate = fields.Float('Exchange Rate', digits=(16, 2), required=True, readonly=True, states={'draft': [('readonly', False)]}, default=1.0)
    amount = fields.Float('Amount', digits=(16, 0), required=True, readonly=True, states={'draft': [('readonly', False)]})
    amount_paid = fields.Float(compute="_amount_paid", string='Amount Paid', digits=(16, 0), store=True)
    
    advance_payment_ids = fields.One2many('hr.advance.payment.line', 'advance_payment_id', 'Advance Payment Line', readonly=True, states={'draft': [('readonly', False)]})
    payment_history_ids = fields.One2many('hr.advance.payment.history', 'advance_payment_id', 'Advance Payment History', readonly=True, states={'confirmed': [('readonly', False)]})
    
    notes = fields.Text(string="Notes")
   
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False, track_visibility="onchange")
    approved_by = fields.Many2one('res.users', string='User Approve', readonly=True, track_visibility="onchange")
   
    state = fields.Selection([('draft', 'Draft'),('confirmed','Confirmed'),('done','Done'),('cancel', 'Cancelled')], 'State', readonly=True, default="draft")
    
    @api.multi
    def unlink(self):
        for payment in self:
            if payment.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(HrAdvancePayment, self).unlink()
    
    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.amount <= 0:
                raise UserError(_("Amount must be greater than 0."))
            return True
    
    @api.constrains('period')
    def _check_period(self):
        for payment in self:
            if payment.period <= 0:
                raise UserError(_("Period must be greater than 0."))
            return True
        
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if not self.employee_id:
            return {'domain': {'department_id': [],'job_id': []}}
        self.update({'department_id': self.employee_id.department_id.id, 'job_id': self.employee_id.job_id.id})
        domain = {'department_id': [('id', '=', self.employee_id.department_id.id)],
                  'job_id': [('id','=', self.employee_id.job_id.id)]}
        return {'domain': domain} 
    
    @api.multi
    def button_load(self):
        payment_line = self.env['hr.advance.payment.line']
        payment_history = self.env['hr.advance.payment.history']
        if self.period > 0:
            self.env.cr.execute('''DELETE FROM hr_advance_payment_line WHERE advance_payment_id = %s;
            DELETE FROM hr_advance_payment_history WHERE advance_payment_id = %s''' % (self.id,self.id))
            amount = round(self.amount / self.period)
            date_from = datetime.strptime(self.date[0:8]+'25', '%Y-%m-%d')
            date_cofig = datetime.strptime(self.date, '%Y-%m-%d')
            count_months = 0
            count = 1
            while count <= self.period:
                if date_cofig > date_from:
                    count_months += 1
                count += 1
                count_months += 1
                date = str(date_from + relativedelta.relativedelta(months=+count_months-1))
                payment_line.create({'sequence': 5, 'date': date, 'payment_amount': amount, 
                    'advance_payment_id': self.id, 'currency_id': self.currency_id.id, 'company_id': self.company_id.id, 'state': 'draft'})
                payment_history.create({'sequence': 5, 'date': date, 'payment_amount': amount, 'payment': False, 
                    'advance_payment_id': self.id, 'currency_id': self.currency_id.id, 'company_id': self.company_id.id, 'state': 'draft'})
        return True
            
    
    @api.v7    
    def action_confirm(self, cr, uid, ids, context=None):
        payslip_pool = self.pool.get('hr.payslip')
        totals = 0
        for line in self.browse(cr, uid, ids):
            for payment_line in line.advance_payment_ids:
                totals +=  payment_line.payment_amount
                
            if line.amount != totals:
                raise UserError(_("Amount improper refund."))
            
            cr.execute('''
            SELECT id, number, state
            FROM hr_payslip
            WHERE employee_id=%s AND date_to >= '%s' AND date_from <='%s' 
            '''%(line.employee_id.id, line.date, line.date))
            res = cr.fetchall()
            for payslip in res:
                if payslip[2] == 'done':
                    raise UserError(_('Warning!'),_("Payslip number '%s' has been paid!\n You are not able to confirm this Payment!")%(payslip[1]))
#                 elif payslip[2] != 'cancel':
#                     cr.execute('''
#                     INSERT INTO hr_advance_payment_payslip_rel(payslip_id,payment_id) VALUES(%s,%s)
#                     '''%(payslip[0],line.id))
                    #Thanh: Recompute Related Payslip to update Advanced Amount
            self.write(cr, uid, [line.id], {'state':'confirmed','approved_by':uid, 'date_approve': time.strftime('%Y-%m-%d %H:%M:%S')})
            if res:
                payslip_pool.compute_sheet(cr, uid, [x[0] for x in res], context)
        return True
    
    @api.v7 
    def action_cancel(self, cr, uid, ids, context=None):
        payslip_pool = self.pool.get('hr.payslip')
        for line in self.browse(cr, uid, ids):
            if line.state == "done": 
                raise UserError(_('You cannot cancel.'))
            cr.execute('''SELECT hp.id, hp.number, hp.state FROM hr_advance_payment_payslip_rel app join
                hr_payslip hp on app.payslip_id = hp.id WHERE app.payment_id = %s'''%(line.id))
            res = cr.fetchall()
            for payslip in res:
                if payslip[2] == 'done':
                    raise UserError(_('Warning!'),_("Payslip number '%s' has been paid!\n You are not able to cancel this Payment!")%(res[0][0]))
                elif payslip[2] != 'cancel':
                    cr.execute('''
                    DELETE FROM hr_advance_payment_payslip_rel WHERE payment_id=%s
                    '''%(line.id))
                    #Thanh: Recompute Related Payslip to update Advanced Amount
            self.write(cr, uid, [line.id], {'state':'cancel'})
            if res:
                payslip_pool.compute_sheet(cr, uid, [x[0] for x in res], context)
        return True
    
    @api.multi
    def set_to_draft(self):
        self.write({'state':'draft', 'user_id':self.env.uid, 'create_date': time.strftime('%Y-%m-%d %H:%M:%S'),'approved_by':False, 'date_approve': False})
    
class HrAdvancePaymentLine(models.Model):
    _name = "hr.advance.payment.line"
    
    sequence = fields.Integer('Seq')
    date = fields.Date('Expected Date', required=True, default=fields.Datetime.now)
    payment_amount = fields.Float('Amount', digits=(16, 0), required=True)
    
    advance_payment_id = fields.Many2one('hr.advance.payment', 'Advance Payment', ondelete='cascade', index=True, copy=False)
    currency_id = fields.Many2one(related='advance_payment_id.currency_id', string='Currency', store=True)
    company_id = fields.Many2one(related='advance_payment_id.company_id', string='Company', store=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('done','Done'),('cancel', 'Cancelled')], 
        related='advance_payment_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
class HrAdvancePaymentHistory(models.Model):
    _name = "hr.advance.payment.history"
    
    sequence = fields.Integer('Seq')
    date = fields.Date('Expected Date', required=True, default=fields.Datetime.now)
    payment_date = fields.Date('Payment Date', readonly=True)
    payment_amount = fields.Float('Amount', digits=(16, 0), required=True)
    payment = fields.Boolean(string="Payment", default=False)
    
    advance_payment_id = fields.Many2one('hr.advance.payment', 'Advance Payment', ondelete='cascade', index=True, copy=False)
    currency_id = fields.Many2one(related='advance_payment_id.currency_id', string='Currency', store=True)
    exchange_rate = fields.Float(related='advance_payment_id.exchange_rate', string='Exchange Rate', store=True)
    company_id = fields.Many2one(related='advance_payment_id.company_id', string='Company', store=True)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'),('done','Done'),('cancel', 'Cancelled')], 
        related='advance_payment_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    @api.multi
    def unlink(self):
        for models in self:
            if models:
                raise UserError(_('You can only delete draft or cancel.'))
        return super(HrAdvancePaymentHistory, self).unlink()