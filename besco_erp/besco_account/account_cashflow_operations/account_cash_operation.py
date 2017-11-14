# -*- encoding: utf-8 -*-
import  time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools import float_is_zero, float_compare
DATE_FORMAT = "%Y-%m-%d"

def _lang_get(self, cr, uid, context={}):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [], context=context)
    res = obj.read(cr, uid, ids, ['code', 'name'], context)
    return [(r['code'], r['name']) for r in res] + [('','')]


class AccountCashOperation(models.Model):
    _name= 'account.cash.operation'
    _description= 'Object to store Cash Operation Demands'
    _order = 'id desc, date_start desc'

    @api.model
    def _get_type(self):
        return self._context.get('type', 'loan')

    @api.model
    def _default_account(self):
        return self.env['account.account'].search([('type','=','liquidity')], limit=1)
    
    @api.one
    @api.depends('amount_main', 'rate', 'day_count_basis')
    def _compute_rate_per_day(self):
        self.rate_per_day = self.amount_main * (self.rate/100) / float(self.day_count_basis)
        
    # general fields
    partner_id = fields.Many2one('res.partner', string='Partner', change_default=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
    partner_bank_id = fields.Many2one('res.partner.bank', 'Partner Bank')
    
    payment_method_id = fields.Many2one('account.journal', string='Default Payment Method', domain="[('type','in',('cash','bank'))]", 
        required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    account_id = fields.Many2one('account.account', string='Demand Account',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        domain="[('deprecated', '=', False), ('type', '!=', 'view')]")
    account_recognition_id = fields.Many2one('account.account', string='Account Recognition',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]},
        domain="[('deprecated', '=', False), ('type', '!=', 'view')]")
    
    description = fields.Char(string='Description', required=False, readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Document Number', required=True, readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
        ('loan','Loan'),
        ('invest','Investment'),
    ], string='Type', help="Type is used to separate Loans and Investments.", default=_get_type)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),],          
        string='State', required=True, readonly=True, default='draft')
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 default=lambda self: self.env['res.company']._company_default_get('account.cash.operation'))
    
    # loan/invest demand fields
    date_start = fields.Date(string='Start Date', readonly=True, states={'draft': [('readonly', False)]})
    date_stop = fields.Date(string='Maturity Date', readonly=True, states={'draft': [('readonly', False)]})
    days = fields.Integer(string='Interest Days', required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    interest_payment = fields.Selection([
        ('pre', 'In Advance'),
        ('post', 'On Maturity Date')],            
        string='Interest Payment', default='post', required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                  default=lambda self: self.env.user.company_id.currency_id)
    journal_id = fields.Many2one('account.journal', string='Journal', domain="[('type','=','general')]", 
                                 required=True, readonly=True, states={'draft': [('readonly', False)]})
    payment_lines = fields.One2many('account.cash.operation.line', 'cash_id', 
                                            string='Interest Payment Lines', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]})
    
    amount_main = fields.Float(string='Transaction Amount', digits_compute=dp.get_precision('Account'), required=True, 
                               readonly=True, states={'draft': [('readonly', False)]})
    rate = fields.Float(string='Interest Rate (%)', required=True, readonly=True, states={'draft': [('readonly', False)]})
    day_count_basis = fields.Selection([
        ('360', '360'),
        ('365', '365')],            
        string='Day Count Basis', required=True, readonly=True, states={'draft': [('readonly', False)]}, default='360')
    rate_per_day = fields.Float(compute='_compute_rate_per_day', string='Rate per day', store=True)
    
    entry_count = fields.Integer(compute='_entry_count', string='# Posted Entries')
    
    #THANH: Add list of payment or receipts (line to account payment: phieu thu, phieu chi)
    operation_payment_lines = fields.One2many('account.cash.operation.in.out', 'out_cash_id', string='Operation Payments', readonly=False, copy=False)
    operation_receipt_lines = fields.One2many('account.cash.operation.in.out', 'in_cash_id', string='Operation Receipts', readonly=False, copy=False)
    
    #THANH: unused fields
    amount_cost = fields.Float(string='Transaction Costs', digits_compute=dp.get_precision('Account'), required=False, 
                               readonly=True, states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one('res.bank', string='Bank', required=False, readonly=True, states={'draft': [('readonly', False)]})
    
    @api.model
    def _get_full_dom(self):
        res = [(i < 10 and '0' + str(i) or str(i), str(i)) for i in range(1,31)]
        return res
    
    payment_date = fields.Selection('_get_full_dom', string='Date of Payment', 
          required=True, readonly=True, states={'draft': [('readonly', False)]}, default='25')
    
    @api.multi
    def _entry_count(self):
        for operation in self:
            move_ids = []
            for payment_line in operation.operation_payment_lines:
                if payment_line.payment_id:
                    for inv in payment_line.payment_id.payment_lines:
                        if inv.move_id:
                            move_ids.append(inv.move_id.id)
            for payment_line in operation.operation_receipt_lines:
                if payment_line.payment_id:
                    for inv in payment_line.payment_id.payment_lines:
                        if inv.move_id:
                            move_ids.append(inv.move_id.id)
            for line in self.payment_lines:
                if line.payment_id:
                    for inv in line.payment_id.payment_lines:
                        if inv.move_id:
                            move_ids.append(inv.move_id.id)
            operation.entry_count = len(move_ids)
            
    @api.multi
    def open_entries(self):
        move_line_ids = []
        for operation in self:
            for payment_line in operation.operation_payment_lines:
                if payment_line.payment_id:
                    for inv in payment_line.payment_id.payment_lines:
                        for move_line in inv.move_id.line_ids:
                            move_line_ids.append(move_line.id)
            for payment_line in operation.operation_receipt_lines:
                if payment_line.payment_id:
                    for inv in payment_line.payment_id.payment_lines:
                        for move_line in inv.move_id.line_ids:
                            move_line_ids.append(move_line.id)
            for line in operation.payment_lines:
                if line.payment_id:
                    for inv in line.payment_id.payment_lines:
                        for move_line in inv.move_id.line_ids:
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
    def open_accrual_entries(self):
        move_line_ids = []
        for operation in self:
            for line in operation.payment_lines:
                if line.reversed_accrual_move_id:
                    for move_line in line.reversed_accrual_move_id.line_ids:
                        move_line_ids.append(move_line.id)
                if line.accrual_move_id:
                    for move_line in line.accrual_move_id.line_ids:
                        move_line_ids.append(move_line.id)
        return {
            'name': _('Accrual Entries'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_line_ids)],
        }
        
    @api.one
    @api.constrains('name')
    def _check_doc_number(self):
        res = self.search([('name','=',self.name), ('id','!=',self.id)])
        if len(res):
            raise UserError(_("This Number (%s) already exist.") % (res[0].name))
    
    @api.onchange('date_start','date_stop')
    def onchange_date(self):
        if not (self.date_start and self.date_stop):
            return {}
        date_start = datetime.strptime(self.date_start, '%Y-%m-%d').date()
        date_stop = datetime.strptime(self.date_stop, '%Y-%m-%d').date()
        nbr_days = (date_stop - date_start).days
        if nbr_days < 1 :
            self.days = 0
            warning = {
               'title': _('Period Warning!'),
               'message' : _('Invalid Date Range!')
            }
            return {'warning': warning} 
        self.days = nbr_days
    
    @api.multi
    def button_confirm(self):
        self.write({'state': 'confirm'})
    
    @api.multi
    def button_done(self):
        for operation in self:
            operation_type = operation.type =='loan' and _('Loan') or _('Investment')
            
            for line in operation.payment_lines:
                if line.state == 'confirm':
                    continue
                else:
                    raise UserError(_("There is an interest payment is not confirmed."))
            
            total_payment = 0.0
            for line in operation.operation_payment_lines:
                if line.state == 'confirm':
                    total_payment += line.amount
            if float_compare(total_payment, operation.amount_main, precision_digits=2) != 0:
                raise UserError(_("Total payment value is not equal %s Amount !")%(_(operation_type)))
            
            total_receipt = 0.0
            for line in operation.operation_receipt_lines:
                if line.state == 'confirm':
                    total_receipt += line.amount
            if float_compare(total_receipt, operation.amount_main, precision_digits=2) != 0:
                raise UserError(_("Total receipt value is not equal %s Amount !")%(_(operation_type)))
            
            
        self.write({'state': 'done'})
        
    @api.multi
    def button_cancel(self):
        for demand in self:
            count = demand._entry_count()
            if count > 0:
                raise UserError(_("There are posted Entries. You must cancel it first."))
            vals = {}
            vals['state'] = 'draft'
            demand.write(vals)        
        return True
    
    @api.multi
    def compute_lines(self):
        self.ensure_one()
        if not self.amount_main:
            raise UserError(_("Loan Amount must bigger than zero."))
        if not self.rate:
            raise UserError(_("Rate must bigger than zero."))
        if not self.days:
            raise UserError(_("Days must bigger than zero."))
        
        months = int(self.days / 30) + 2
        index = 1
        num_payment = 1
        date_start = date_end =False
        unposted_line_ids = self.payment_lines.filtered(lambda x: not x.state == 'confirm')
        commands = [(2, line_id.id, False) for line_id in unposted_line_ids]
        
        cumulative_amount = 0.0
        while (months >= index):
            if date_end and date_end >= self.date_stop:
                break
            if index == 1:
                date_start = self.date_start
                if int(self.date_start[-2:]) > int(self.payment_date):
                    date_start =  datetime.strptime(self.date_start, DATE_FORMAT) + relativedelta(months=1)
                    date_start = date_start.strftime(DATE_FORMAT)
                    
                date_end = date_start[0:7] + '-'+ str(self.payment_date)
                date_end = datetime.strptime(date_end, DATE_FORMAT)
                dow = date_end.strftime('%A')
    
                plus_days = 0
                if dow == 'Saturday':
                    plus_days = 2
                if dow == 'Sunday':
                    plus_days = 1
                
                #THANH: add more days into date end in case payment date is Saturday (+2) and Sunday (+1)
                if plus_days:
                    date_end = date_end + relativedelta(days=+plus_days)
                    
                date_start = datetime.strptime(self.date_start, DATE_FORMAT)
                days = (date_end - date_start).days
                date_end = date_end.strftime(DATE_FORMAT)
                if self.date_stop < date_end:
                    date_end = self.date_stop
            else:
                date_start =  datetime.strptime(date_end, DATE_FORMAT) + relativedelta(days=+1)
                
                date_end = datetime.strptime(date_end, DATE_FORMAT) + relativedelta(months=1)
                date_end = date_end.strftime(DATE_FORMAT)
                date_end = date_end[0:7]
                date_end = date_end + '-'+ str(self.payment_date)
                date_end = datetime.strptime(date_end, DATE_FORMAT)
                dow = date_end.strftime('%A')
    
                plus_days = 0
                if dow == 'Saturday':
                    plus_days = 2
                if dow == 'Sunday':
                    plus_days = 1
                
                #THANH: add more days into date end in case payment date is Saturday (+2) and Sunday (+1)
                if plus_days:
                    date_end = date_end + relativedelta(days=+plus_days)
                if self.date_stop < date_end.strftime(DATE_FORMAT):
                    date_end = self.date_stop
                    date_end = datetime.strptime(date_end, DATE_FORMAT)
                    
                days = (date_end - date_start).days + 1
                date_end = date_end.strftime(DATE_FORMAT)
            
            if days > 0:
                if self.type == 'loan':
                    name = _("Tiền lãi vay kỳ %s của khế ước số '%s'")%(num_payment, self.name)
                else:
                    name = _("Tiền lãi đầu tư kỳ %s của mã đầu tư số '%s'")%(num_payment, self.name)
                    
                amount = days * self.rate_per_day
                amount = self.currency_id.round(amount)
                cumulative_amount += amount
                vals = {
                    'date': date_end,
                    'payment_method_id': self.payment_method_id.id,
#                     'actual_amount':amount,
                    'cash_id': self.id,
                    'sequence': index,
                    'name': name,
                    'cumulative_amount': cumulative_amount,
                    'days': days,
                }
                commands.append((0, False, vals))
                num_payment += 1
                
            index +=1
        self.write({'payment_lines': commands})
        return True
    
    @api.multi
    def unlink(self):
        unlink_ids = []
        for s in self:
            if s.state in ('draft'):
                unlink_ids.append(s['id'])
            else:
                raise UserError(_("Only Demands in state 'draft' can be deleted !"))
        return super(AccountCashOperation, self).unlink()
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default = default.copy()
        default.update({
                'name': None,
                'state': 'draft',
                'amount_main': None,
                'rate': None,
                'amount_interest': None,
                'date_start': None,
                'date_stop': None,
                'days': None,    
                'date': time.strftime('%Y-%m-%d'),
                'user_id': self.env.user.id,
            })
        return super(AccountCashOperation, self).copy(default)

class AccountCashOperationLine(models.Model):
    _name = 'account.cash.operation.line'
    _description = 'Interest Payment lines'
    _order = 'sequence,date'
    
    @api.one
    @api.depends('state', 'days', 'cash_id.operation_payment_lines.state')
    def _compute_interest_amount(self):
        for line in self:
#             if line.state == 'confirm':
#                 continue
            if not line.date:
                #THANH: trong truong hop them dong tra lai tre han
                continue
            if not line.days:
                #THANH: trong truong hop them dong tra lai tre han
                line.days = (datetime.strptime(line.date, DATE_FORMAT) - datetime.strptime(line.cash_id.date_stop, DATE_FORMAT)).days
            if not line.days:
                continue
            
            demand_amount = line.cash_id.amount_main
            pre_payment_date = line.date
            for pre_payment in line.cash_id.payment_lines:
                if pre_payment.date >= line.date:
                    break
                pre_payment_date = pre_payment.date
            
            amount = 0.0
            interval_days = 0.0
            payment_lines = [x for x in line.cash_id.operation_payment_lines if x.state == 'confirm']
            if len(payment_lines):
                payment_lines.reverse()
                for payment in payment_lines:
                    if payment.state == 'confirm' and payment.date > pre_payment_date:
                        rate_per_day = demand_amount * (line.cash_id.rate/100) / float(line.cash_id.day_count_basis)
                        days = (datetime.strptime(payment.date, DATE_FORMAT) - datetime.strptime(pre_payment_date, DATE_FORMAT)).days
                        amount += line.currency_id.round(days * rate_per_day)
                        interval_days += days
                        
                    if payment.state == 'confirm' and payment.date <= line.date:
                        demand_amount -= payment.amount
            
            line.loan_amount = line.currency_id.round(demand_amount)
            if amount == 0:
                line.rate_per_day = demand_amount * (line.cash_id.rate/100) / float(line.cash_id.day_count_basis)
                line.amount = line.currency_id.round(line.days * line.rate_per_day)
                    
            if interval_days > 0:
                rate_per_day = demand_amount * (line.cash_id.rate/100) / float(line.cash_id.day_count_basis)
                line.amount = line.currency_id.round((line.days - interval_days) * rate_per_day) + amount
                line.rate_per_day = line.amount / line.days
            
            if line.state != 'confirm' and line.id and not line.actual_amount:
                self._cr.execute('''update account_cash_operation_line 
                                    set actual_amount = %s
                                    where id=%s
                '''%(line.amount, line.id))
#                 line.write({'actual_amount': line.amount})
#                 line.actual_amount = line.amount
    
    @api.one
    @api.depends('actual_amount')
    def _compute_cumulative_amount(self):
        for line in self:
            cumulative_amount = 0.0
            for payment in line.cash_id.payment_lines:
                cumulative_amount += payment.actual_amount
                if payment.sequence >= line.sequence:
                    break
            line.cumulative_amount = cumulative_amount
            
    cash_id = fields.Many2one('account.cash.operation', string='Cash Operation', required=True, ondelete='cascade')
    payment_method_id = fields.Many2one('account.journal', string='Payment Method', domain="[('type','in',('cash','bank'))]", required=True,
                                        readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Payment Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    sequence = fields.Integer(required=False)
    
    date = fields.Date('Action Date', index=True, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', related='cash_id.currency_id', store=True)
    
    days = fields.Integer(string='Days', readonly=True)
    rate_per_day = fields.Float(compute='_compute_interest_amount', string='Rate per day', store=True)
    loan_amount = fields.Float(compute='_compute_interest_amount', string='Loan Amount', digits=0, readonly=True, store=True)
    amount = fields.Float(compute='_compute_interest_amount', string='Interest Amount', digits=0, readonly=True, store=True)
    actual_amount = fields.Float(string='Actual Interest Amount', required=False, readonly=True, states={'draft': [('readonly', False)]})
    cumulative_amount = fields.Float(compute='_compute_cumulative_amount', string='Cumulative Amount', required=False, readonly=True, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')],          
        string='State', required=True, readonly=True, default='draft')
    
    payment_id = fields.Many2one('account.payment', string='Payment')
    
    #THANH: Accrual Moves
    accrual_move_id = fields.Many2one('account.move', string='Accrual Entry')
    reversed_accrual_move_id = fields.Many2one('account.move', string='Reversed Accrual Entry')
    
    @api.multi
    def write(self, vals):
        if vals.get('date', False):
            for this_line in self:
                #THANH: check duplicate date
                res = self.search([('cash_id', '=', this_line.cash_id.id), ('date','=',vals['date'])])
                if len(res):
                    raise UserError(_("Payment date '%s' is duplicate. Please select another date.") % (vals['date'],))
            
                if this_line.sequence == 1:
                    pre_payment_date = this_line.cash_id.date_start
                    this_payment_date = vals['date']
                    days = (datetime.strptime(this_payment_date, DATE_FORMAT) - datetime.strptime(pre_payment_date, DATE_FORMAT)).days
                    vals.update({'days': days})
                else:   
                    #THANH: time ngay thanh toan truoc do
                    for pre_payment in this_line.cash_id.payment_lines:
                        if pre_payment.sequence == (this_line.sequence - 1):
                            pre_payment_date = pre_payment.date
                    pre_payment_date = datetime.strptime(pre_payment_date, DATE_FORMAT)# + relativedelta(days=+1)
                    
#                     if this_line.cash_id.date_stop < vals['date']:
#                         vals['date'] = this_line.cash_id.date_stop
                        
                    days = (datetime.strptime(vals['date'], DATE_FORMAT) - pre_payment_date).days
                    vals.update({'days': days})
                
                #THANH: update lai payment date va days cua nhung next payment
                pre_payment_date = vals['date']
                for next_payment in this_line.cash_id.payment_lines:
                    if next_payment.sequence > this_line.sequence:
                        pre_payment_date = datetime.strptime(pre_payment_date, DATE_FORMAT)# + relativedelta(days=+1)
                        next_payment_date = datetime.strptime(next_payment.date, DATE_FORMAT)
                        days = (next_payment_date - pre_payment_date).days
                        next_payment.write({'days': days})
                        pre_payment_date = next_payment_date.strftime(DATE_FORMAT)
                        
        return super(AccountCashOperationLine, self).write(vals)
    
    @api.model
    def create(self, vals):
        if vals.get('cash_id',False) and not vals.get('sequence', False):
            res = self.search([('cash_id', '=', vals['cash_id'])])
            if len(res):
                sequence = len(self.search([('cash_id', '=', vals['cash_id'])])) + 1
                vals['sequence'] = sequence
        if not vals.get('days', False):
            #THANH: check duplicate date
            res = self.search([('cash_id', '=', vals['cash_id']), ('date','=',vals['date'])])
            if len(res):
                raise UserError(_("Payment date '%s' is duplicate. Please select another date.") % (vals['date'],))
            
            cash = self.env['account.cash.operation'].browse(vals['cash_id'])
            days = (datetime.strptime(vals['date'], DATE_FORMAT) - datetime.strptime(cash.date_stop, DATE_FORMAT)).days
            vals.update({'days':days})
        return super(AccountCashOperationLine, self).create(vals) 
    
    #THANH: Print Payment as VAS template
    @api.multi
    def print_payment(self):
        self.ensure_one()
        if self.payment_id:
            datas = {'ids' : [self.payment_id.id]}
            res = self.payment_id.print_payment()
            res.update({'datas': datas})
            return res
            
    @api.multi
    def create_move(self):
        account_payment = self.env['account.payment']
        for line in self:
            if line.cash_id.state == 'done':
                raise UserError(_("This demand '%s' has been done. You can not modify the payment.")%(_(line.cash_id.name)))
            if line.cash_id.state == 'draft':
                raise UserError(_("You must confirm this operation firstly."))
            #THANH: create an interest payment
            payment_methods = line.payment_method_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            invoice_line_vals = {'partner_id': line.cash_id.partner_id.id,
                                 'journal_id': line.cash_id.journal_id.id,
                                 'currency_id': line.cash_id.currency_id.id,
                                 'reference': line.cash_id.name,
                                 'invoice_lines': [(0, 0, {'account_id': line.cash_id.account_recognition_id.id,
                                                          'price_unit': line.actual_amount,
                                                          'name': line.name})]}
            
            partner_bank_id = False
            if line.payment_method_id.type == 'bank':
                if not line.cash_id.partner_bank_id:
                    raise UserError(_("Please define Bank for Partner '%s' !")%(_(line.cash_id.partner_id.name)))
                partner_bank_id = line.cash_id.partner_bank_id.id
                
            payment_vals = {'payment_type': 'outbound', 'show_invoice': True, 'payment_method_id': payment_method_id.id, 'partner_type': 'supplier',
                            'partner_bank_id': partner_bank_id,
                            'partner_id': line.cash_id.partner_id.id, 
                            'source_document': line.cash_id.name,
                            'invoice_journal_id': line.cash_id.journal_id.id,
                            'journal_id': line.payment_method_id.id,
                            'communication': line.name,
                            'payment_date': line.date,
                            'amount': line.actual_amount,
                            'payment_lines': [(0,0,invoice_line_vals)]}
            if line.payment_id:
                line.payment_id.payment_lines.unlink()
                line.payment_id.write(payment_vals)
                payment = line.payment_id
            else:
                payment = account_payment.create(payment_vals)
            payment.post()
            line.write({'payment_id': payment.id, 'state': 'confirm'})
    
    @api.multi
    def cancel(self):
        for line in self:
            if line.payment_id:
                line.payment_id.cancel()
            line.write({'state': 'draft'})
                
class AccountCashOperationInOut(models.Model):
    _name = 'account.cash.operation.in.out'
    _description = 'Cash In Out'
    _order = 'date desc'
    
    in_cash_id = fields.Many2one('account.cash.operation', string='In Cash Operation', ondelete='cascade')
    out_cash_id = fields.Many2one('account.cash.operation', string='Out Cash Operation', ondelete='cascade')
    
    name = fields.Char(string='Description', required=True, readonly=True, states={'draft': [('readonly', False)]})
    payment_method_id = fields.Many2one('account.journal', string='Payment Method', domain="[('type','in',('cash','bank'))]", required=True,
                                        readonly=True, states={'draft': [('readonly', False)]})
    payment_type = fields.Selection([('inbound', 'Inbound'), ('outbound', 'Outbound')], required=True)
    date = fields.Date('Date', index=True, default=fields.Date.context_today, readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency')
    amount = fields.Monetary(string='Amount', currency_field='currency_id', required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')],          
        string='State', required=True, readonly=True, default='draft')
    payment_id = fields.Many2one('account.payment', string='Payment Ref')
    
    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        operation = self.in_cash_id or self.out_cash_id
        total_amount = 0.0
        if self.in_cash_id:
            for line in operation.operation_receipt_lines:
                if line.state == 'confirm':
                    total_amount += line.amount
        if self.out_cash_id:
            for line in operation.operation_payment_lines:
                if line.state == 'confirm':
                    total_amount += line.amount
        if (total_amount + self.amount) > operation.amount_main:
            operation_type = operation.type =='loan' and _('Loan') or _('Investment')
            raise UserError(_("Total payment value is bigger than %s Amount !")%(_(operation_type)))
            
    @api.onchange('payment_method_id')
    def _onchange_payment_method_id(self):
        if self.payment_method_id:
            self.currency_id = self.payment_method_id.currency_id.id or self.payment_method_id.company_id.currency_id.id
    
    @api.model
    def default_get(self, fields): 
        rec = super(AccountCashOperationInOut, self).default_get(fields)
        operation_id = self._context.get('operation_id')
        if operation_id:
            operation = self.env['account.cash.operation'].browse(operation_id)
            rec['payment_method_id'] = operation.payment_method_id.id   
            rec['amount'] = operation.amount_main
        return rec
    
    @api.multi
    def create_move(self):
        account_payment = self.env['account.payment']
        for line in self:
            cash_id = line.in_cash_id or line.out_cash_id
            
            if cash_id.state == 'done':
                raise UserError(_("This demand '%s' has been done. You can not modify the payment.")%(_(cash_id.name)))
            
            #THANH: create an interest payment
            payment_methods = line.payment_method_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            
            invoice_line_vals = {'partner_id': cash_id.partner_id.id,
                                 'journal_id': cash_id.journal_id.id,
                                 'currency_id': cash_id.currency_id.id,
                                 'reference': cash_id.name,
                                 'invoice_lines': [(0, 0, {'account_id': cash_id.account_id.id,
                                                          'price_unit': line.amount,
                                                          'name': line.name})]}
            
            partner_bank_id = False
            if line.payment_method_id.type == 'bank':
                if not cash_id.partner_bank_id:
                    raise UserError(_("Please define Bank for Partner '%s' !")%(_(cash_id.partner_id.name)))
                partner_bank_id = cash_id.partner_bank_id.id
            
            payment_type = line.payment_type
            partner_type = 'supplier'
            if payment_type == 'inbound':
                partner_type = 'customer'
                
            payment_vals = {'payment_type': payment_type, 'show_invoice': True, 'payment_method_id': payment_method_id.id, 'partner_type': partner_type,
                            'partner_bank_id': partner_bank_id,
                            'partner_id': cash_id.partner_id.id, 
                            'source_document': cash_id.name,
                            'invoice_journal_id': cash_id.journal_id.id,
                            'journal_id': line.payment_method_id.id,
                            'communication': line.name,
                            'payment_date': line.date,
                            'amount': line.amount,
                            'payment_lines': [(0,0,invoice_line_vals)]}
            if line.payment_id:
                line.payment_id.payment_lines.unlink()
                line.payment_id.write(payment_vals)
                payment = line.payment_id
            else:
                payment = account_payment.create(payment_vals)
            payment.post()
            line.write({'payment_id': payment.id, 'state': 'confirm'})
    
    @api.multi
    def cancel(self):
        for line in self:
            if line.payment_id:
                line.payment_id.cancel()
            line.write({'state': 'draft'})
    
    #THANH: Print Payment as VAS template
    @api.multi
    def print_payment(self):
        self.ensure_one()
        if self.payment_id:
            datas = {'ids' : [self.payment_id.id]}
            res = self.payment_id.print_payment()
            res.update({'datas': datas})
            return res
        
class AccountPayment(models.Model):
    _inherit = "account.payment"    
    
    operation_payment_id = fields.Many2one('account.cash.operation', string="Cash Operation Payment", ondelete='cascade')
    operation_receipt_id = fields.Many2one('account.cash.operation', string="Cash Operation Receipt", ondelete='cascade')
    
    @api.model
    def create(self, vals):
        #THANH: check payment date must be >= start date of Cash Operation
        if vals.get('operation_id', False) and vals.get('date_start',False):
            operation = self.env['account.cash.operation'].browse(vals['operation_id'])
            if operation.payment_date < vals['date_start']:
                raise UserError(_('Payment date must be greater than Start date.'))
        return super(AccountPayment, self).create(vals)
    
    @api.multi
    def unlink(self):
        operation_line = self.env['account.cash.operation.line']
        operation_inout = self.env['account.cash.operation.in.out']
        for line in self:
            operation = False
            res = operation_line.search([('payment_id','=',line.id)])
            if not res:
                res = operation_inout.search([('payment_id','=',line.id)])
                if res:
                    operation = res.out_cash_id or res.in_cash_id
            else:
                operation = res.cash_id
            if operation:
                if operation.state == 'done':
                    raise UserError(_("The related document '%s' has been done. You can not delete this payment.")%(operation.name))
                res.write({'state':'draft'})
        return super(AccountPayment, self).unlink()
    
    @api.multi
    def post(self):
        for rec in self:
            #THANH: Kiem tra so tien nhan duoc tu vay/dau tu co bang yeu cau ko
            if rec.operation_receipt_id:
                total_receipt = 0.0
                for line in rec.operation_receipt_id.operation_receipt_lines:
                    total_receipt += line.total_payment
                if rec.operation_receipt_id.amount_main != total_receipt:
                    raise UserError(_("Total receipt money (%s) is difference from Amount Demand (%s) of Document '%s'")%(total_receipt, rec.operation_receipt_id.amount_main, rec.operation_receipt_id.name))
        super(AccountPayment, self).post()