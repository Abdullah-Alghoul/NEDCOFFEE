# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.tools import float_is_zero, float_compare
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, RedirectWarning, ValidationError, Warning
import openerp.addons.decimal_precision as dp

import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountPartnerReconciliation(models.Model):
    _name = "account.partner.reconciliation"
    _description = "Partner Reconciliation"
    _order = "reconcile_date desc"
    
    @api.model
    def _default_currency(self):
#         journal = self._default_journal()
#         return journal.currency_id or journal.company_id.currency_id
        return self.env.user.company_id.currency_id
    
    partner_id = fields.Many2one('res.partner', string='Partner', 
                                 domain="[(context.get('filter_customer',context.get('filter_supplier','active')), '=', True)]",
                                 required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    reconcile_date = fields.Date(string='Reconcile Date', required=True, default=time.strftime(DATE_FORMAT), readonly=True, states={'draft': [('readonly', False)]})#, readonly=True, states={'draft':[('readonly',False)]})
    
    fixed_amount = fields.Monetary(string='Reconciled Amount', required=True, default=0.0, currency_field='currency_id', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, default=_default_currency, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, domain="[('type','=','general'), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company',
        required=True, default=lambda self: self.env['res.company']._company_default_get('account.partner.reconciliation'), readonly=True, states={'draft': [('readonly', False)]})
    receivable_lines = fields.One2many('account.partner.reconciliation.line', 'header_receivable_id', string='Receivables', readonly=True, states={'draft': [('readonly', False)]})
    payable_lines = fields.One2many('account.partner.reconciliation.line', 'header_payable_id', string='Payables', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
            ('draft','Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', default='draft', readonly=True, states={'draft': [('readonly', False)]})
    move_id = fields.Many2one('account.move', string='Entry', readonly=True)
    
    @api.onchange('receivable_lines', 'payable_lines', 
                  'receivable_lines.allocated_amount', 
                  'payable_lines.allocated_amount')
    def _onchange_amount(self):
        reveivable = 0.0
        payable = 0.0
        reveivable_fixed = 0.0
        payable_fixed = 0.0
        for recei in self.receivable_lines:
            reveivable += recei.residual
            reveivable_fixed += recei.allocated_amount or recei.residual
        for pay in self.payable_lines:
            payable += pay.residual
            payable_fixed += pay.allocated_amount or pay.residual
            
        self.fixed_amount = reveivable_fixed if (reveivable - payable) < 0 else payable_fixed
    
    @api.multi
    def open_entries(self):
        move_line_ids = []
        for move_line in self.move_id.line_ids:
            move_line_ids.append(move_line.id)
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_line_ids)],
        }
        
    @api.multi
    def action_cancel(self):
        for rec in self:
            rec.move_id.line_ids.remove_move_reconcile()
            rec.move_id.button_cancel()
            rec.move_id.unlink()
            rec.state = 'cancel'
    
    @api.multi
    def set_to_draft(self):
        for rec in self:
            rec.state = 'draft'
    
    @api.multi
    def get_allocation_amount(self):
        reveivable = 0.0
        payable = 0.0
        reveivable_fixed = 0.0
        payable_fixed = 0.0
        for recei in self.receivable_lines:
            reveivable += recei.residual
            reveivable_fixed += recei.allocated_amount or recei.residual
        for pay in self.payable_lines:
            payable += pay.residual
            payable_fixed += pay.allocated_amount or pay.residual
            
        fixed_amount = reveivable_fixed if (reveivable - payable) < 0 else payable_fixed
        return fixed_amount
    
    @api.multi
    def allocate_balance(self):
        for rec in self:
            original_fixed_amount = rec.get_allocation_amount()
#             print 'ORI: ', original_fixed_amount
            #THANH: auto allocation
            fixed_amount = original_fixed_amount#rec.fixed_amount
            for recei in rec.receivable_lines:
                if fixed_amount > 0:
                    if fixed_amount > recei.residual:
                        recei.allocated_amount = recei.residual
                    else:
                        recei.allocated_amount = fixed_amount
                    fixed_amount -= recei.residual
                else:
                    recei.allocated_amount = 0.0
                if recei.allocated_amount == recei.residual:
                    recei.full_reconcile = True
#                 print 'AAA', recei.allocated_amount, fixed_amount
                
            fixed_amount = original_fixed_amount#rec.fixed_amount
            for pay in rec.payable_lines:
                if fixed_amount > 0:
                    if fixed_amount > pay.residual:
                        pay.allocated_amount = pay.residual
                    else:
                        pay.allocated_amount = fixed_amount
                    fixed_amount -= pay.residual
                else:
                    pay.allocated_amount = 0.0
                if pay.allocated_amount == pay.residual:
                    pay.full_reconcile = True
                
    @api.multi
    def load_data(self):
        for rec in self:
            self.env.cr.execute("delete from account_partner_reconciliation_line where header_receivable_id=%s"%(rec.id))
            sql = '''
                SELECT distinct aml.id
                FROM account_move_line aml
                    LEFT JOIN account_account acc on aml.account_id=acc.id
                    
                    JOIN account_move_line aml2 on aml2.move_id = aml.move_id
                        JOIN account_account acc2 on aml2.account_id=acc2.id
                        
                WHERE aml.partner_id=%s and round(aml.amount_residual,%s) != 0.0 --aml.reconciled = false 
                    and ((acc.type='receivable' and aml.debit > 0) or (acc.type='payable' and aml.debit > 0))
                    and aml.date <= '%s'
                    and acc2.type not in ('receivable','payable')
            '''%(rec.partner_id.id, self.currency_id.decimal_places, rec.reconcile_date)
            self.env.cr.execute(sql)
            result = self.env.cr.fetchall()
            if len(result):
                for line in result:
                    self.env['account.partner.reconciliation.line'].create({'header_receivable_id':rec.id, 'move_line_id':line[0]})
            
            self.env.cr.execute("delete from account_partner_reconciliation_line where header_payable_id=%s"%(rec.id))
            sql = '''
                SELECT distinct aml.id
                FROM account_move_line aml
                    LEFT JOIN account_account acc on aml.account_id=acc.id
                    
                    JOIN account_move_line aml2 on aml2.move_id = aml.move_id
                        JOIN account_account acc2 on aml2.account_id=acc2.id
                        
                WHERE aml.partner_id=%s and round(aml.amount_residual,%s) != 0.0
                    and ((acc.type='payable' and aml.credit > 0) or (acc.type='receivable' and aml.credit > 0))
                    and aml.date <= '%s'
                    and acc2.type not in ('receivable','payable')
            '''%(rec.partner_id.id, self.currency_id.decimal_places, rec.reconcile_date)
            self.env.cr.execute(sql)
            result = self.env.cr.fetchall()
            if len(result):
                for line in result:
                    self.env['account.partner.reconciliation.line'].create({'header_payable_id':rec.id, 'move_line_id':line[0]})
                    
            #THANH: auto allocation
            receivable, payable = 0.0, 0.0
            for recei in rec.receivable_lines:
                receivable += recei.company_currency_id.round(recei.residual)
            for pay in rec.payable_lines:
                payable += pay.company_currency_id.round(pay.residual)
            fixed_amount = receivable if (receivable - payable) < 0 else payable
            rec.fixed_amount = fixed_amount
            for recei in rec.receivable_lines:
                residual = recei.company_currency_id.round(recei.residual)
                if receivable < payable:
                    recei.allocated_amount = residual
                elif fixed_amount > 0:
                    if fixed_amount > recei.residual or receivable == payable:
                        recei.allocated_amount = residual
                    else:
                        recei.allocated_amount = fixed_amount
                    fixed_amount -= residual
                    
            for pay in rec.payable_lines:
                residual = pay.company_currency_id.round(pay.residual)
                if payable < receivable:
                    pay.allocated_amount = residual
                elif fixed_amount > 0:
                    if fixed_amount > pay.residual or receivable == payable:
                        pay.allocated_amount = residual
                    else:
                        pay.allocated_amount = fixed_amount
                    fixed_amount -= residual
        return
    
    @api.multi
    def action_reconcile(self):
        move_obj = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        
        allocated_reveivable = 0.0
        allocated_payable = 0.0
        for recei in self.receivable_lines:
            allocated_reveivable += recei.allocated_amount
        for pay in self.payable_lines:
            allocated_payable += pay.allocated_amount
        
        if float_compare(allocated_reveivable, allocated_payable, precision_digits=2) != 0:
            raise UserError(_('Receivables Allocated Amount must be equal to Payables Allocated Amount.'))
        
        if not len(self.receivable_lines) or not len(self.payable_lines):
            raise UserError(_('Receivables or Payables is missing ! You cannot excute this feature.'))
        
        if not self.journal_id.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % self.journal_id.name)
        if not self.journal_id.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % self.journal_id.name)
        name = self.journal_id.with_context(ir_sequence_date=self.reconcile_date).sequence_id.next_by_id()
        
        company_currency = self.company_id.currency_id
        
        ctx = {}
        ctx['date'] = self.reconcile_date
        ctx['check_move_validity'] = False
        move_vals = {
            'name': name,
            'journal_id': self.journal_id.id,
            'date': self.reconcile_date,
            'doc_date': self.reconcile_date,
            'narration': _('Bù trừ công nợ của đối tác ') + _(self.partner_id.name),
            'company_id': self.company_id.id,
        }
        move_id = move_obj.with_context(ctx).create(move_vals)
        
#         total = 0.0
        for recei in self.receivable_lines:
            #THANH: Create move line for the same partner
#             if recei.allocated_amount > abs(recei.move_line_id.amount_residual):
            if float_compare(recei.allocated_amount, abs(recei.move_line_id.amount_residual), precision_digits=self.currency_id.round_decimal_places) > 0:
                raise Warning(_('Amount Due of Receivables has been changed, please click button Load Data to refresh new Amount Due.'))
            if recei.allocated_amount > 0:
                vals = {
                    'name': _('Bù trừ công nợ chứng từ số %s')%(_(recei.ref)),
                    'partner_id': self.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'ref': name,
                    'date': self.reconcile_date,
                    'debit': 0.0,
                    'credit': company_currency.round(recei.allocated_amount),
                    'account_id': recei.account_id.id,
                    'move_id': move_id.id,
                }
                new_line = move_line_pool.with_context(ctx).create(vals)
                rec_ids = [recei.move_line_id.id,new_line.id]
                reconcile_lines = move_line_pool.browse(rec_ids)
                reconcile_lines.auto_reconcile_lines()
                
#                 total += company_currency.round(recei.allocated_amount)
#                 print 'AAAA', recei.allocated_amount, company_currency.round(recei.allocated_amount), total
                
#         total = 0.0
        for pay in self.payable_lines:
            if float_compare(pay.allocated_amount, abs(pay.move_line_id.amount_residual), precision_digits=self.currency_id.round_decimal_places) > 0:
                raise Warning(_('Amount Due of Payables has been changed, please click button Load Data to refresh new Amount Due.'))
            
            if pay.allocated_amount > 0:
                vals = {
                    'name': _('Bù trừ công nợ chứng từ số %s')%(_(pay.ref)),
                    'partner_id': self.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'ref': name,
                    'date': self.reconcile_date,
                    'debit': company_currency.round(pay.allocated_amount),
                    'credit': 0.0,
                    'account_id': pay.account_id.id,
                    'move_id': move_id.id,
                }
                new_line = move_line_pool.with_context(ctx).create(vals)
                rec_ids = [pay.move_line_id.id,new_line.id]
                reconcile_lines = move_line_pool.browse(rec_ids)
                reconcile_lines.auto_reconcile_lines()
                
#                 total += company_currency.round(pay.allocated_amount)
#                 print 'BBBB', pay.allocated_amount, company_currency.round(pay.allocated_amount), total
                
        move_id.post()
        self.move_id = move_id
        self.state = 'posted'
       
class AccountPartnerReconciliationLine(models.Model):
    _name = "account.partner.reconciliation.line"
    _order = 'entry_date,due_date,move_line_id'
    
    @api.depends('move_line_id')
    def _compute_line(self):
        for line in self:
            line.amount_currency = abs(line.move_line_id.amount_currency)
            line.amount_residual_currency = abs(line.move_line_id.amount_residual_currency)
            line.amount_paid_currency = line.amount_currency - line.amount_residual_currency
            
            line.amount_total = abs(line.move_line_id.balance)
            line.residual = abs(line.move_line_id.amount_residual)
            line.amount_paid = line.amount_total - line.residual
            
            #THANH: get reference from move line or account move
            line.ref = line.move_line_id.ref or line.move_line_id.narration
            
    header_receivable_id = fields.Many2one('account.partner.reconciliation', string="Header Receivable", ondelete='cascade')
    header_payable_id = fields.Many2one('account.partner.reconciliation', string="Header Payable", ondelete='cascade')
    
    full_reconcile = fields.Boolean(string='Full Reconcile', default=False)
    move_line_id = fields.Many2one('account.move.line', string="Move", required=False)
    
    ref = fields.Char(compute='_compute_line', string='Reference', store=True, readonly=True)
    account_id = fields.Many2one('account.account', related='move_line_id.account_id', string='Account', store=True, readonly=True)
    entry_date = fields.Date(related='move_line_id.date', string='Entry Date', store=True, readonly=True)
    due_date = fields.Date(related='move_line_id.date_maturity', string='Due Date', store=True, readonly=True)
    
    amount_currency = fields.Monetary(compute='_compute_line', currency_field='currency_id', string='Amount Currency', store=True, readonly=True)
    amount_paid_currency = fields.Monetary(compute='_compute_line', currency_field='currency_id', string='Paid Amount Currency', store=True, readonly=True)
    amount_residual_currency = fields.Monetary(compute='_compute_line', currency_field='currency_id', string='Amount Currency Due', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='move_line_id.currency_id', string='Currency', store=True, readonly=True)
    
    amount_total = fields.Monetary(compute='_compute_line', string='Original Amount', currency_field='company_currency_id', store=True, readonly=True)
    amount_paid = fields.Monetary(compute='_compute_line', string='Paid Amount', currency_field='company_currency_id', store=True, readonly=True)
    residual = fields.Monetary(compute='_compute_line', string='Amount Due', currency_field='company_currency_id', store=True, readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='move_line_id.company_id.currency_id', string='Currency', store=True, readonly=True)
    
    allocated_amount = fields.Monetary(string='Allocated Amount', default=0.0, required=True, currency_field='company_currency_id')
    
    @api.onchange('full_reconcile')
    def _onchange_full_reconcile(self):
        if self.full_reconcile:
            self.allocated_amount = self.residual
        else:
            self.allocated_amount = 0.0
    
    @api.onchange('allocated_amount')
    def _onchange_allocated_amount(self):
        if self.residual == self.allocated_amount:
            self.full_reconcile = True
        else:
            self.full_reconcile = False