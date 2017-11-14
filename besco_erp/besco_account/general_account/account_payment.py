# -*- coding: utf-8 -*-
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

import time
from datetime import datetime
import copy
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountPaymentInvoiceLine(models.Model):
    _name = "account.payment.invoice.line"
    
    @api.one
    @api.depends('price_unit', 'quantity')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
            
    name = fields.Text(string='Description', required=True)
    invoice_id = fields.Many2one('account.payment.invoice', 'Invoice' ,ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('deprecated', '=', False),('type', '!=', 'view')])
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Untaxed Amount', store=True, readonly=True, compute='_compute_subtotal')
    quantity = fields.Float(required=True, default=1)
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
#     tax_ids = fields.Many2many('account.tax', string='Tax', help="Only for tax excluded from price")

class AccountPaymentInvoice(models.Model):
    _name = "account.payment.invoice"
    
    @api.multi
    @api.depends('invoice_lines','tax_correction', 'tax_ids', 'currency_id', 'invoice_lines.price_subtotal')
    def _compute_total(self):
        for invoice in self:
            subtotal = 0
            tax_amount = 0
            for line in invoice.invoice_lines:
                subtotal += line.price_unit * line.quantity
            
            tax_info = invoice.tax_ids.compute_all(subtotal, invoice.currency_id, 1,  invoice.partner_id)
            invoice.sub_total = subtotal
            tax_amount += sum([t.get('amount',0.0) for t in tax_info.get('taxes', False)])             
            invoice.tax_amount = tax_info['total_included'] - tax_info['total_excluded']
            if invoice.tax_correction:
                invoice.amount = tax_info['total_excluded'] + invoice.tax_correction
            else:
                invoice.amount = tax_info['total_included']
    
#     @api.depends('invoice_lines', 'invoice_lines.account_id', 'tax_ids')
    def _get_accounts(self):
        for invoice in self:
            accounts = ''
            for line in invoice.invoice_lines:
                accounts += line.account_id.code + ', '
            for tax in invoice.tax_ids:
                accounts += tax.account_id and tax.account_id.code + ', ' or ''
            if len(accounts):
                accounts = accounts[0:-2]
            invoice.accounts = accounts
            
    @api.model
    def _default_journal(self):
        journal_id = self._context.get('default_journal_id', False)
        if not journal_id:
            raise UserError(_("You must select Journal Firstly before adding a new Invoice."))
        return journal_id
    
    @api.one
    @api.depends('move_id')
    def _get_move_check(self):
        self.move_check = bool(self.move_id)
        
    line_id = fields.Many2one('account.payment', 'Payment Line', ondelete='cascade')
    invoice_lines = fields.One2many('account.payment.invoice.line','invoice_id', 'invoice Line', copy=True)
    number = fields.Char("Invoice Number", copy=False)
    reference = fields.Char('Invoice Reference', copy=True)
    date = fields.Date(string="Invoice Date", copy=False, default=fields.Date.context_today)
    narration = fields.Text('Notes', required=False)
    
    amount = fields.Monetary(string='Total', compute='_compute_total', currency_field='currency_id', store=True, readonly=True)
    sub_total = fields.Monetary(string='Untaxed Total', compute='_compute_total', currency_field='currency_id', store=True, readonly=True)
    tax_amount = fields.Monetary(string='Tax Amount', compute='_compute_total', currency_field='currency_id', store=True, readonly=True)
    tax_correction = fields.Monetary(string="Tax Correction", currency_field='currency_id')
    
    accounts = fields.Char(string='Accounts', compute='_get_accounts', store=False, readonly=True)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    #THANH: this field will be used to hide button duplicate on tree view (can not use field move_id because odoo not support on xml to check available)
    move_check = fields.Boolean(compute='_get_move_check', string='Posted', track_visibility='always', store=True, default=False, copy=False)

    partner_id = fields.Many2one('res.partner', 'Partner')
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain="[('type_tax_use','=', {'inbound': 'sale', 'outbound': 'purchase'}.get(context.get('payment_type', ''), '')), '|', ('active', '=', False), ('active', '=', True)]")
    
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id', string='Currency', store=True)
    company_id = fields.Many2one('res.company', related='line_id.company_id', string='Company', store=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.payment.invoice'))
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, default=_default_journal, 
        domain="[('type', 'in', ['general']), ('company_id', '=', company_id)]")
    
    #THANH: Used to link asset
    asset_id = fields.Many2one('account.asset.asset', 'Asset')
    
    #THANH: Do not duplicate invoice (check Partner, Inv Number and Inv Date)
    def check_invoice_duplication(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids):
            where = 'WHERE api.id != %s and api.line_id is not null'%(line.id)
            if line.partner_id:
                where += ' AND api.partner_id = %s'%(line.partner_id.id)
            if line.date:
                where += " AND api.date = '%s'"%(line.date)
            if line.reference:
                where += " AND api.reference = '%s'"%(line.reference)
            if line.number:
                where += " AND api.number = '%s'"%(line.number)
                sql = "SELECT api.number, api.reference FROM account_payment_invoice api " + where
                cr.execute(sql)
                res = cr.fetchall()
                if len(res) > 0:
                    number = res[0][0] or ''
                    reference = res[0][1] or ''
                    raise UserError(_("Invoice Number (%s) already exist in payment '%s'") % (number + reference, line.line_id.name))
        return True
    
    _constraints = [(check_invoice_duplication, '', [])]
    
    @api.multi
    def duplicate(self):
        for invoice in self:
            if invoice.line_id.state == 'draft':
                invoice.copy()
                invoice.line_id._onchange_payment_lines()
                return
        raise UserError(_("Only duplicate data on draft state."))
        
class account_register_payments(models.TransientModel):
    _inherit = "account.register.payments"
    
    #THANH: add partner_bank
    partner_bank_id = fields.Many2one('res.partner.bank', 'Partner Bank')
    responsible = fields.Char(string='Responsible')
    
    def get_payment_vals(self):
        """ Hook for extension """
        #THANH: check partner bank
        if self.payment_type in ['outbound'] and self.journal_id.type == 'bank' and not self.partner_bank_id:
            raise UserError(_("Please define Bank for Partner '%s' !")%(_(self.partner_id.name)))
        
        return {
            'journal_id': self.journal_id.id,
            'payment_method_id': self.payment_method_id.id,
            'payment_date': self.payment_date,
            'communication': self.communication,
            'invoice_ids': [(4, inv.id, None) for inv in self._get_invoices()],
            'payment_type': self.payment_type,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_type': self.partner_type,
            
            #THANH: add partner bank
            'partner_bank_id': self.partner_bank_id and self.partner_bank_id.id or False,
        }
        
class AccountPayment(models.Model):
    _inherit = "account.payment"    
    
    @api.one
    @api.depends('payment_fee_lines.amount', 'amount', 'currency_id', 'company_id')
    def _compute_total_payment(self):
        self.total_payment = sum(line.amount for line in self.payment_fee_lines) + self.amount
        
    source_document = fields.Char(string='Source Document', copy=False)
    extend_payment = fields.Selection([
        ('payment', 'Payment'),
        ('advance', 'Advance'),
    ],  default='payment', string='Payment Mode', readonly=True, states={'draft': [('readonly', False)]})
    
    #THANH: Show expenses invoices
    show_invoice = fields.Boolean(string="Show Invoice", default=False, readonly=True, states={'draft': [('readonly', False)]})
    has_fee = fields.Boolean(string="Has Fees", default=False, readonly=True, states={'draft': [('readonly', False)]})
    
    invoice_journal_id = fields.Many2one('account.journal', string='Journal', 
        domain="[('type', 'in', ['general']), ('company_id', '=', company_id)]",
        readonly=True, states={'draft': [('readonly', False)]})
    other_payment_number = fields.Char(string='Other Number')#This field used to print payment pdf
    responsible = fields.Char(string='Responsible')
    
    payment_lines = fields.One2many('account.payment.invoice','line_id', string='Invoice Lines', readonly=True, copy=True, states={'draft': [('readonly', False)]})
    partner_bank_id = fields.Many2one('res.partner.bank', 'Partner Bank', readonly=True, default=False, states={'draft': [('readonly', False)]})
    
    payment_fee_lines = fields.One2many('account.payment.fee','payment_id', string='Fee Lines', readonly=True, copy=True, states={'draft': [('readonly', False)]})
    
    #THANH: Total payment (include fee)
    total_payment = fields.Monetary(string='Total Payment (Inc. Fees)', store=True, readonly=True, compute='_compute_total_payment')
    
    
    @api.multi
    def action_view_invoice_move_line(self):
        #THANH: View Invoice Move Lines
        move_ids = []
        for inv in self.payment_lines:
            for line in inv.move_id.line_ids:
                move_ids.append(line.id)
        for line in self.move_line_ids:
            move_ids.append(line.id)
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }
    
    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            #THANH: No need to raise this error
#             if not self.company_id.transfer_account_id.id:
#                 raise UserError(_('Transfer account not defined on the company.'))
            #THANH: get account from destination journal account
            self.destination_account_id = self.destination_journal_id.default_debit_account_id.id or self.destination_journal_id.default_credit_account_id.id
            #self.company_id.transfer_account_id.id
        elif self.partner_id:
            #THANH: When this is advance payment will get other account in partner
            if self.partner_type == 'customer':
                if self.extend_payment == 'payment':
                    self.destination_account_id = self.partner_id.property_account_receivable_id.id
                else:
                    self.destination_account_id = self.partner_id.property_customer_advance_acc_id.id
            else:
                if self.extend_payment == 'payment':
                    self.destination_account_id = self.partner_id.property_account_payable_id.id
                else:
                    self.destination_account_id = self.partner_id.property_vendor_advance_acc_id.id
                
    #THANH: Show Invoices Number
    @api.one
    @api.depends('invoice_ids.state', 'show_invoice', 'payment_lines')
    def _get_invoice_number(self):
        res = ''
        if len(self.invoice_ids):
            for inv in self.invoice_ids:
                if inv.state not in ['draft', 'cancel'] and inv.reference:
                    res += inv.reference + ', '
        if len(self.payment_lines) and self.show_invoice:
            for inv in self.payment_lines:
                if inv.number:
                    res += inv.number + ', '
        if len(res):
            self.invoice_reference = res[:-2]
            
    invoice_reference = fields.Char(compute='_get_invoice_number', string="Invoice Number", readonly=True, store=True)
    
    def _check_partner_bank_id(self, cr, uid, ids, context=None):
        for payment in self.browse(cr, uid, ids):
            #THANH: Check partner_bank_id
            if payment.payment_type in ['outbound'] and payment.journal_id.type == 'bank' and not payment.partner_bank_id:
                raise UserError(_("Please define Bank for Partner '%s' !")%(payment.partner_id.name))
        return True
    
    #_constraints = [(_check_partner_bank_id, '', [])]
    
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        res = super(AccountPayment, self)._onchange_payment_type()
        if self.payment_type == 'transfer':
            self.show_invoice = False
        return res
        
    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        #THANH: Dont check when show invoices
        if not self.show_invoice and not self.amount > 0.0:
            raise ValidationError(_('The payment amount must be strictly positive.'))
    
    @api.onchange('payment_lines')
    def _onchange_payment_lines(self):
        #THANH: Auto compute payment amount
        if self.show_invoice:
            self.amount = 0.0
            for line in self.payment_lines:
                self.amount += line.amount
    
    @api.onchange('amount')
    def _onchange_amount(self):
        if self.invoice_ids:
            invoice = self.invoice_ids[0]
            invoice_currency = invoice.currency_id
            payment_currency = self.currency_id or self.journal_id.currency_id or self.journal_id.company_id.currency_id
            amount_currency = invoice_currency.with_context(date=self.payment_date).compute(invoice.residual, payment_currency)
            if self.amount > amount_currency:
                #THANH: auto select this option to create Advance Payment
                self.payment_difference_handling = 'reconcile'
                self.writeoff_account_id = invoice.account_id.id
            else:
                self.payment_difference_handling = 'open'
            
    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            #THANH: Add thanh toan to clear entry for VAS report purpose
            rec['communication'] = _('Thanh toán hóa đơn số ') + (invoice['reference'] or invoice['name'] or invoice['number'])
            if invoice['partner_id'] and invoice['partner_id'][1]:
                rec['communication'] += _(' của ') + _(invoice['partner_id'][1])
        return rec
         
    @api.model
    def create(self, vals):
        #THANH: default / to auto get sequence
        vals['name'] = '/'
        return super(AccountPayment,self).create(vals)
    
    def _get_liquidity_move_line_vals(self, amount):
        name = self.name
        if self.payment_type == 'transfer':
            #THANH: Trsnlate name into VN
            name = self.communication#_('Transfer to %s') % self.destination_journal_id.name
                
        vals = {
            'name': name,
            'account_id': self.payment_type in ('outbound','transfer') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id,
            'payment_id': self.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
        }

        # If the journal has a currency specified, the journal item need to be expressed in this currency
        if self.journal_id.currency_id and self.currency_id != self.journal_id.currency_id:
            amount = self.currency_id.with_context(date=self.payment_date).compute(amount, self.journal_id.currency_id)
            debit, credit, amount_currency, dummy = self.env['account.move.line'].with_context(date=self.payment_date).compute_amount_fields(amount, self.journal_id.currency_id, self.company_id.currency_id)
            vals.update({
                'amount_currency': amount_currency,
                'currency_id': self.journal_id.currency_id.id,
            })

        return vals
    
    #THANH: Khi thanh toán thì tham chiếu thanh toán cho Hóa đơn nào (thay vì journal sequence)
    def _get_counterpart_move_line_vals(self, invoice=False):
        if self.payment_type == 'transfer':
            #THANH: get from ly do
            name = self.communication
        else:
            name = ''
#             if self.partner_type == 'customer':
#                 if self.payment_type == 'inbound':
#                     name += _("Customer Payment")
#                 elif self.payment_type == 'outbound':
#                     name += _("Customer Refund")
#             elif self.partner_type == 'supplier':
#                 if self.payment_type == 'inbound':
#                     name += _("Vendor Refund")
#                 elif self.payment_type == 'outbound':
#                     name += _("Vendor Payment")

            #THANH: Translate into VN
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    if self.extend_payment == 'payment':
                        name += _("Khách hàng thanh toán")
                    else:
                        name += _("Khách hàng ứng tiền")
                elif self.payment_type == 'outbound':
                    name += _("Hoàn tiền cho khách hàng")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name += _("Nhà cung cấp trả tiền")
                elif self.payment_type == 'outbound':
                    if self.extend_payment == 'payment':
                        name += _("Thanh toán tiền cho nhà cung cấp")
                    else:
                        name += _("Ứng tiền nhà cung cấp")
                    
            if invoice:
                name += ': '
                for inv in invoice:
                    if inv.move_id and inv.reference:
                        #THANH name + invoice number not sequence
                        name += _("HĐ ") + inv.reference + _(', ')
                name = name[:len(name)-2]
                
        return {
            'name': name,
            'account_id': self.destination_account_id.id,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False,
            'payment_id': self.id,
        }
        
    @api.multi
    def generate_expense_move(self):
        """
        THANH: New function: generate account move for each Invoice line (Other expenses or incomes) in Payment
        """
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id or company_currency
        account_id = self.payment_type in ('outbound') and self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
        
        local_context = dict(self._context, force_company=self.journal_id.company_id.id)
        ctx = local_context.copy()
        
        for invoice in self.payment_lines:
            invoice_journal_id = invoice.journal_id or self.invoice_journal_id
            if invoice_journal_id.sequence_id:
                if not invoice_journal_id.sequence_id.active:
                    raise UserError(_('Please activate the sequence of selected journal (%s)!')%(invoice_journal_id.name))
                name = invoice_journal_id.sequence_id.with_context(ir_sequence_date=self.payment_date).next_by_id()
            else:
                raise UserError(_('Please define a sequence on the journal (%s)!')%(invoice_journal_id.name))
            
            ctx['date'] = self.payment_date
            ctx['check_move_validity'] = False
            
            ref = self.name
            if invoice.reference or invoice.number:
                ref += ' - ' + (invoice.reference and (invoice.reference + '/') or '') + (invoice.number or '') 
            narration = invoice.narration or ''
            if self.communication:
                narration += " (" + self.communication + ")"
            move_vals = {
                            'name': name,
                            'journal_id': invoice_journal_id.id,
                            'narration': narration,
                            'date': self.payment_date,
                            'doc_date': invoice.date or self.payment_date,
                            'ref': ref,
                            
                            'asset_id': invoice.asset_id and invoice.asset_id.id or False,
                        }
            move = self.env['account.move'].create(move_vals)
            first_line_name = ''
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    first_line_name += _("Thu tiền")
                if self.payment_type == 'outbound':
                    first_line_name += _("Thanh toán")
            if self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    first_line_name += _("Thu tiền")
                if self.payment_type == 'outbound':
                    first_line_name += _("Thanh toán")
            if len(first_line_name):
                first_line_name += ': '
            
            #Kiet: Sum đối ứng 
            total_dk = 0.0
            for line in invoice.invoice_lines:
                first_line_name += _(line.name) + ', '
                #Move Line for Invoice Details
                convert_price_subtotal = self.with_context(ctx).currency_id.compute(line.price_subtotal, self.company_id.currency_id)
                debit, credit, amount_currency = 0.0, 0.0, abs(line.price_subtotal)
                sign = 1
                if self.payment_type == 'outbound':
                    debit = abs(convert_price_subtotal)
                    if convert_price_subtotal < 0:
                        debit = 0.0
                        credit = abs(convert_price_subtotal)
                        sign = -1
                else:
                    credit = abs(convert_price_subtotal)
                    sign = -1
                    if convert_price_subtotal < 0:
                        debit = abs(convert_price_subtotal)
                        credit = 0.0
                        sign = 1
                        
                total_dk += convert_price_subtotal
                move_line = {
                    'journal_id': invoice_journal_id.id,
                    'name': line.name or '/',
                    'account_id': line.account_id.id,
                    'move_id': move.id,
                    'partner_id': invoice.partner_id and invoice.partner_id.id or False,
                    'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                    'quantity': line.quantity,
                    'debit': debit,
                    'credit': credit,
                    'date': self.payment_date,
                    
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': sign * amount_currency if current_currency != company_currency else 0.0,
                }
                self.env['account.move.line'].with_context(ctx).create(move_line)
                
            #THANH: remove ': ' or ', ' in first_line_name
            first_line_name = first_line_name[:-2]
            
            #THANH; Update Invoice Naration if it is null
            if not invoice.narration or not len(invoice.narration):
                invoice.write({'narration': first_line_name})
            
            #THANH: Tax lines
            if len(invoice.tax_ids):
                tax_account_id = False
                tax_name = ''
                for t in invoice.tax_ids:
                    tax_name += t.name
                    tax_account_id = t.account_id and t.account_id.id or False
                
                if not tax_account_id and len(tax_name):
                    raise UserError(_('Please define a Tax Account in Tax (%s).')%(tax_name))
                
                convert_tax_amount = self.with_context(ctx).currency_id.compute(invoice.tax_correction or invoice.tax_amount, self.company_id.currency_id)
                debit, credit, amount_currency = 0.0, 0.0, abs(invoice.tax_correction or invoice.tax_amount)
                sign = 1
                if self.payment_type == 'outbound':
                    debit = abs(convert_tax_amount)
                    if convert_tax_amount < 0:
                        debit = 0.0
                        credit = abs(convert_tax_amount)
                        sign = -1
                else:
                    credit = abs(convert_tax_amount)
                    sign = -1
                    if convert_tax_amount < 0:
                        debit = abs(convert_tax_amount)
                        credit = 0.0
                        sign = 1
                total_dk += convert_tax_amount
                move_line = {
                    'journal_id': invoice_journal_id.id,
                    'name': tax_name,
                    'account_id': tax_account_id,
                    'move_id': move.id,
                    'partner_id': invoice.partner_id and invoice.partner_id.id or False,
                    'debit': debit,
                    'credit': credit,
                    'date': self.payment_date,
                    
                    'currency_id': company_currency != current_currency and current_currency or False,
                    'amount_currency': sign * amount_currency if current_currency != company_currency else 0.0,
                }
                self.env['account.move.line'].with_context(ctx).create(move_line)
                
            #First line
            debit, credit, amount_currency = 0.0, 0.0, abs(invoice.amount)
            sign = 1
            if self.payment_type == 'inbound':
                debit = abs(total_dk)
                if total_dk < 0:
                    debit = 0.0
                    credit = abs(total_dk)
                    sign = -1
            else:
                credit = abs(total_dk)
                sign = -1
                if total_dk < 0:
                    debit = abs(total_dk)
                    credit = 0.0
                    sign = 1
            move_line = {
                'name': first_line_name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': account_id,
                'move_id': move.id,
                'journal_id': invoice_journal_id.id,
                'partner_id': invoice.partner_id and invoice.partner_id.id or False,
                'date': self.payment_date,
                
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': sign * amount_currency if company_currency != current_currency else 0.0,
            }
            self.env['account.move.line'].with_context(ctx).create(move_line)
            
            move.write(move_vals)
            move.post()
            invoice.write({'move_id': move.id, 'journal_id': invoice_journal_id.id})
    
    @api.multi
    def generate_payment_fee(self):
        """
        THANH: New function: generate account move for Bank Fee
        """
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id or company_currency
        account_id = self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
        local_context = dict(self._context, force_company=self.journal_id.company_id.id)
        ctx = local_context.copy()
        ctx['date'] = self.payment_date
        ctx['check_move_validity'] = False
        
        for fee in self.payment_fee_lines:
            if fee.journal_id.sequence_id:
                if not fee.journal_id.sequence_id.active:
                    raise UserError(_('Please activate the sequence of selected journal (%s)!')%(fee.journal_id.name))
                name = fee.journal_id.sequence_id.with_context(ir_sequence_date=self.payment_date).next_by_id()
            else:
                raise UserError(_('Please define a sequence on the journal (%s)!')%(fee.journal_id.name))
            move_vals = {
                            'name': name,
                            'journal_id': fee.journal_id.id,
                            'narration': fee.description,
                            'date': self.payment_date,
                            'doc_date': self.payment_date,
                            'ref': self.name,
                        }
            move = self.env['account.move'].create(move_vals)
            #Hach toan chi phi
            convert_fee_amount = self.currency_id.compute(fee.amount, self.company_id.currency_id)
            move_line = {
                'journal_id': fee.journal_id.id,
                'name': fee.description,
                'account_id': fee.account_id.id,
                'move_id': move.id,
                'partner_id': self.partner_id.id,
                'debit': convert_fee_amount,
                'credit': 0.0,
                'date': self.payment_date,
                'payment_id': self.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': fee.amount if current_currency != company_currency else 0.0,
            }
            self.env['account.move.line'].with_context(ctx).create(move_line)
            
            #Hach toan cash or bank
            move_line = {
                'journal_id': fee.journal_id.id,
                'name': fee.description,
                'account_id': account_id,
                'move_id': move.id,
                'partner_id': self.partner_id.id,
                'debit': 0.0,
                'credit': convert_fee_amount,
                'date': self.payment_date,
                'payment_id': self.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': (-1) * fee.amount if current_currency != company_currency else 0.0,
            }
            self.env['account.move.line'].with_context(ctx).create(move_line)
            move.post()
            fee.write({'move_id': move.id})
               
    @api.multi
    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconciliable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconciliable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        for rec in self:
            #THANH: Check these conditions before posting entry
            if rec.amount <= 0.0:
                raise UserError(_("Payment Amount must be bigger than zero."))
            
            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted. Trying to post a payment in state %s.") % rec.state)

            if any(inv.state != 'open' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # Use the right sequence to set the name
            #THANH: Move sequence to create event
            if rec.name =='/':
                journal = rec.journal_id
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.payment_type == 'inbound':
                        if journal.type == 'bank':
                            sequence_code = 'receive.money.bank'
                        else:
                            sequence_code = 'receive.money.cash'
                    else:
                        if journal.type == 'bank':
                            sequence_code = 'send.money.bank'
                        else:
                            sequence_code = 'send.money.cash'
                 
                if not rec.payment_date:
                    rec.payment_date =time.strftime(DATE_FORMAT)
                rec.name = self.env['ir.sequence'].with_context(ir_sequence_date=rec.payment_date).next_by_code(sequence_code)
            
            #THANH: Generate Payment Fees Entry (like Bank, Internal fee)
            if len(rec.payment_fee_lines):
                self.generate_payment_fee()
                
            #THANH: If payment for expenses invoices => move to customized work-flow. Otherwise, works as original source
            if rec.show_invoice:
                self.generate_expense_move()
                rec.state = 'posted'
                return True
            else:
                self.invoice_journal_id = False
            #THANH: If payment for expenses invoices => move to customized work-flow. Otherwise, works as original source
            
            # Create the journal entry
            amount = rec.amount * (rec.payment_type in ('outbound', 'transfer') and 1 or -1)
            move = rec._create_payment_entry(amount)
            
            # In case of a transfer, the first journal entry created debited the source liquidity account and credited
            # the transfer account. Now we debit the transfer account and credit the destination liquidity account.
            #THANH: No need to reconcile
#             if rec.payment_type == 'transfer':
#                 transfer_credit_aml = move.line_ids.filtered(lambda r: r.account_id == rec.company_id.transfer_account_id)
#                 transfer_debit_aml = rec._create_transfer_entry(amount)
#                 (transfer_credit_aml + transfer_debit_aml).reconcile()

            rec.state = 'posted'
    
    def _get_move_vals(self, journal=None):
        """ Return dict to create the payment move
        """
        journal = journal or self.journal_id
        if not journal.sequence_id:
            raise UserError(_('Configuration Error !'), _('The journal %s does not have a sequence, please specify one.') % journal.name)
        if not journal.sequence_id.active:
            raise UserError(_('Configuration Error !'), _('The sequence of journal %s is deactivated.') % journal.name)
        name = journal.with_context(ir_sequence_date=self.payment_date).sequence_id.next_by_id()
        return {
            'name': name,
            'date': self.payment_date,
            
            #THANH: join so phieu chi + memo
#             'ref': self.communication or '',
            'ref': self.name,
            'narration': self.communication or '',
            #THANH: join so phieu chi + memo
            
            'company_id': self.company_id.id,
            'journal_id': journal.id,
        }
        
    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        invoice_currency = False
        if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
            #if all the invoices selected share the same currency, record the paiement in that currency too
            invoice_currency = self.invoice_ids[0].currency_id
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount, self.currency_id, self.company_id.currency_id, invoice_currency)

        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
            debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(self.payment_difference, self.currency_id, self.company_id.currency_id, invoice_currency)
#             writeoff_line['name'] = _('Counterpart')
            
            #THANH: sua lai thanh ung tien
            name = _('Thanh toán thừa')
            if self.partner_type == 'customer':
                if self.payment_type == 'inbound':
                    name = _("Khách hàng thanh toán")
                elif self.payment_type == 'outbound':
                    name = _("Hoàn tiền khách hàng")
            elif self.partner_type == 'supplier':
                if self.payment_type == 'inbound':
                    name = _("Nhà cung cấp trả tiền")
                elif self.payment_type == 'outbound':
                    name = _("Ứng tiền nhà cung cấp")
            writeoff_line['name'] = name
            writeoff_line['extend_payment'] = 'advance'
            #THANH: sua lai thanh ung tien
                    
            writeoff_line['account_id'] = self.writeoff_account_id.id
            writeoff_line['debit'] = debit_wo
            writeoff_line['credit'] = credit_wo
            writeoff_line['amount_currency'] = amount_currency_wo
            writeoff_line['currency_id'] = currency_id
            writeoff_line = aml_obj.create(writeoff_line)
            if counterpart_aml['debit']:
                counterpart_aml['debit'] += credit_wo - debit_wo
            if counterpart_aml['credit']:
                counterpart_aml['credit'] += debit_wo - credit_wo
            counterpart_aml['amount_currency'] -= amount_currency_wo
        
        #THANH check invoice_ids is exist will go to this function register_payment
#         self.invoice_ids.register_payment(counterpart_aml)
        if len(self.invoice_ids):
            self.invoice_ids.register_payment(counterpart_aml)

        #Write counterpart lines
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml_obj.create(liquidity_aml_dict)
        
        #THANH: Update payment or advance for move
        move.extend_payment = self.extend_payment
        #THANH: Update payment or advance for move
            
        move.post()
        return move
    
    @api.multi
    def cancel(self):
        for rec in self:
            #THANH: Generate sequence at 
#             sequence_his = self.env['ir.sequence.his'].search([('generate_code','=',rec.name)])
#             if sequence_his:
#                 number =0.0
#                 sql ='''
#                     SELECT max(id) from ir_sequence_his where seq_id = %s
#                 '''%(sequence_his.seq_id.id)
#                 self.env.cr.execute(sql)
#                 res = self.env.cr.fetchall()
#                 if len(res) > 0:
#                     number = res[0][0] or ''
#                 if number == sequence_his.id:
#                     sequence_his.unlink()
#                     rec.name ='/'
            
            
            #THANH:check show invoice, cancel move by each invoice
            #THANH: context force_cancel to pass check from account move
            if rec.show_invoice:
                for invoice in rec.payment_lines:
                    invoice.move_id.with_context(payment_force_cancel=True).button_cancel()
                    invoice.move_id.unlink()
            #THANH:check show invoice, cancel move by each invoice
            
            for move in rec.move_line_ids.mapped('move_id'):
                if rec.invoice_ids:
                    move.line_ids.remove_move_reconcile()
                move.with_context(payment_force_cancel=True).button_cancel()
                move.unlink()
            rec.state = 'draft'

class AccountPaymentFee(models.Model):
    _name = "account.payment.fee"
    
    payment_id = fields.Many2one('account.payment', 'Payment ID', ondelete='cascade', copy=True)
    
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    description = fields.Text('Description', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True)
    account_id = fields.Many2one('account.account', string="Fee Account", domain="[('type','=','other'),('deprecated', '=', False)]" , required=True)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', string='Currency', store=True)
    company_id = fields.Many2one('res.company', related='payment_id.company_id', string='Company', store=True)
    
