# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.tools import float_is_zero
from openerp.tools.misc import formatLang

from openerp.exceptions import UserError, RedirectWarning, ValidationError

import openerp.addons.decimal_precision as dp

import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
    
class AccountInvoiceReconciliation(models.Model):
    _name = "account.invoice.reconciliation"
    _description = "Invoice Reconciliation"
    
    @api.model
    def _default_currency(self):
#         journal = self._default_journal()
#         return journal.currency_id or journal.company_id.currency_id
        return self.env.user.company_id.currency_id
    
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, readonly=True, states={'draft': [('readonly', False)]})
    reconcile_date = fields.Date(string='Reconcile Date', required=True, default=time.strftime(DATE_FORMAT), readonly=True, states={'draft': [('readonly', False)]})#, readonly=True, states={'draft':[('readonly',False)]})
#     type = fields.Selection([
#             ('invoice','Receivables vs Payables'),
#             ('payment_receivable','Payments vs Receivables'),
#             ('payment_payable','Payments vs Payables'),
#         ], string='Reconcile Type', required=True, default="invoice", readonly=True, states={'draft': [('readonly', False)]})
    
    fixed_amount = fields.Monetary(string='Reconciled Amount', required=True, default=0.0, currency_field='currency_id', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency',
        required=True, default=_default_currency, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, domain="[('type','=','general'), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', string='Company',
        required=True, default=lambda self: self.env['res.company']._company_default_get('account.invoice.reconciliation'), readonly=True, states={'draft': [('readonly', False)]})
#     company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    customer_invoice_lines = fields.One2many('account.invoice.reconciliation.line', 'header_cus_id', string='Customer Invoices', readonly=True, states={'draft': [('readonly', False)]})
    vendor_invoice_lines = fields.One2many('account.invoice.reconciliation.line', 'header_ven_id', string='Vendor Invoices', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
            ('draft','Draft'),
            ('posted', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', default='draft', readonly=True, states={'draft': [('readonly', False)]})
    move_id = fields.Many2one('account.move', string='Entry', readonly=True)
    
    @api.onchange('customer_invoice_lines', 'vendor_invoice_lines')
    def _onchange_amount(self):
        cus_amount = 0.0
        sup_amount = 0.0
        cus_fixed_amount = 0.0
        sup_fixed_amount = 0.0
        for inv in self.customer_invoice_lines:
            cus_amount += inv.residual_signed
            cus_fixed_amount += inv.allocated_amount
        for inv in self.vendor_invoice_lines:
            sup_amount += inv.residual_signed
            sup_fixed_amount += inv.allocated_amount
        self.fixed_amount = cus_fixed_amount if (cus_amount - sup_amount) < 0 else sup_fixed_amount
    
    @api.multi
    def button_journal_entries(self):
        return {
            'name': _('Journal Entry'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.move_id.id,
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
    def allocate_invoice(self):
        for rec in self:
            #THANH: auto allocation
            fixed_amount = rec.fixed_amount
            for inv in rec.customer_invoice_lines:
                if fixed_amount > 0:
                    if fixed_amount > inv.invoice_id.residual_signed:
                        inv.allocated_amount = inv.invoice_id.residual_signed
                    else:
                        inv.allocated_amount = fixed_amount
                    fixed_amount -= inv.invoice_id.residual_signed
                    
            fixed_amount = rec.fixed_amount
            for inv in rec.vendor_invoice_lines:
                if fixed_amount > 0:
                    if fixed_amount > inv.invoice_id.residual_signed:
                        inv.allocated_amount = inv.invoice_id.residual_signed
                    else:
                        inv.allocated_amount = fixed_amount
                    fixed_amount -= inv.invoice_id.residual_signed
            
    @api.multi
    def load_invoice(self):
        for rec in self:
            cus_amount = 0.0
            sup_amount = 0.0
            
            self.env.cr.execute("delete from account_invoice_reconciliation_line where header_cus_id=%s"%(rec.id))
            cus_invoices = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id), 
                                                               ('currency_id','=',self.currency_id.id), 
                                                               ('type','in',['out_invoice','in_refund']), ('state','=','open')])
            if len(cus_invoices):
                for inv in cus_invoices:
                    self.env['account.invoice.reconciliation.line'].create({'header_cus_id':rec.id, 'invoice_id':inv.id})
                    cus_amount += inv.residual_signed
            
            self.env.cr.execute("delete from account_invoice_reconciliation_line where header_ven_id=%s"%(rec.id))
            sup_invoices = self.env['account.invoice'].search([('partner_id','=',self.partner_id.id), 
                                                               ('currency_id','=',self.currency_id.id),
                                                               ('type','in',['in_invoice','out_refund']), ('state','=','open')])
            if len(sup_invoices):
                for inv in sup_invoices:
                    self.env['account.invoice.reconciliation.line'].create({'header_ven_id':rec.id, 'invoice_id':inv.id})
                    sup_amount += inv.residual_signed
            rec.fixed_amount = cus_amount if (cus_amount - sup_amount) < 0 else sup_amount
            
            #THANH: auto allocation
            rec.refresh()
            fixed_amount = rec.fixed_amount
            for inv in rec.customer_invoice_lines:
                if cus_amount < sup_amount:
                    inv.allocated_amount = inv.invoice_id.residual_signed
                elif fixed_amount > 0:
                    if fixed_amount > inv.invoice_id.residual_signed:
                        inv.allocated_amount = inv.invoice_id.residual_signed
                    else:
                        inv.allocated_amount = fixed_amount
                    fixed_amount -= inv.invoice_id.residual_signed
            for inv in rec.vendor_invoice_lines:
                if sup_amount < cus_amount:
                    inv.allocated_amount = inv.invoice_id.residual_signed
                elif fixed_amount > 0:
                    if fixed_amount > inv.invoice_id.residual_signed:
                        inv.allocated_amount = inv.invoice_id.residual_signed
                    else:
                        inv.allocated_amount = fixed_amount
                    fixed_amount -= inv.invoice_id.residual_signed
            
    @api.multi
    def action_reconcile(self):
        move_obj = self.env['account.move']
        move_line_pool = self.env['account.move.line']
        
        if not len(self.customer_invoice_lines) or not len(self.vendor_invoice_lines):
            raise UserError(_('Customer Invoices or Supplier Invoices is missing ! You cannot excute this feature.'))
        
        cus_invoice_number = ''
        sup_invoice_number = ''
        for inv in self.customer_invoice_lines:
            if inv.allocated_amount > 0:
                cus_invoice_number += inv.invoice_id.reference +','
        for inv in self.vendor_invoice_lines:
            if inv.allocated_amount > 0:
                sup_invoice_number += inv.invoice_id.reference +','
        
        #THANH: remove dau ','
        cus_invoice_number = len(cus_invoice_number) and cus_invoice_number[:-1] or cus_invoice_number
        sup_invoice_number = len(sup_invoice_number) and sup_invoice_number[:-1] or sup_invoice_number
        
        property_account_receivable_id = self.partner_id.property_account_receivable_id.id
        property_account_payable_id = self.partner_id.property_account_payable_id.id
        
        if not self.journal_id.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % self.journal_id.name)
        if not self.journal_id.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % self.journal_id.name)
        name = self.journal_id.with_context(ir_sequence_date=self.reconcile_date).sequence_id.next_by_id()
        
        ctx = {}
        ctx['date'] = self.reconcile_date
        ctx['check_move_validity'] = False
        move_vals = {
            'name': name,
            'journal_id': self.journal_id.id,
            'date': self.reconcile_date,
            'doc_date': self.reconcile_date,
            'narration': _('Bù trừ công nợ hóa đơn của đối tác ') + _(self.partner_id.name),
            'company_id': self.company_id.id,
        }
        move_id = move_obj.with_context(ctx).create(move_vals)
        for inv in self.customer_invoice_lines:
            #THANH: Create move line for the same partner
            if inv.allocated_amount > 0:
                move_line = {
                    'name': _('Bù trừ công nợ hóa đơn đầu ra số [%s]')%(_(cus_invoice_number)),
                    'partner_id': self.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'ref': name,
                    'date': self.reconcile_date,
                    'debit': 0.0,
                    'credit': inv.allocated_amount,
                    'account_id': property_account_receivable_id,
                    'move_id': move_id.id,
                }
                move_line = move_line_pool.with_context(ctx).create(move_line)
                self.env.cr.execute("SELECT id FROM account_move_line WHERE move_id=%s AND account_id=%s"%(inv.invoice_id.move_id.id, inv.invoice_id.account_id.id))
                rec_ids = [x[0] for x in self.env.cr.fetchall()]
                if len(rec_ids):
                    rec_ids.append(move_line.id)
                    reconcile_lines = move_line_pool.browse(rec_ids)
                    reconcile_lines.auto_reconcile_lines()

        for inv in self.vendor_invoice_lines:
            if inv.allocated_amount > 0:
                move_line = {
                    'name': _('Bù trừ công nợ hóa đơn đầu vào số [%s]')%(_(sup_invoice_number)),
                    'partner_id': self.partner_id.id,
                    'journal_id': self.journal_id.id,
                    'ref': name,
                    'date': self.reconcile_date,
                    'debit': inv.allocated_amount,
                    'credit': 0.0,
                    'account_id': property_account_payable_id,
                    'move_id': move_id.id,
                }
                move_line = move_line_pool.with_context(ctx).create(move_line)
                self.env.cr.execute("SELECT id FROM account_move_line WHERE move_id=%s AND account_id=%s"%(inv.invoice_id.move_id.id, inv.invoice_id.account_id.id))
                rec_ids = [x[0] for x in self.env.cr.fetchall()]
                if len(rec_ids):
                    rec_ids.append(move_line.id)
                    reconcile_lines = move_line_pool.browse(rec_ids)
                    reconcile_lines.auto_reconcile_lines()
                
        move_id.post()
        self.move_id = move_id
        self.state = 'posted'
       
class AccountInvoiceReconciliationLine(models.Model):
    _name = "account.invoice.reconciliation.line"
    _order = 'date_invoice'
    
    @api.one
    @api.depends('header_receivable_id', 'header_payable_id', 'move_line_id', 'amount_total_signed', 'residual_signed')
    def _compute_amount(self):
#         date = self.revaluation_id.date_end
#         ex_rate , rate = self.currency_id.with_context({'date':date})._get_conversion_rate(self.currency_id, self.company_currency_id)
#         self.revaluation_rate = rate
#         revaluated_balance = self.company_currency_id.round(self.foreign_balance * ex_rate)
#         for this in self:
#             self.amount_total_signed = self.
#             self.unrealized_gain_loss =  abs(revaluated_balance) - abs(self.balance)
        a = 0
        
    header_receivable_id = fields.Many2one('account.invoice.reconciliation', string="Header Customer", ondelete='cascade')
    header_payable_id = fields.Many2one('account.invoice.reconciliation', string="Header Vendor", ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', string="Move", required=False)
    
    entry_date = fields.Date(related='move_line_id.date', string='Entry Date', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='move_line_id.currency_id', string='Currency', store=True, readonly=True)
    
    amount_total_signed = fields.Monetary(compute='_compute_amount', string='Total', currency_field='currency_id', store=True, readonly=True)
    residual_signed = fields.Monetary(compute='_compute_amount', string='Amount Due', currency_field='currency_id', store=True, readonly=True)
    allocated_amount = fields.Monetary(string='Allocated Amount', default=0.0, required=True, currency_field='currency_id')
    
    header_cus_id = fields.Many2one('account.invoice.reconciliation', string="Header Customer", ondelete='cascade')
    header_ven_id = fields.Many2one('account.invoice.reconciliation', string="Header Vendor", ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', string="Invoice", required=False)
    date_invoice = fields.Date(related='invoice_id.date_invoice', string='Entry Date', store=True, readonly=True)
#     currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', string='Currency', store=True, readonly=True)
#     amount_total_signed = fields.Monetary(string='Total', related='invoice_id.amount_total_signed', currency_field='currency_id', store=True, readonly=True)
#     residual_signed = fields.Monetary(string='Amount Due', related='invoice_id.residual_signed', currency_field='currency_id', store=True, readonly=True, )
#     allocated_amount = fields.Monetary(string='Allocated Amount', default=0.0, required=True, currency_field='currency_id')