# -*- coding: utf-8 -*-
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

class account_account(models.Model):
    _inherit = "account.account"
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        remove_account_ids = []
        if context.get('filter_remove_account_ids') and len(context['filter_remove_account_ids']):
            account_ids = context['filter_remove_account_ids'][0][2]
            remove_account_ids += [x.id for x in self.with_context(filter_remove_account_ids=False).search([('id', 'child_of', account_ids)])]
#         if context.get('filter_remove_cp_account_ids') and len(context['filter_remove_cp_account_ids']):
#             account_ids = context['filter_remove_cp_account_ids'][0][2]
#             remove_account_ids += [x.id for x in self.with_context(filter_remove_cp_account_ids=False).search([('id', 'child_of', account_ids)])]
        
        if len(remove_account_ids):
            args += [('id', 'not in', remove_account_ids)]
        return super(account_account, self).search(args, offset, limit, order, count=count)
    
class ReportAccountLedger(models.TransientModel):
    _name = "report.account.ledger"
    _description = "Report Account Ledger"
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    @api.model
    def create(self, vals):
        result = super(ReportAccountLedger, self).create(vals)
        return result
    
    @api.model
    def default_get(self, vals):
        result = super(ReportAccountLedger, self).default_get(vals)
        return result
    
    @api.model
    def _get_current_month(self):
        return time.strftime('%m')
            
    times = fields.Selection([
        ('dates','Date'),
        ('month', 'Month'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='month')
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscalyear', default=_get_fiscalyear)
    date_start = fields.Date(string='Date start', default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date(string='Date end', default=time.strftime('%Y-%m-%d'))
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
        ('12','12')], string='Month', default=_get_current_month)
    quarter = fields.Selection([
        ('1', '1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Quarter', default='1')
    
    
    view_type = fields.Selection([
        ('normal','Normal Accounts'),
        ('partner','Partner Accounts'),
        ('liquidity', 'Liquidity Accounts')], string='View Type', default='normal')
    
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    child_company_ids  = fields.Many2many('res.company', 'report_account_ledger_company_rel', 'report_id', 'company_id', string='Child Companies')
    
    #THANH: help to show tab second currency, should be readonly because it will call update to res.company again (will rase error for normal user)
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', string="2nd Company Currency", readonly=True)
    
    partner_ids = fields.Many2many('res.partner', 'report_account_ledger_partner_rel', 'balance_id', 'partner_id', string='Partners')
    account_ids = fields.Many2many('account.account', 'report_account_ledger_account_rel', 'balance_id', 'account_id', string='Accounts')
    cp_account_ids = fields.Many2many('account.account', 'report_account_ledger_cp_account_rel', 'balance_id', 'account_id', string='Counterpart Accounts')
    cp2_account_ids = fields.Many2many('account.account', 'report_account_ledger_cp2_account_rel', 'balance_id', 'account_id', string='Counterpart Accounts 2')
    
    general_ledger_ids = fields.One2many('general.account.ledger','ledger_id',string = "General Account")
    detail_ledger_ids = fields.One2many('general.account.ledger.detail','ledger_id',string = "Detail")
    
    general_ledger_2rd_ids = fields.One2many('general.account.ledger','ledger_id',string = "2nd General Account")
    detail_ledger_2rd_ids = fields.One2many('general.account.ledger.detail','ledger_id',string = "2nd Detail")
    
    name = fields.Char(string="Name", default='Account Ledger')
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, 
                                   default=lambda self: self.env['account.journal'].search([]))
    
    extend_payment = fields.Selection([
        ('none', 'All'),
        ('payment', 'Payment'),
        ('advance', 'Advance'),
    ],  string='Payment Mode', readonly=False, default='none')
    
    @api.multi
    def load_journal(self):
    	domain = []
    	if self._context.get('journal_type', False):
    		domain = [('internal_type','=',self._context['journal_type'])]
    	self.journal_ids = self.env['account.journal'].search(domain)

    @api.onchange('account_ids')
    def _onchange_account_ids(self):
        self.view_type = 'normal'
        for account in self.account_ids:
            if account.type in ['payable','receivable']:
                self.view_type = 'partner'
                break
            if account.type in ['liquidity']:
                self.view_type = 'liquidity'
                break
        return
    
    @api.multi
    def print_account_ledger(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'general_report_account_ledger'}
    
    @api.multi
    def print_general_journal(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_general_journal'}
    
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

    @api.multi
    def load_data(self):
        for report in self:
            account_ids =[]
            cp_account_ids =[]
            cp2_account_ids = []
            journal_ids = []
            
            company_id = report.company_id.id
            child_company_ids = [x.id for x in report.child_company_ids]
            
            second_currency_id = report.company_id.second_currency_id and report.company_id.second_currency_id.id or False
            
            #Get company info
            sql ='''
                DELETE from general_account_Ledger where ledger_id = %s;
            '''%(report.id)
            self.env.cr.execute(sql)
            
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            if report.account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.account_ids])]):
                    account_ids.append(acc.id)
                
                account_ids = (','.join(map(str, account_ids)))
            
            if report.cp_account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.cp_account_ids])]):
                    cp_account_ids.append(acc.id)
                cp_account_ids = (','.join(map(str, cp_account_ids)))
            
            if report.cp2_account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.cp2_account_ids])]):
                    cp2_account_ids.append(acc.id)
                cp2_account_ids = (','.join(map(str, cp2_account_ids)))
                
            partner_ids = [x.id for x in report.partner_ids]
            partner_ids = (','.join(map(str, partner_ids)))
            
            journal_ids = [x.id for x in report.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
            
            #THANH: Insert table balance
            self.env['sql.account.ledger'].get_line(start_date, end_date, journal_ids, account_ids, cp_account_ids, cp2_account_ids, (),  #Except accounts for BS\
                                                    False, partner_ids, company_id, second_currency_id, report = report)
    def load_banalce(self):
        
        ac = 0.0
        nd_acc = 0.0
        for line in self.env['general.account.ledger.detail'].search([('ledger_id','=',self.id)], order = 'seq'):
            if line.seq == 99998:
                continue
            
            if line.seq == 99999:
                line.ac_balance = ac
                line.ac_balance_second = nd_acc
                continue
            
            nd_acc += abs(line.debit_second) + line.credit_second * (-1)
            line.ac_balance_second = nd_acc
            
            ac += abs(line.debit) + line.credit * (-1)
            line.ac_balance = ac
        
        return
    
    @api.multi
    def load_data_detail(self):
        for report in self:
            account_ids =[]
            cp_account_ids = []
            cp2_account_ids = []
            journal_ids = []
            
            company_id = report.company_id.id
            second_currency_id = report.company_id.second_currency_id and report.company_id.second_currency_id.id or False
            
            #Get company info
            sql ='''
                DELETE from general_account_ledger_detail where ledger_id = %s;
            '''%(report.id)
            self.env.cr.execute(sql)
            
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            if report.account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.account_ids])]):
                    account_ids.append(acc.id)
                
                account_ids = (','.join(map(str, account_ids)))
            
            if report.cp_account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.cp_account_ids])]):
                    cp_account_ids.append(acc.id)
                cp_account_ids = (','.join(map(str, cp_account_ids)))
            
            if report.cp2_account_ids:
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report.cp2_account_ids])]):
                    cp2_account_ids.append(acc.id)
                cp2_account_ids = (','.join(map(str, cp2_account_ids)))
                
            partner_ids = [x.id for x in report.partner_ids]
            partner_ids = (','.join(map(str, partner_ids)))
            
            journal_ids = [x.id for x in report.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
            
            #THANH: Insert table details
            self.env['sql.account.ledger'].get_line(start_date, end_date, journal_ids, account_ids, cp_account_ids, cp2_account_ids, (), #Except accounts for BS \
                                                    True, partner_ids, company_id, second_currency_id, report = report)
            
            self.load_banalce()
    
class GeneralAccountLedger(models.TransientModel):
    _name = "general.account.ledger"
    _description = "General Account Ledger"
    
    
    ledger_id = fields.Many2one('report.account.ledger')
    description = fields.Char(string="Description") 
    
    debit = fields.Monetary(string="Dr",currency_field='com_currency_id')
    credit = fields.Monetary(string="Cr",currency_field='com_currency_id')
    
    debit_second = fields.Monetary(string="2nd Dr",currency_field='second_currency_id')
    credit_second = fields.Monetary(string="2nd Cr",currency_field='second_currency_id')
    
    com_currency_id = fields.Many2one('res.currency', string="Currency")
    second_currency_id = fields.Many2one('res.currency', string="Currency")


class GeneralAccountLedgerDetail(models.TransientModel):
    _name = "general.account.ledger.detail"
    _description = "General Account Ledger Detail"
    _order = "seq"
    
    ledger_id = fields.Many2one('report.account.ledger')
    seq = fields.Integer(string="Sequence")
    gl_date = fields.Date(string="GL Date")
    doc_date = fields.Date(string="Doc Date")
    doc_no = fields.Char(string="Doc No", size=64)
    description = fields.Char(string="Description")
    acc_code = fields.Char(string="Acc")
    cp_acc_code = fields.Char(string="CP Acc")
    
    amount_currency = fields.Monetary(string="Amount Currency", currency_field='second_currency_id')
    currency_rate = fields.Monetary(string="Currency Rate", currency_field='second_currency_id')
    currency_name = fields.Char(string="Currency Name")
    
    debit = fields.Monetary(string="Dr",currency_field='com_currency_id')
    credit = fields.Monetary(string="Cr",currency_field='com_currency_id')
    
    debit_second = fields.Monetary(string="2nd Dr", currency_field='second_currency_id')
    credit_second = fields.Monetary(string="2nd Cr", currency_field='second_currency_id')
    second_ex_rate = fields.Monetary(string="2nd Rate", currency_field='second_currency_id')
    
    partner_id = fields.Many2one('res.partner', string="Partner")
    partner_code = fields.Char(related='partner_id.partner_code',string="Partner Code")
    
    com_currency_id = fields.Many2one('res.currency', string="Company Currency")
    second_currency_id = fields.Many2one('res.currency', string="Second Currency")
    ac_balance = fields.Monetary(string="AC balance",currency_field='com_currency_id')
    ac_balance_second = fields.Monetary(string="2nd AC Balance",currency_field='second_currency_id')
