# -*- coding: utf-8 -*-
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp

import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class ResCompany(models.Model):
    _inherit = "res.company"

    advance_employee_expense_id = fields.Many2one('account.account', string='Advance Employee Expense')

class HrExpenseInvoiceLine(models.Model):
    _name = "hr.expense.invoice.line"
    
    @api.one
    @api.depends('price_unit', 'quantity')
    def _compute_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
            
    product_id = fields.Many2one('product.product', string='Expense Item', domain=[('can_be_expensed', '=', True)], required=False)
    name = fields.Char(string="Name")
    invoice_id = fields.Many2one('hr.expense.invoice', 'Invoice' ,ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account',
        required=True, domain=[('deprecated', '=', False),('type', '!=', 'view')])
    price_unit = fields.Float(string='Unit Price', required=True)
    price_subtotal = fields.Float(string='Untaxed Amount', store=True, readonly=True, compute='_compute_subtotal')
    quantity = fields.Float(required=True, default=1)
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            self.account_id = False
        else:
            account = self.product_id.product_tmpl_id._get_product_accounts()['expense']
            if not account:
                raise UserError(_("No Expense account found for the product %s (or for it's category), please configure one.") % (self.product_id.name))
            if account:
                self.account_id = account.id
    
class HrExpenseInvoice(models.Model):
    _name = "hr.expense.invoice"
    
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
            
    @api.one
    @api.depends('move_id')
    def _get_move_check(self):
        self.move_check = bool(self.move_id)
        
    expense_id = fields.Many2one('hr.expense', 'Expense Line', ondelete='cascade')
    invoice_lines = fields.One2many('hr.expense.invoice.line','invoice_id', 'invoice Line', copy=True)
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
    move_check = fields.Boolean(compute='_get_move_check', string='Posted', track_visibility='always', store=True, default=False, copy=False)

    partner_id = fields.Many2one('res.partner', 'Partner')
    tax_ids = fields.Many2many('account.tax', string='Taxes',
                               domain="[('type_tax_use','=', 'purchase'), '|', ('active', '=', False), ('active', '=', True)]")
    
    currency_id = fields.Many2one('res.currency', related='expense_id.currency_id', string='Currency', store=True)
    company_id = fields.Many2one('res.company', related='expense_id.company_id', string='Company', store=True,
                                 default=lambda self: self.env['res.company']._company_default_get('hr.expense.invoice'))
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=False,
        domain="[('type', 'in', ['general']), ('company_id', '=', company_id)]")
    
    asset_id = fields.Many2one('account.asset.asset', 'Asset')
    
    #THANH: Do not duplicate invoice (check Partner, Inv Number and Inv Date)
    def check_invoice_duplication(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids):
            where = 'WHERE api.line_id is not null'
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
            if invoice.expense_id.state != 'completed':
                invoice.copy()
                return
        raise UserError(_("Only duplicate data on draft state."))
    
class HrExpense(models.Model):
    _inherit = "hr.expense"
    
    @api.depends('request_type', 'unit_amount', 'invoice_lines', 'invoice_lines.amount')
    def _compute_amount(self):
        for expense in self:
            expense.total_amount = sum(line.amount for line in self.invoice_lines)
            expense.reimburse_amount = expense.unit_amount - expense.total_amount if expense.request_type == 'advance' else 0.0 
            
    #THANH: change total amount to be equal total invoice amount, add more field to record reimburse amount
    total_amount = fields.Monetary(string='Total', store=True, compute='_compute_amount')
    reimburse_amount = fields.Monetary(string='Reimburse Amount', store=True, compute='_compute_amount')
    reimburse_date = fields.Date(readonly=False, 
                                 states={'completed': [('readonly', True)]},  
                                 string="Reimburse Date")
    
    #THANH: change default journal to false
    journal_id = fields.Many2one('account.journal', string='Expense Journal', 
                                 states={'done': [('readonly', True)], 'completed': [('readonly', True)]}, 
                                 default=False, 
                                 help="The journal used when the expense is done.")
    #THANH: Change these unused fields to non required
    product_id = fields.Many2one('product.product', string='Product', required=False)
    product_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=False)
    unit_amount = fields.Float(string='Advance Amount', readonly=True, required=False, states={'draft': [('readonly', False)]})
    
    #THANH: add new state for advance paid
    state = fields.Selection([('draft', 'To Submit'),
                              ('submit', 'Submitted'),
                              ('approve', 'Approved'),
                              ('post', 'Waiting Payment'),
                              ('done', 'Paid'),
                              ('completed', 'Done'),
                              ('cancel', 'Refused')
                              ], string='Status', index=True, readonly=True, 
        track_visibility='onchange', copy=False, default='draft', required=True,
        help='When the expense request is created the status is \'To Submit\'.\n It is submitted by the employee and request is sent to manager, the status is \'Submitted\'.\
        \nIf the manager approve it, the status is \'Approved\'.\n If the accountant genrate the accounting entries for the expense request, the status is \'Waiting Payment\'.')


    #THANH: add new fields to manage advance
    request_type = fields.Selection([
            ('advance', 'Advance'),
            ('reimburse', 'Reimburse'),
            ], string='Request Type', default='advance', readonly=True, required=False, states={'draft': [('readonly', False)]})
    invoice_lines = fields.One2many('hr.expense.invoice','expense_id', 'invoice', copy=True)
    
    #THANH: new field for payment
    payment_method_id = fields.Many2one('account.journal', string='Payment Method',copy=False,
                                        readonly=True, required=False, states={'post': [('readonly', False)]},
                                        domain=[('type', 'in', ('bank', 'cash'))])
    payment_date = fields.Date(readonly=True, states={'post': [('readonly', False)]}, string="Payment Date")
    payment_id = fields.Many2one('account.payment', string='Payment Ref',copy=False,readonly=True)
    final_payment_id = fields.Many2one('account.payment', string='Final Payment',copy=False, readonly=True)
    
    @api.model
    def _default_currency_id(self):
        return self.env.user.company_id.second_currency_id or self.env.user.company_id.currency_id
    
    _defaults = {
        'currency_id': _default_currency_id
    }
    
    @api.multi
    def action_view_move_line(self):
        move_ids = []
        for inv in self.invoice_lines:
            for line in inv.move_id.line_ids:
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
    
    @api.multi
    def approve_expenses(self):
        #THANH: bypass state approved and move to state Waiting payment
        self.write({'state': 'post'})
    
    
    
    def generate_expense_move(self):
        """
        THANH: New function: generate account move for each Invoice line (Other expenses or incomes) in Payment
        """
        company_currency = self.journal_id.company_id.currency_id.id
        current_currency = self.currency_id.id or company_currency
        if not self.company_id.advance_employee_expense_id.id:
            raise
        account_id = self.company_id.advance_employee_expense_id.id
        
        local_context = dict(self._context, force_company=self.company_id.id)
        ctx = local_context.copy()
        
        for invoice in self.invoice_lines:
            if invoice.journal_id.sequence_id:
                if not invoice.journal_id.sequence_id.active:
                    raise UserError(_('Please activate the sequence of selected journal (%s)!')%(invoice.journal_id.name))
                name = invoice.journal_id.sequence_id.with_context(ir_sequence_date=self.payment_date).next_by_id()
            else:
                raise UserError(_('Please define a sequence on the journal (%s)!')%(invoice.journal_id.name))
            
            ctx['date'] = invoice.date
            ctx['check_move_validity'] = False
            
            ref = self.name
            if invoice.reference or invoice.number:
                ref += ' - ' + (invoice.reference and (invoice.reference + '/') or '') + (invoice.number or '') 
            move_vals = {
                            'name': name,
                            'journal_id': invoice.journal_id.id,
                            'narration': invoice.narration or False,
                            'date': self.payment_date,
                            'doc_date': invoice.date or self.payment_date,
                            'ref': ref,
                            'asset_id': invoice.asset_id and invoice.asset_id.id or False,
                        }
            move = self.env['account.move'].create(move_vals)
            first_line_name = ''
           
            
            #Kiet: Sum đối ứng 
            total_dk = 0.0
            for line in invoice.invoice_lines:
                first_line_name += _(invoice.number) + ', '
                #Move Line for Invoice Details
                convert_price_subtotal = self.with_context(ctx).currency_id.compute(line.price_subtotal, self.company_id.currency_id)
                debit, credit, amount_currency = 0.0, 0.0, abs(line.price_subtotal)
                sign = 1
                debit = abs(convert_price_subtotal)
                if convert_price_subtotal < 0:
                    debit = 0.0
                    credit = abs(convert_price_subtotal)
                    sign = -1
                        
                total_dk += convert_price_subtotal
                move_line = {
                    'journal_id': invoice.journal_id.id,
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
                debit = abs(convert_tax_amount)
                if convert_tax_amount < 0:
                    debit = 0.0
                    credit = abs(convert_tax_amount)
                    sign = -1
                total_dk += convert_tax_amount
                move_line = {
                    'journal_id': invoice.journal_id.id,
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
                'journal_id': invoice.journal_id.id,
                'partner_id': invoice.partner_id and invoice.partner_id.id or False,
                'date': self.payment_date,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': sign * amount_currency if company_currency != current_currency else 0.0,
            }
            self.env['account.move.line'].with_context(ctx).create(move_line)
            
            move.write(move_vals)
            move.post()
            invoice.write({'move_id': move.id, 'journal_id': invoice.journal_id.id})
    
    
    
    @api.multi
    def action_done(self):
        account_payment = self.env['account.payment']
        for expense in self:
            #Kiet: Tạo phiếu chi/ Thu Bút toán Final phần còn lại
            payment_methods = expense.payment_method_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            #kiet: 
            comp_expense_id = expense.company_id.advance_employee_expense_id.id
            if not expense.employee_id.address_home_id:
                raise
            if expense.employee_id.address_home_id.property_account_payable_id.id != comp_expense_id:
                expense.employee_id.address_home_id.property_account_payable_id = comp_expense_id
                
            if expense.reimburse_amount == 0:
                expense.write({'state': 'completed'})
            else:
                if expense.reimburse_amount < 0:
                    outbound = 'outbound'
                else:
                    outbound = 'inbound'
                    
            payment_vals = {'payment_type': outbound, 
                            'payment_method_id': payment_method_id.id, 
                            'partner_type': 'supplier',
                            'partner_id': expense.employee_id.address_home_id.id, 
                            'journal_id': expense.payment_method_id.id,
                            'communication': expense.name,
                            'payment_date': expense.payment_date,
                            'amount': abs(expense.reimburse_amount)
                            }
            payment = account_payment.create(payment_vals)
            expense.write({'final_payment_id': payment.id, 'state': 'completed'})
            payment.post()
            
            #Tạo bút toán hóa đơn Clear tài khoản 141
            
            self.generate_expense_move()
                
                
#             else:
#                 invoice_lines = []
#                 invoice_line_vals = {}
#                 for invoice in expense.invoice_lines:
#                     line ={}
#                     for i in invoice.invoice_lines:
#                         line = {'account_id': i.account_id.id,
#                                     'price_unit': i.price_unit,
#                                     'name': i.product_id.default_code}
#                         line = (0,0,line)
#                         invoice_lines.append(line)
#                         
#                     invoice_line_vals = {'partner_id': invoice.partner_id.id,
#                                         'journal_id': invoice.journal_id.id,
#                                         'currency_id': invoice.currency_id.id,
#                                         'reference': invoice.number,
#                                         'invoice_lines': invoice_lines}
# #                     invoice_lines.append(object)
#                 if invoice_line_vals:
#                     payment_vals.update({'show_invoice': True,
#                                          'invoice_journal_id': expense.journal_id.id,
#                                          'payment_lines': [(0,0,invoice_line_vals)],
#                                          'amount': expense.total_amount,
#                                          })
#                 else:
#                     payment_vals.update({'show_invoice': True,
#                                          'invoice_journal_id': expense.journal_id.id,
#                                          'amount': expense.total_amount,
#                                          })
 
#             payment = account_payment.create(payment_vals)
#             expense.write({'final_payment_id': payment.id, 'state': 'completed'})
#             payment.post()
        
    @api.multi
    def action_payment(self):
        
        account_payment = self.env['account.payment']
        
        for expense in self:
            comp_expense_id = expense.company_id.advance_employee_expense_id.id
            if not expense.employee_id.address_home_id:
                raise
            if expense.employee_id.address_home_id.property_account_payable_id.id != comp_expense_id:
                expense.employee_id.address_home_id.property_account_payable_id = comp_expense_id
            
            payment_methods = expense.payment_method_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            
            payment_vals = {'payment_type': 'outbound', 
                            'payment_method_id': payment_method_id.id, 
                            'partner_type': 'supplier',
                            'partner_id': expense.employee_id.address_home_id.id, 
                            'journal_id': expense.payment_method_id.id,
                            'communication': expense.name,
                            'payment_date': expense.payment_date,
            }
            
            if expense.request_type == 'reimburse':
                if not expense.invoice_lines:
                    raise UserError(_("You must input invoices or bills before making payment."))
                payment_vals.update({'amount': expense.unit_amount})
            
            else:
                invoice_lines = []
                invoice_line_vals = {}
                for invoice in expense.invoice_lines:
                    line ={}
                    for i in invoice.invoice_lines:
                        line = {'account_id': i.account_id.id,
                                    'price_unit': i.price_unit,
                                    'name': i.product_id.default_code}
                        line = (0,0,line)
                        invoice_lines.append(line)
                        
#                     invoice_line_vals = {'partner_id': invoice.partner_id.id,
#                                         'journal_id': invoice.journal_id.id,
#                                         'currency_id': invoice.currency_id.id,
#                                         'reference': invoice.number,
#                                         'invoice_lines': invoice_lines}
#                     invoice_lines.append(object)
                if invoice_line_vals:
                    payment_vals.update({'show_invoice': False,
                                         'invoice_journal_id': expense.journal_id.id,
                                         'payment_lines': [(0,0,invoice_line_vals)],
                                         'amount': expense.unit_amount,
                                         })
                else:
                    payment_vals.update({'show_invoice': False,
                                         'invoice_journal_id': expense.journal_id.id,
                                         'amount': expense.unit_amount,
                                         })

            if expense.payment_id:
                expense.payment_id.payment_lines.unlink()
                expense.payment_id.write(payment_vals)
                payment = expense.payment_id
            else:
                payment = account_payment.create(payment_vals)
            expense.write({'payment_id': payment.id, 'state': 'done'})
            payment.post()
            
            
        
        
        
        