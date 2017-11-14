# -*- coding: utf-8 -*-
from openerp import api, fields, models

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    _order = "parent_left"
    _parent_order = "code"
    _parent_store = True
    
    @api.one
    @api.depends('child_ids')
    def _child_compute(self):
        for account in self:
            account.child_complete_ids = map(lambda x: x.id, [child for child in account.child_ids])
    
    @api.one
    @api.depends('child_ids.level','parent_id')
    def _get_level(self):
        for account in self:
            #we may not know the level of the parent at the time of computation, so we
            # can't simply do res[account.id] = account.parent_id.level + 1
            level = 0
            parent = account.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            account.level = level
    
    #THANH: Add theses field to manage Analytic Hierarchy
    parent_id = fields.Many2one('account.analytic.account', string='Parent Analytic Account')
    parent_left = fields.Integer('Parent Left', select=1)
    parent_right = fields.Integer('Parent Right', select=1)
    level = fields.Integer(compute='_get_level', string='Level')
                   
    child_ids = fields.One2many('account.analytic.account', 'parent_id', string='Child Accounts')
    child_complete_ids = fields.Many2many(compute='_child_compute', relation='account.analytic.account', string="Account Hierarchy")
    
    #THANH: inherit these field to add more function compute value to parent account
    @api.multi
    def _compute_debit_credit_balance(self):
        for account in self:
            analytic_line_obj = self.env['account.analytic.line']
            #THANH: get full account include children
            full_accounts = self.search([('parent_id', 'child_of', account.id)])
            domain = [('account_id', 'in', full_accounts.mapped('id'))]
            
            if self._context.get('from_date', False):
                domain.append(('date', '>=', self._context['from_date']))
            if self._context.get('to_date', False):
                domain.append(('date', '<=', self._context['to_date']))
            
            account_amounts = analytic_line_obj.search_read(domain, ['amount'])
                
            #THANH: new computation
            debit = 0.0
            credit = 0.0
            for account_amount in account_amounts:
                if account_amount['amount'] < 0.0:
                    debit += account_amount['amount']
                else:
                    credit += account_amount['amount']
    
            account.debit = abs(debit)
            account.credit = credit
            account.balance = account.credit - account.debit
            
    balance = fields.Monetary(compute='_compute_debit_credit_balance', string='Balance')
    debit = fields.Monetary(compute='_compute_debit_credit_balance', string='Debit')
    credit = fields.Monetary(compute='_compute_debit_credit_balance', string='Credit')
    
class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('from_date'):
            args.append(['date', '>=', context.get('from_date')])
        if context.get('to_date'):
            args.append(['date', '<=', context.get('to_date')])
        return super(account_analytic_line, self).search(args, offset, limit, order, count=count)
    
#         return recs.name_get()