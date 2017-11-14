# -*- coding: utf-8 -*-
import time
from datetime import date, datetime

from openerp.osv import expression
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

from collections import OrderedDict

class AccountAccount(models.Model):
    _inherit = "account.account"
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', '=ilike', name + '%'), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        accounts = self.search(domain + args, limit=limit)
        #THANH: return like name get
        result = []
        for account in accounts:
            name = account.code + ' - ' + account.name
            result.append((account.id, name))
        return result
    
    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for account in self:
            #THANH: sua ngay 10/08/2017: Thao noi la show het cho dep
            name = account.code + ' - ' + account.name
            #THANH: No need to show account name in reference
#             if self.env.context and self.env.context.get('show_account_name',False):
#                 name = account.code + ' - ' + account.name
#             else:
#                 name = account.code
            result.append((account.id, name))
        return result
    
class AccountAccountType(models.Model):
    _inherit = "account.account.type"
    
    #THANH: add type income and expenses
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
        ('income', 'Income'),
        ('expenses', 'Expenses'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: liquidity type is for cash or bank accounts"\
        ", payable/receivable is for vendor/customer accounts.")

class AccountAccountTag(models.Model):
    _inherit = 'account.account.tag'
    
    #THANH: Allow translate this field
    name = fields.Char(required=True, translate=True)
    code = fields.Char(string='Code', required=False)
    
class AccountTax(models.Model):
    _inherit = 'account.tax'
    _order = 'name,type_tax_use'
    
    transaction_type = fields.Selection([
                ('import','Import'),
                ('export','Export'),
                ('none','None')], 'Transaction Type', default='none')

class AccountJournal(models.Model):
    _inherit = "account.journal"
    
    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('situation', 'Situation'),
            ('general', 'Miscellaneous'),
        ], required=True,
        help="Select 'Sale' for customer invoices journals."\
        " Select 'Purchase' for vendor bills journals."\
        " Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments."\
        " Select 'General' for miscellaneous operations journals."\
        " Select 'Opening/Closing Situation' for entries generated for new fiscal years.")
    
    #THANH: Add new field named Accrual Account (using for Loan and Investment
    accrual_account_id = fields.Many2one('account.account', string='Accrual Account',
        domain=[('deprecated', '=', False), ('type', '!=', 'view')], help="It acts as a accrual amount on loan, investment, ...")
    
    internal_type = fields.Selection([
            ('public', 'Public'),
            ('internal', 'Internal'),
        ], string='Internal Type', default='public')
    
    @api.model
    def default_get(self, fields):
        rec = super(AccountJournal, self).default_get(fields)
        rec.update({
            #THANH: alway = true at creation
            'update_posted': True,
        })
        return rec
    
    @api.model
    def _get_sequence_prefix(self, code, refund=False):
        prefix = code.upper()
        if refund:
            prefix = 'R' + prefix
#         return prefix + '/%(range_year)s/'
        return prefix + '-%(year)s%(month)s' #THANH: use this format
    
    @api.model
    def _create_sequence(self, vals, refund=False):
        """ Create new no_gap entry sequence for every new Journal"""
        prefix = self._get_sequence_prefix(vals['code'], refund)
        seq = {
            'name': vals['name'],
            'implementation': 'standard',#THANH: use standard instead of no gap
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            'use_date_range': False,#THANH: use sequence history
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.env['ir.sequence'].create(seq)
    
class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _order = "date desc, move_id desc, group_cp asc, id asc, debit desc, credit desc"
    #
    
    #THANH: advance field to improve update debit and credit, transaction_rate will keep debit and credit value 
    #but average_rate will change them based on amount currency and rate in menu currencies
    rate_type = fields.Selection([('transaction_rate', 'Transaction Rate'),
                                  ('average_rate', 'Average Rate')], 
                                 string='Rate Type', default='average_rate', copy=True)
    currency_ex_rate = fields.Float(string='Currency Rate', copy=False, readonly=False)
    second_ex_rate = fields.Float(string='2nd Rate', copy=False, readonly=True)
    second_amount = fields.Monetary(string='2nd Amount', currency_field='second_currency_id', copy=False, readonly=True)
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', store=True, string='2nd Currency', readonly=True, copy=False)
    
    warehouse_id = fields.Many2one(related='move_id.warehouse_id',readonly=True,store=True,string="Warehouse")
    
    #THANH: new field sequence help to drag drop move line in Journal Entry
    group_cp = fields.Integer(string="Group CP", default=0)
    
    @api.model
    def default_get(self, fields):
        rec = super(AccountMoveLine, self.with_context(from_default_get=True)).default_get(fields)
        context = dict(self._context or {})
#         active_model = context.get('active_model')
#         active_ids = context.get('active_ids')
        
        #THANH: auto update field group cp
        line_ids = context.get('line_ids')
        if line_ids:
            decimal_places = self.env.user.company_id.currency_id.decimal_places
            lines = []
            for line in line_ids:
                line_data = line[2]
                if line[1]:
                    move_data = self.browse([line[1]])
                    line_data = {'group_cp': move_data.group_cp,
                                 'debit': move_data.debit,
                                 'credit': move_data.credit,
                                 'currency_id': move_data.currency_id and move_data.currency_id.id or False,
                                 'amount_currency': move_data.amount_currency}
                    
                    if line[2]:
                        line_data.update(line[2])
                lines.append(line_data)

            balance = 0.0
            balance_currency = 0.0
            currency_id = False
            group_cp = 0
            for line_data in sorted(lines, key=lambda k: k['group_cp']):
                group_cp = line_data['group_cp']
                currency_id = line_data['currency_id']
                balance += round(line_data['debit'], decimal_places) - round(line_data['credit'], decimal_places)
                balance_currency += line_data['amount_currency']
                if float_is_zero(balance, precision_rounding=5):
                    group_cp += 1
                    currency_id = False
            
            rec.update({
                'group_cp': group_cp,
                'debit': balance < 0.0 and abs(balance) or 0.0,
                'credit': balance > 0.0 and abs(balance) or 0.0,
                'currency_id': currency_id,
                'amount_currency': balance_currency * -1
            })
        return rec
    
    #THANH: pass context to cron update debit, credit for posted entries
    @api.multi
    def _update_check(self):
        """ Raise Warning to cause rollback if the move is posted, some entries are reconciled or the move is older than the lock date"""
        move_ids = set()
        for line in self:
            err_msg = _('Move name (id): %s (%s)') % (line.move_id.name, str(line.move_id.id))
            allow_update = self._context.get('allow_update', False)
            if line.move_id.state != 'draft' and not allow_update:
                raise UserError(_('You cannot do this modification on a posted journal entry, you can just change some non legal fields. You must revert the journal entry to cancel it.\n%s.') % err_msg)
            if line.reconciled and not (line.debit == 0 and line.credit == 0) and not allow_update:
                raise UserError(_('You cannot do this modification on a reconciled entry. You can just change some non legal fields or you must unreconcile first.\n%s.') % err_msg)
            if line.move_id.id not in move_ids:
                move_ids.add(line.move_id.id)
            self.env['account.move'].browse(list(move_ids))._check_lock_date()
        return True
    
    #THANH: modify field counterpart to be stored and add new field reconcile_counterpart to query sql faster
    #THANH: store array ids char only
    @api.one
    @api.depends('move_id.line_ids')
    def _get_counterpart_ids(self):
        counterpart = set()
        counterpart_code = set()
        this_debit_side = self.debit and True or False
        for line in self.move_id.line_ids:
            line_debit_side = line.debit and True or False
            #THANH: use field group_cp to determine the counter-part accounts in an Journal Entry (where many Dr and Cr account) 
            if (line.account_id.id != self.account_id.id) and this_debit_side != line_debit_side and self.group_cp == line.group_cp:
                counterpart.add(str(line.account_id.id))
                counterpart_code.add(str(line.account_id.code))
        self.counterpart_ids = ",".join(counterpart)
        self.counterpart_code = ",".join(counterpart_code)
    
    @api.one
    @api.depends('reconciled', 'move_id.line_ids.reconciled')
    def _get_reconcile_counterpart_ids(self):
        counterpart = set()
        counterpart_code = set()
        for line in self:
            for r in line.matched_debit_ids:
                for r1 in r.debit_move_id.move_id.line_ids:
                    if (r.debit_move_id.account_id.id != r1.account_id.id): 
                        counterpart.add(str(r1.account_id.id))
                        counterpart_code.add(str(r1.account_id.code))
            for r in line.matched_credit_ids:
                for r1 in r.credit_move_id.move_id.line_ids:
                    if (r.credit_move_id.account_id.id != r1.account_id.id): 
                        counterpart.add(str(r1.account_id.id))
                        counterpart_code.add(str(r1.account_id.code))

        self.reconcile_counterpart_ids = ",".join(counterpart)
        self.reconcile_counterpart_code = ",".join(counterpart_code)
        
        #THANH: trong truong hop but toan mua tai san hay CCDC (242, 331) sau do thanh toan hoa don thi (331,111 or 112)
            #neu counterpart_code trong nghia la but toan 242 ko lay dc cp2 account thi lay cp2 account cua 331 la 111 or 112
            #Giup cho sau nay lam Cash-flow co chi tieu tai san hay CCDC dc mua = 111 or 112
        
        if not counterpart and self.account_id.type not in ['receivable', 'payable']:
            #THANH: trong truong hop line dang tinh toan la tk 242 thi counterpart_code = null nen se lay tu line doi ung (tk: 331)
            reconcile_counterpart_ids = ''
            reconcile_counterpart_code = ''
            for line2 in self.move_id.line_ids:
                if (line2.account_id.id != self.account_id.id) and line2.reconcile_counterpart_ids:
                    reconcile_counterpart_ids += line2.reconcile_counterpart_ids
                    reconcile_counterpart_code += line2.reconcile_counterpart_code
            self.reconcile_counterpart_ids = reconcile_counterpart_ids
            self.reconcile_counterpart_code = reconcile_counterpart_code
        else:
            #THANH: trong truong hop line dang tinh toan la tk 331 thi update nguoc lai cho line 242
            for line2 in self.move_id.line_ids:
                if (line2.account_id.id != self.account_id.id):
                    line2.reconcile_counterpart_ids = self.reconcile_counterpart_ids
                    line2.reconcile_counterpart_code = self.reconcile_counterpart_code
                    
    counterpart_ids = fields.Char("CP IDs", compute='_get_counterpart_ids', store=True, help="Compute the counter part accounts of this journal item for this journal entry. This can be needed in reports.")
    reconcile_counterpart_ids = fields.Char("CP2 IDs", compute='_get_reconcile_counterpart_ids', store=True)
    
    #THANH: add new field to help accountant filter on account_move_line
    counterpart_code = fields.Char("CP Code", compute='_get_counterpart_ids', store=True)
    reconcile_counterpart_code = fields.Char("CP2 Code", compute='_get_reconcile_counterpart_ids', store=True)
    
    #THANH: dung de in so cai va xem khoan nao la ung tien (cua khach hang or ncc)
    extend_payment = fields.Selection([
        ('none', 'All'),
        ('payment', 'Payment'),
        ('advance', 'Advance'),
    ],  string='Payment Mode', readonly=True, default='none')
    
    @api.one
    @api.constrains('account_id')
    def _check_account_type(self):
        if self.account_id.type == 'view':
            raise UserError(_("Account '%s' is type 'View', please choose another account.") % (self.account_id.code))
    
    @api.onchange('amount_currency', 'currency_id')
    def _onchange_currency(self):
        #THANH: this method help to control changing currency and amount currency to auto compute debit and credit
        if self.amount_currency:
            if not self.currency_id and self.env.user.company_id.second_currency_id:
                self.currency_id = self.env.user.company_id.second_currency_id.id
                from_currency = self.env.user.company_id.second_currency_id
            else:
                from_currency = self.currency_id
            
            if from_currency:
                decimal_places = self.env.user.company_id.currency_id.decimal_places
                ex_from_currency_rate, from_currency_rate = self.currency_id.with_context({'date':self.move_id.date})\
                                                    ._get_conversion_rate(from_currency, self.env.user.company_id.currency_id)
                self.currency_ex_rate = from_currency_rate
                self.debit = round(abs(self.amount_currency * ex_from_currency_rate), decimal_places) if self.amount_currency > 0 else 0.0
                self.credit = round(abs(self.amount_currency * ex_from_currency_rate), decimal_places) if self.amount_currency < 0 else 0.0
            else:
                self.debit = 0.0
                self.credit = 0.0
        return
    
    @api.onchange('currency_ex_rate', 'amount_currency')
    def _onchange_currency_ex_rate(self):
        if self.currency_ex_rate and self.currency_id:
            ex_second_rate, second_rate = self.currency_id.with_context({'date':self.move_id.date})\
                                                ._get_conversion_rate(self.currency_id, self.env.user.company_id.currency_id)
            if ex_second_rate != 0.0 and ex_second_rate > 1:
                value = self.amount_currency / self.currency_ex_rate
            else:
                value = self.amount_currency * (1 / self.currency_ex_rate)
            
            value = round(value, self.env.user.company_id.currency_id.round_decimal_places)
            self.debit = abs(value) if self.amount_currency > 0 else 0.0
            self.credit = abs(value) if self.amount_currency < 0 else 0.0
        return
    
    @api.one
    @api.constrains('currency_id','amount_currency','rate_type','currency_ex_rate')
    def _check_currency_id(self):
        #THANH: check constrain on field amount_currency, currency_id, currency rate, rate type
#         if self.currency_id and self.amount_currency == 0.0:
#             raise UserError(_("Amount Currency must be difference than 0.0!\n At line %s")%(self.name))
        if not self.currency_id and self.amount_currency != 0.0:
            raise UserError(_("Currency should not be empty!\n At line %s")%(self.name))
        if self.currency_id and self.rate_type == 'transaction_rate' and self.amount_currency != 0.0 and self.currency_ex_rate <= 0.0:
            raise UserError(_("Currency Rate should not be empty!\n At line %s")%(self.name))
    
class AccountMove(models.Model):
    _inherit = 'account.move'
    
    doc_date = fields.Date(required=False, string='Document Date', states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    date = fields.Date(required=True, string='GL Date', states={'posted': [('readonly', True)]}, index=True, default=fields.Date.context_today)
    
    @api.multi
    def assert_balanced(self):
        if not self.ids:
            return True
        prec = self.env['decimal.precision'].precision_get('Account')
        
        #THANH: modify original sql, no need to check draft entry
        self._cr.execute("""\
            SELECT      aml.move_id
            FROM        account_move_line aml
                        JOIN account_move am on aml.move_id=am.id
            WHERE       am.state='posted' and aml.move_id in %s
            GROUP BY    aml.move_id
            HAVING      abs(sum(aml.debit) - sum(aml.credit)) > %s
            """, (tuple(self.ids), 10 ** (-max(5, prec))))
        if len(self._cr.fetchall()) != 0:
            raise UserError(_("Cannot create unbalanced journal entry."))
        return True
    
    @api.one
    @api.constrains('date')
    def _check_entry_date(self):
        pass_check = self._context and self._context.get('force_post',False) or False
        
        #THANH: Prevent generate entry in closed period
        if not pass_check:
            period = self.env['account.period'].search([('date_start', '<=' ,self.date), ('date_stop', '>=', self.date)], limit=1)
            if (period and period.state == 'done'):
                raise ValidationError(_("The period '%s' has been closed. You can not generate account entry !")%(period.name))
        
        #THANH: unallow input future transaction
#         today = fields.Date.context_today(self)
        today = datetime.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        if self.date and self.date > today:
            raise ValidationError(_("Transaction Date '%s' is invalid. Unallow to input future transaction!")%(self.date))
    
    @api.multi
    def button_cancel(self):
        #THANH" call check date
        self._check_entry_date()
        invoice_force_cancel = self._context and self._context.get('invoice_force_cancel',False) or False
        if not invoice_force_cancel:
            for move in self:
                sql = '''
                    SELECT count(*)
                    FROM account_invoice
                    WHERE move_id = %s
                '''%(move.id)
                self.env.cr.execute(sql)
                res = self.env.cr.fetchone()
                if res[0] > 0:
                    raise UserError(_("This Journal Entry created from menu Invoice. You must cancel Invoice firstly."))
            
        payment_force_cancel = self._context and self._context.get('payment_force_cancel',False) or False
        if not payment_force_cancel:
            for move in self:
                #THANH: check related account payment
                sql = '''
                SELECT count(*)
                FROM (
                    SELECT id
                    FROM account_payment_invoice
                    WHERE move_id = %s
                    
                    UNION
                    
                    SELECT id
                    FROM account_payment_fee
                    WHERE move_id = %s
                    
                    UNION
                    
                    SELECT distinct move_id
                    FROM account_move_line
                    WHERE move_id = %s and payment_id is not null
                ) foo
                '''%(move.id, move.id, move.id)
                self.env.cr.execute(sql)
                res = self.env.cr.fetchone()
                if res[0] > 0:
                    raise UserError(_("This Journal Entry created from menu Payment. You must cancel Payment firstly."))
            
        return super(AccountMove, self).button_cancel()
    
    @api.multi
    def remove_line(self):
        ctx = {'check_move_validity': False}
        for move in self:
            if move.state == 'draft':
                for line in move.line_ids:
                    line.with_context(ctx).unlink()
        return True
    
    #THANH: dung de in so cai va xem khoan nao la ung tien (cua khach hang or ncc)
    extend_payment = fields.Selection([
        ('none', 'All'),
        ('payment', 'Payment'),
        ('advance', 'Advance'),
    ],  string='Payment Mode', readonly=True, default='none')
    
    #kiet: them warehouse
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", states={'posted': [('readonly', True)]})
    
    #THANH: get doc_date = date when no doc_dat e in Vals
    @api.model
    def create(self, vals):
        if not vals.get('doc_date',False):
            vals.update({'doc_date': vals.get('date', fields.Date.context_today)})
        move = super(AccountMove, self).create(vals)
        return move
    
    @api.multi
    def post(self):
        if self.ids:
            #THANH: check posted entry balance
            self._cr.execute('''
                SELECT      sum(aml.debit) debit, sum(aml.credit) credit
                FROM        account_move_line aml
                WHERE       aml.move_id in %s
                GROUP BY    aml.move_id
                ''', (tuple(self.ids), ))
            res = self._cr.fetchall()
            if len(res) != 0 and res[0][0] == 0.0 and res[0][1] == 0.0:
                raise UserError(_("Cannot create unbalanced journal entry."))
            
            #THANH: check posted entry balance
            self._cr.execute('''
                SELECT      distinct rate_type
                FROM        account_move_line aml
                WHERE       aml.move_id in %s
                ''', (tuple(self.ids), ))
            if len(self._cr.fetchall()) >= 2:
                raise UserError(_("Rate Type should be the same for all lines."))
        
        #THANH: update field extend_payment for move line
        for move in self:
            #THANH: check posted entry balance
            decimal_places = move.company_id.currency_id.decimal_places
            prec = self.env['decimal.precision'].precision_get('Account')
            self._cr.execute('''
                SELECT      aml.move_id
                FROM        account_move_line aml
                WHERE       aml.move_id in %s
                GROUP BY    aml.move_id
                HAVING      abs(round(sum(aml.debit),%s) - round(sum(aml.credit),%s)) > %s
                ''', (tuple([move.id]), decimal_places, decimal_places, 10 ** (-max(5, prec))))
            
            res = self._cr.fetchall()
            if len(res) != 0:
                raise UserError(_("Cannot create unbalanced journal entry."))
                
            #THANH: update field 2nd currency into null to prevent revert and post again (cron will not work after these fields updated))
            sql_set = '''
                second_amount = 0.0, 
                second_ex_rate = 0.0
            '''
            if move.extend_payment == 'advance':
                sql_set += " ,extend_payment='advance'"
            if self.env.user.company_id.second_currency_id:
                sql_set += " ,second_currency_id=%s"%(self.env.user.company_id.second_currency_id.id)
            self.env.cr.execute('''
                UPDATE account_move_line 
                SET %s
                WHERE move_id = %s;
            '''%(sql_set, move.id))
            
            #THANH: Update narration = fist move line
            if not move.narration:
                self.env.cr.execute('''
                    update account_move am
                    set narration = (select name from account_move_line where move_id=am.id  
                                        order by date desc, move_id desc, id asc, debit desc, credit desc
                                        limit 1)
                    where id = %s;
                '''%(move.id))
        super(AccountMove, self).post()
    
    @api.multi
    def reverse_moves(self, date=None, journal_id=None):
#         date = date or fields.Date.today()
#         reversed_moves = self.env['account.move']
#         for ac_move in self:
            #THANH: xoa luon but toan danh gia chenh lech ty gia da thuc hien (module goc tao revert move)
#             ac_move.with_context({'allow_update':True}).button_cancel()
#             ac_move.refresh()
#             ac_move.with_context({'allow_update':True}).unlink()
#             reversed_move = ac_move.copy(default={'date': date,
#                 'journal_id': journal_id.id if journal_id else ac_move.journal_id.id,
#                 'ref': _('reversal of: ') + ac_move.name})
#             for acm_line in reversed_move.line_ids:
#                 acm_line.with_context(check_move_validity=False).write({
#                     'debit': acm_line.credit,
#                     'credit': acm_line.debit,
#                     'amount_currency': -acm_line.amount_currency
#                     })
#             reversed_moves |= reversed_move
#         if reversed_moves:
#             reversed_moves._post_validate()
#             reversed_moves.post()
#             return [x.id for x in reversed_moves]
        return []
    
class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"
    
    def create_exchange_rate_entry(self, aml_to_fix, amount_diff, diff_in_currency, currency, move_date):
        """ Automatically create a journal entry to book the exchange rate difference.
            That new journal entry is made in the company `currency_exchange_journal_id` and one of its journal
            items is matched with the other lines to balance the full reconciliation.
        """
        for rec in self:
            if not rec.company_id.currency_exchange_journal_id:
                raise UserError(_("You should configure the 'Exchange Rate Journal' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not self.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not self.company_id.expense_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            move_vals = {'journal_id': rec.company_id.currency_exchange_journal_id.id, 'rate_diff_partial_rec_id': rec.id}

            # The move date should be the maximum date between payment and invoice (in case
            # of payment in advance). However, we should make sure the move date is not
            # recorded after the end of year closing.
            if move_date > rec.company_id.fiscalyear_lock_date:
                move_vals['date'] = move_date
            move = rec.env['account.move'].create(move_vals)
            amount_diff = rec.company_id.currency_id.round(amount_diff)
            diff_in_currency = currency.round(diff_in_currency)
            
            #THANH: compute currency_ex_rate
            currency_ex_rate = 0.0
            if abs(diff_in_currency) and abs(amount_diff):
                if abs(diff_in_currency) > abs(amount_diff):
                    currency_ex_rate = currency.round(abs(diff_in_currency) / abs(amount_diff))
                else:
                    currency_ex_rate = currency.round(abs(amount_diff) / abs(diff_in_currency))
                    
            line_to_reconcile = rec.env['account.move.line'].with_context(check_move_validity=False).create({
                'name': _('Currency exchange rate difference'),
                'debit': amount_diff < 0 and -amount_diff or 0.0,
                'credit': amount_diff > 0 and amount_diff or 0.0,
                'account_id': rec.debit_move_id.account_id.id,
                'move_id': move.id,
                'currency_id': currency.id,
                'amount_currency': -diff_in_currency,
                'partner_id': rec.debit_move_id.partner_id.id,
                
                #THANH: alway transaction rate to prevent re compute debit or credit
                'rate_type': 'transaction_rate',
                'currency_ex_rate': currency_ex_rate,
            })
            rec.env['account.move.line'].create({
                'name': _('Currency exchange rate difference'),
                'debit': amount_diff > 0 and amount_diff or 0.0,
                'credit': amount_diff < 0 and -amount_diff or 0.0,
                'account_id': amount_diff > 0 and rec.company_id.currency_exchange_journal_id.default_debit_account_id.id or rec.company_id.currency_exchange_journal_id.default_credit_account_id.id,
                'move_id': move.id,
                'currency_id': currency.id,
                'amount_currency': diff_in_currency,
                'partner_id': rec.debit_move_id.partner_id.id,
                
                #THANH: alway transaction rate to prevent re compute debit or credit
                'rate_type': 'transaction_rate',
                'currency_ex_rate': currency_ex_rate,
            })
            for aml in aml_to_fix:
                partial_rec = rec.env['account.partial.reconcile'].create({
                    'debit_move_id': aml.credit and line_to_reconcile.id or aml.id,
                    'credit_move_id': aml.debit and line_to_reconcile.id or aml.id,
                    'amount': abs(aml.amount_residual),
                    'amount_currency': abs(aml.amount_residual_currency),
                    'currency_id': currency.id,
                })
            move.post()
        return line_to_reconcile.id, partial_rec.id
    
    @api.multi
    def unlink(self):
        """ When removing a link between entries, we need to revert the eventual journal entries we created to book the
            fluctuation of the foreign currency's exchange rate.
            We need also to reconcile together the origin currency difference line and its reversal in order to completly
            cancel the currency difference entry on the partner account (otherwise it will still appear on the aged balance
            for example).
        """
        # we must unlink the reconciliation with the exchange rate difference entry as well, to be able to reconcile it with its reversal entry
        to_unlink = self
        exchange_rate_entries = self.env['account.move'].search([('rate_diff_partial_rec_id', 'in', self.ids)])
        for rec in self:
            partial_rec_set = OrderedDict.fromkeys([rec])
            aml_set = self.env['account.move.line']
            total_debit = 0
            total_credit = 0
            total_amount_currency = 0
            currency = None
            for partial_rec in partial_rec_set:
                if currency is None:
                    currency = partial_rec.currency_id
                for aml in [partial_rec.debit_move_id, partial_rec.credit_move_id]:
                    if aml not in aml_set:
                        total_debit += aml.debit
                        total_credit += aml.credit
                        aml_set |= aml
                        if aml.currency_id and aml.currency_id == currency:
                            total_amount_currency += aml.amount_currency
                    for x in aml.matched_debit_ids | aml.matched_credit_ids:
                        partial_rec_set[x] = None
            digits_rounding_precision = aml_set[0].company_id.currency_id.rounding
            if float_compare(total_debit, total_credit, precision_rounding=digits_rounding_precision) == 0 \
              or (currency and float_is_zero(total_amount_currency, precision_rounding=currency.rounding)):
                #if the reconciliation is full, also unlink any currency rate diffence entry created
                exchange_rate_entries = self.env['account.move'].search([('rate_diff_partial_rec_id', 'in', [x.id for x in partial_rec_set.keys()])])

        # revert the currency difference entry
        reversed_moves = exchange_rate_entries.reverse_moves()
        # find the origin currency difference line on the partner account and its newly created reversal, and store them in a list
        pairs_to_rec = []
        for rev_move in self.env['account.move'].browse(reversed_moves):
            if not rev_move.rate_diff_partial_rec_id:
                continue
            origin_move = exchange_rate_entries.filtered(lambda x: x.rate_diff_partial_rec_id == rev_move.rate_diff_partial_rec_id)
            for acm_line in rev_move.line_ids:
                if acm_line.account_id.reconcile:
                    for origin_line in origin_move.line_ids:
                        if origin_line.account_id == acm_line.account_id and origin_line.debit == acm_line.credit and origin_line.credit == acm_line.debit:
                            to_unlink |= origin_line.matched_debit_ids | origin_line.matched_credit_ids
                            to_rec = origin_line + acm_line
                            pairs_to_rec.append(to_rec)
        #make sure that the exchange_rate_entries aren't linked to any partial reconciliation anymore
        
        #THANH: hide exchange_rate_entries because it has been deleted from exchange_rate_entries.reverse_moves() above
        #exchange_rate_entries.write({'rate_diff_partial_rec_id': False})
        
        # the call to super() had to be delayed in order to mark the move lines to reconcile together (to use 'rate_diff_partial_rec_id')
        res = super(AccountPartialReconcile, to_unlink).unlink()
        
        #THANH: after delete reconcile of payment, then delete reconcile of currency revaluation
        exchange_rate_entries.line_ids.remove_move_reconcile()
        exchange_rate_entries.with_context({'allow_update':True}).button_cancel()
        exchange_rate_entries.with_context({'allow_update':True}).unlink()
            
        # now that the origin currency difference line is not reconciled anymore, we can reconcile it with its reversal entry to cancel it completly
        for to_rec in pairs_to_rec:
            to_rec.reconcile()
        return res
    
    
