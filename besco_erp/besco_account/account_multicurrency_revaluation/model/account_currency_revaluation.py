# -*- coding: utf-8 -*-
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

import time
from openerp import api, fields, models, _
from openerp.exceptions import UserError, UserError, ValidationError

class AccountCurrencyRevaluationModel(models.Model):
    _name = 'account.currency.revaluation.model'
    
    @api.model
    def _get_default_journal_id(self):
        """
        Get default journal if one is defined in company settings
        """
        return self.env.user.company_id.default_currency_reval_journal_id
    
    name = fields.Char(string='Name', required=True, default='/')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, default=_get_default_journal_id)
    account_ids = fields.Many2many('account.account', 'account_currency_revaluation_model_rel', 
                                   'model_id', 'account_id', 
                                   string='Accounts to revaluation', required=True, domain=[('type','!=','view')])
    
    #Thanh: Add some fields
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.regularization'))
    active = fields.Boolean(string='Active', default=True)
    
    
class AccountCurrencyRevaluation(models.Model):
    _name = 'account.currency.revaluation'

    name = fields.Char(string='Name', required=True, default='/')
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    @api.model
    def _get_current_month(self):
        return time.strftime('%m')
    
    times = fields.Selection([
        ('dates','Date'),
        ('month', 'Month'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='month', readonly=True, states={'draft': [('readonly', False)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscalyear', default=_get_fiscalyear, readonly=True, states={'draft': [('readonly', False)]})
    date_start = fields.Date(string='From Date', default=time.strftime('%Y-%m-%d'), readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date(string='To Date', default=time.strftime('%Y-%m-%d'), readonly=True, states={'draft': [('readonly', False)]})
    month = fields.Selection([
        ('01','1'),
        ('02','2'),
        ('03','3'),
        ('04','4'),
        ('05','5'),
        ('06','6'),
        ('07','7'),
        ('08','8'),
        ('09','9'),
        ('10','10'),
        ('11','11'),
        ('12','12')], string='Month', default=_get_current_month, readonly=True, states={'draft': [('readonly', False)]})
    quarter = fields.Selection([
        ('1', '1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Quarter', default='1', readonly=True, states={'draft': [('readonly', False)]})
    
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        domain="[('type','=','general')]",
        help="You can set the default journal in company settings.",
        required=True, readonly=True, states={'draft': [('readonly', False)]}
    )
    label = fields.Char(
        string='Entry description',
        size=100,
        help="This label will be inserted in entries description. "
             "You can use %(account)s, %(currency)s and %(rate)s keywords.",
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default="%(currency)s %(account)s "
                "%(rate)s currency revaluation"
    )
    model_id = fields.Many2one('account.currency.revaluation.model', string='Revaluation model', required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    revaluation_lines = fields.One2many('account.currency.revaluation.line', 'revaluation_id', string="Revaluation lines", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id, readonly=True, states={'draft': [('readonly', False)]})
    type = fields.Selection([
            ('unrealized','Unrealized Revaluation'),
            ('realized','Realized Revaluation'),
        ], required=True, string='Type', default='unrealized', readonly=True, states={'draft': [('readonly', False)]})
    
    state = fields.Selection([
            ('draft','Draft'),
            ('posted', 'Posted'),
        ], string='Status', readonly=True, default='draft')
    
    account_move_id = fields.Many2one('account.move', string='Journal Entry')#THANH: view be removed
    account_move_ids = fields.Many2many('account.move', 'account_currency_revaluation_move_rel', string='Journal Entries')
    
    @api.model
    def default_get(self, fields): 
        rec = super(AccountCurrencyRevaluation, self).default_get(fields)
        model = self.env['account.currency.revaluation.model'].search([('active','=',True)], limit=1)
        if model:
            rec['model_id'] = model.id
            rec['amount'] = model.journal_id.id
        return rec
    
    @api.multi
    def open_entries(self):
        move_line_ids = []
        for this in self:
            if len(this.account_move_ids):
                for move in this.account_move_ids:
                    for move_line in move.line_ids:
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
    def get_period(self, report):
        start_date, end_date = False, False
        if report.times == 'dates':
            start_date = report.date_start
            end_date = report.date_end
        else:
            year = report.fiscalyear_id.date_stop.split('-')[0]
            if report.times =='month':
                date = date_object(int(year), int(report.month), 01)
                
                start_date = year + '-%s-01'%(report.month)
                end_date = date + relativedelta(day=1, months=+1, days=-1)
                end_date = end_date.strftime('%Y-%m-%d')
            if report.times == 'years':
                start_date = report.fiscalyear_id.date_start
                end_date   = report.fiscalyear_id.date_stop
            if report.times == 'quarter':
                if report.quarter == '1':
                    start_date = year + '-01-01'
                    end_date = year + '-03-31'
                elif report.quarter == '2':
                    start_date = year + '-04-01'
                    end_date = year + '-06-30'
                elif report.quarter == '3':
                    start_date = year + '-07-01'
                    end_date = year + '-09-30'
                else:
                    start_date = year + '-10-01'
                    end_date = year + '-12-31'
                            
        return start_date, end_date
                   
    @api.model
    def _format_label(self, text, account_id, currency_id, rate):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param int currency_id: id of the currency to display
        @param float rate: rate to display
        """
        account_obj = self.env['account.account']
        currency_obj = self.env['res.currency']
        account = account_obj.browse(account_id)
        currency = currency_obj.browse(currency_id)
        data = {'account': account.code or False,
                'currency': currency.name or False,
                'rate': rate or False}
        return text % data

    @api.multi
    def _write_adjust_balance(self, account_id, currency_id, partner_id, amount, label, revaluation_line, move_id, transfer_account_id):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """

        if partner_id is None:
            partner_id = False
        move_line_obj = self.env['account.move.line']
        ctx = {'check_move_validity': False}
        company = self.company_id
        analytic_acc_id = (company.revaluation_analytic_account_id.id
                               if company.revaluation_analytic_account_id
                               else False)
        
        base_line = {'name': label,
                     'partner_id': partner_id,
                     'date': revaluation_line.revaluation_id.date_end,
                     
                     'currency_id': revaluation_line.currency_id.id,
                     'amount_currency' : 0.0,
                     'rate_type': 'transaction_rate',
                    }
        
        # over revaluation
        if amount >= 0.01:
            #THANH: Gain Other Income
            # Create a move line for Debit account to be revaluated
            line_data = {
                        #THANH: change solution amount > 0 should be in debit
                        'debit': amount,
                        'credit': 0.0,
                        'move_id': move_id,
                        'account_id': account_id,
                         }
            line_data.update(base_line)
            move_line_obj.with_context(ctx).create(line_data)
            # Create a move line to Credit revaluation gain account
            line_data = {
                        'debit': 0.0,
                        'credit': amount,
                        'account_id': self.type == 'realized' and company.income_currency_exchange_account_id.id or transfer_account_id,
                        'move_id': move_id,
                        'analytic_account_id': self.type == 'realized' and analytic_acc_id or False,
                        }
            line_data.update(base_line)
            move_line_obj.with_context(ctx).create(line_data)
        # under revaluation
        elif amount <= -0.01:
            #THANH: Loss
            amount = -amount
            # Create a move line to Credit account to be revaluated
            line_data = {
                            'debit': 0.0,
                            'credit': amount,
                            'move_id': move_id,
                            'account_id': account_id,
                        }
            line_data.update(base_line)
            move_line_obj.with_context(ctx).create(line_data)
            
            # Create a move line to Debit revaluation loss account
            line_data = {
                        'debit': amount,
                        'credit': 0.0,
                        'move_id': move_id,
                        'account_id': self.type == 'realized' and company.expense_currency_exchange_account_id.id or transfer_account_id,
                        'analytic_account_id': self.type == 'realized' and analytic_acc_id or False,
                        }
            line_data.update(base_line)
            move_line_obj.with_context(ctx).create(line_data)
            
    @api.multi
    def revaluate_currency(self):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """
        #THANH: get accounts
        account_ids = self.model_id.account_ids
        if not account_ids:
            raise UserError(
                _("No account to be revaluated found. "
                  "Please check 'Allow Currency Revaluation' "
                  "for at least one account in account form.")
            )
        
        #THANH: get date
        start_date, end_date = self.get_period(self)
        self.date_start = start_date
        self.date_end = end_date
            
        # Get balance sums
        account_sums = account_ids.compute_revaluations(self.type, self.date_end, self.company_id.id)
        
        # Create entries only after all computation have been done
        revaluation_line = self.env['account.currency.revaluation.line']
        self.env.cr.execute('delete from account_currency_revaluation_line where revaluation_id=%s'%(self.id))
        for account_id, account_tree in account_sums.iteritems():
            for currency_id, currency_tree in account_tree.iteritems():
                for partner_id, sums in currency_tree.iteritems():
                    foreign_balance = sums.get('foreign_balance', 0.0)
                    
                    if self.type == 'realized' and foreign_balance != 0.0:
                        continue
                    if self.type == 'unrealized' and sums['revaluation_balance'] == 'dr_balance' and sums['balance'] < 0:
                        continue
                    if self.type == 'unrealized' and sums['revaluation_balance'] == 'cr_balance' and sums['balance'] > 0:
                        continue
                    if self.type == 'unrealized' and not foreign_balance:
                        continue
                    
                    vals = {'label': '', 'revaluation_id': self.id, 'account_id':  sums['id']}
                    vals.update(sums)
                    vals.pop('groupby_account')
                    vals.pop('revaluation_balance')
                    revaluation_line.create(vals)
    @api.multi
    def cancel(self):
        if self.account_move_ids:
            for move in self.account_move_ids:
                move.with_context(force_cancel=True).button_cancel()
                move.unlink()
        self.state = 'draft'
            
    @api.multi
    def post(self):
        #THANH: POST Revaluation Entry (New function)
        company = self.journal_id.company_id or self.env.user.company_id
        move_obj = self.env['account.move']
        move_line_obj = self.env['account.move.line']
        ctx = {'check_move_validity': False}
        for this in self:
            #THANH: Check account firstly
            if this.type == 'realized':
                if not company.income_currency_exchange_account_id or not company.expense_currency_exchange_account_id:
                    raise UserError(
                        _("No Realized Revaluation Accounts are defined"
                          " for your company.")
                    )
            else:
                if (not company.revaluation_loss_account_id and not company.revaluation_gain_account_id):
                    raise UserError(
                        _("No Unrealized Revaluation Accounts are defined"
                          " for your company.")
                    )
                if not company.provision_bs_loss_account_id or not company.provision_bs_gain_account_id:
                    raise UserError(_("Configuration error!\nThe Default Debit Account or Default Credit Account was not set on Journal '%s'.")%(_(this.journal_id.name)))
            
            transfer_account_id = company.provision_bs_loss_account_id.id
            
            move_ids = []
            has_line = False
            debit , credit = 0.0, 0.0
            for line in this.revaluation_lines:
                if this.type == 'unrealized' and line.account_id.revaluation_balance == 'dr_balance' and line.balance < 0:
                    continue
                if this.type == 'unrealized' and line.account_id.revaluation_balance == 'cr_balance' and line.balance > 0:
                    continue
                    
                if line.unrealized_gain_loss:
                    base_move = {'name': _("Currency Revaluation at '%s' for account '%s'"%(this.date_end, line.account_id.code)),
                                 'journal_id': this.journal_id.id,
                                 'date': this.date_end}
                    move = move_obj.create(base_move)
            
                    if line.unrealized_gain_loss >= 0.01:
                        debit += line.unrealized_gain_loss
                        credit += 0.0
                        
                    elif line.unrealized_gain_loss <= -0.01:
                        debit += 0.0
                        credit += -line.unrealized_gain_loss
                        
                    has_line = True
                    rate = line.revaluation_rate
                    label = self._format_label(
                        this.label, line.account_id.id, line.currency_id.id, rate
                    )
                    line.write({'label': label})#THANH: update label
                    self._write_adjust_balance(
                                                line.account_id.id,
                                                line.currency_id.id,
                                                line.partner_id and line.partner_id.id or False,
                                                line.unrealized_gain_loss,
                                                label,
                                                line,
                                                move.id,
                                                transfer_account_id)
                    move.post()
                    move_ids.append(move.id)
                    
            if has_line:
                if this.type == 'unrealized':
                    profit_loss = debit - credit
                    analytic_acc_id = (this.company_id.revaluation_analytic_account_id.id
                               if this.company_id.revaluation_analytic_account_id
                               else False)
                    
                    if profit_loss:
                        base_move = {'name': _("Currency Revaluation at '%s' for account '%s'"%(this.date_end, profit_loss > 0 and company.revaluation_gain_account_id.code or company.revaluation_loss_account_id.code)),
                                     'journal_id': this.journal_id.id,
                                     'date': this.date_end}
                        move = move_obj.create(base_move)
                        
                        #THANH: first item for profit and loss account (tai khoan loi lo chua ghi nhan)
                        move_line = {'name': _('Kết chuyển lãi, lỗ tỷ giá hối đoái đánh giá lại'),
                            'amount_currency': 0.0,
                            'date': this.date_end,
                            'debit': profit_loss < 0 and -profit_loss or 0.0,
                            'credit': profit_loss > 0 and profit_loss or 0.0,
                            'move_id': move.id,
                            'account_id': profit_loss < 0 and company.revaluation_loss_account_id.id or company.revaluation_gain_account_id.id,
                            'analytic_account_id': analytic_acc_id,
                            
                            'rate_type': 'transaction_rate',
                        }
                        move_line_obj.with_context(ctx).create(move_line)
                        
                        #THANH: second item for transfer account (413)
                        move_line = {'name': _('Kết chuyển lãi, lỗ tỷ giá hối đoái đánh giá lại'),
                            'amount_currency': 0.0,
                            'date': this.date_end,
                            'debit': profit_loss > 0 and profit_loss or 0.0,
                            'credit': profit_loss < 0 and -profit_loss or 0.0,
                            'move_id': move.id,
                            'account_id': transfer_account_id,
                            'analytic_account_id': False,
                            
                            'rate_type': 'transaction_rate',
                        }
                        move_line_obj.with_context(ctx).create(move_line)
                        
                        move.post()
                        move_ids.append(move.id)
                        
                this.account_move_ids = move_ids
                this.state = 'posted'
            
class AccountCurrencyRevaluationLine(models.Model):
    _name = 'account.currency.revaluation.line'
    _order = 'account_id, partner_id, currency_id'
    
    @api.one
    @api.depends('revaluation_id.date_end', 'foreign_balance', 'currency_id', 'balance', 'debit', 'credit')
    def _get_currency_rate(self):
        date = self.revaluation_id.date_end
        ex_rate , rate = self.currency_id.with_context({'date':date})._get_conversion_rate(self.currency_id, self.company_currency_id)
        self.revaluation_rate = rate
        revaluated_balance = self.company_currency_id.round(self.foreign_balance * ex_rate)
        self.revaluated_balance = revaluated_balance
        self.unrealized_gain_loss =  revaluated_balance - self.balance
            
    revaluation_id = fields.Many2one('account.currency.revaluation', string="Revaluation", ondelete="cascade")
    label = fields.Char(required=True, string="Label")
    
    account_id = fields.Many2one('account.account', string='Account', required=False, domain=[('deprecated', '=', False)])
    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency')
    foreign_balance = fields.Monetary(default=0.0, string='Amount Currency', currency_field='currency_id')
    
    debit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='revaluation_id.company_id.currency_id', readonly=True)
    
    revaluation_rate = fields.Float(compute='_get_currency_rate', string='Revaluation Rate', currency_field='company_currency_id', store=True)
    revaluated_balance = fields.Monetary(compute='_get_currency_rate', string='Revaluated Balance', currency_field='company_currency_id', store=True)
    unrealized_gain_loss = fields.Monetary(compute='_get_currency_rate', string='Unrealized Gain Loss', currency_field='company_currency_id', store=True)

class AccountMove(models.Model):
    _inherit = "account.move"
    
    @api.multi
    def button_cancel(self):
        #THANH: Kiểm tra nếu bút toán liên quan đến đánh giá tỷ giá thì báo lỗi
        pass_check = self._context and self._context.get('force_cancel',False) or False
        for move in self:
            sql = '''
                SELECT count(*)
                FROM account_currency_revaluation_move_rel
                WHERE account_move_id = %s
            '''%(move.id)
            self.env.cr.execute(sql)
            res = self.env.cr.fetchone()
            if res[0] > 0 and not pass_check:
                raise UserError(_("This Journal Entry created from menu Currency Revaluation. You must cancel Revaluation firstly."))
        return super(AccountMove, self).button_cancel()
    
    
    