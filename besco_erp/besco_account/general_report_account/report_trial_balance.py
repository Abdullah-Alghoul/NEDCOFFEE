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

class FinTrialBalanceReport(models.TransientModel):
    _name = "fin.trial.balance.report"
    _description = "Fin Trial Balance Report"
    
    @api.multi
    def print_report(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'fn_trial_balance_report'}
    
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
        start_date = False
        end_date = False
        uid = self.env.user.id
        account_obj = self.env['account.account']
        
        for report in self:
            company_id = self.company_id.id
            currency_id = self.company_id.currency_id and self.company_id.currency_id.id or False
            second_currency_id = self.company_id.second_currency_id and self.company_id.second_currency_id.id or 'null'

            #Get company info
            sql ='''
                delete from trial_balance_detail where trial_id = %s;
            '''%(report.id)
            self.env.cr.execute(sql)
            
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            ac_date = report.ac_date or ''
            
            journal_ids = [x.id for x in report.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
            #THANH: use this to pass list into an sql function
            journal_ids = '{%(journal_ids)s}'%({'journal_ids':journal_ids,})
            
            filter_aml_account_ids = ''
            if len(report.account_ids):
                account_ids = []
                for acc in report.account_ids:
                    if acc.type == 'view':
                        full_accounts = account_obj.search_read([('parent_id','child_of', acc.id), ('type','!=','view')], ['id'])
                    else:
                        full_accounts = account_obj.search_read([('parent_id','parent_of', acc.id), ('level','>=',2), ('type','!=','view')], ['id'])
                    account_ids += [x['id'] for x in full_accounts]
                account_ids = (','.join(map(str, account_ids)))
                filter_aml_account_ids += ' and coa_id in (%(account_id)s)'%({'account_id':account_ids})
            
            sql = _('''
                Insert Into trial_balance_detail (create_uid, create_date, write_uid, write_date,
                    acc_level, coa_id, coa_code, 
                    coa_name, description,
                    begin_dr, begin_cr, period_dr, period_cr, ac_dr, ac_cr, end_dr, end_cr,
                    begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd,
                    trial_id, com_currency_id, second_currency_id)
                SELECT  %s, current_timestamp, %s, current_timestamp,
                    acc_level, coa_id, coa_code, coa_name, '' as description, 
                    begin_dr, begin_cr, period_dr, period_cr, ac_dr, ac_cr, end_dr, end_cr, 
                    begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd, 
                    %s, %s, %s 
                FROM fin_trial_balance_report('%s', '%s', %s, '%s', '%s'::INT[])
                where 
                    (begin_dr notnull or begin_cr notnull
                    or period_dr notnull or period_cr notnull
                    or end_dr notnull or end_cr notnull)
                    and acc_level != 10
                    %s --filter_aml_account_ids
                order by acc_level, coa_code
            ''')
            sql = sql%(uid, uid, report.id, currency_id, second_currency_id, start_date, end_date, company_id, ac_date, journal_ids, filter_aml_account_ids)
            self.env.cr.execute(sql)
            
            sql = _('''
                Insert Into trial_balance_detail (create_uid, create_date, write_uid, write_date,
                    coa_name, description,
                    begin_dr, begin_cr, period_dr, period_cr, ac_dr, ac_cr, end_dr, end_cr,
                    begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd,
                    
                    trial_id, com_currency_id, second_currency_id)
               
                SELECT %s, current_timestamp, %s, current_timestamp,
                    '' as coa_name, 'Tổng' as description,
                    sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                    sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                    
                    sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd, sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                    sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd,
                    %s, %s, %s
                FROM (
                    SELECT  coa_code,
                        begin_dr, begin_cr, period_dr, period_cr, 
                        ac_dr, ac_cr, end_dr, end_cr, 
                        begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, 
                        ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd
                    FROM fin_trial_balance_report('%s', '%s', %s, '%s', '%s'::INT[])
                        where acc_level <> 10 
                        %s --filter_aml_account_ids
                        and
                        (
                            begin_dr notnull or begin_cr notnull
                            or period_dr notnull or period_cr notnull
                            or end_dr notnull or end_cr notnull
                        )
                )x
            ''')
            sql = sql%(uid, uid, report.id, currency_id, second_currency_id, start_date, end_date, company_id, ac_date, journal_ids, filter_aml_account_ids)
            self.env.cr.execute(sql) 
            
            if not len(report.account_ids):
                #THANH: Tài khoản ngoại bảng
                sql = _('''
                    Insert Into trial_balance_detail (create_uid, create_date, write_uid, write_date,
                        coa_name, description,
                        begin_dr, begin_cr, period_dr, period_cr, ac_dr, ac_cr, end_dr, end_cr,
                        begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd,
                        trial_id, com_currency_id, second_currency_id)
                        
                    SELECT %s, current_timestamp, %s, current_timestamp,
                        '' as coa_name, 'Tài Khoản Ngoại bảng' as description, 
                        sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                        sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                        
                        sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd,sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                        sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd,
                        %s, %s, %s
                    FROM fin_trial_balance_report('%s', '%s', %s, '%s', '%s'::INT[])
                    WHERE acc_level = 10
                        and (
                            begin_dr notnull or begin_cr notnull
                            or period_dr notnull or period_cr notnull
                            or end_dr notnull or end_cr notnull
                        )
                ''')
                sql = sql%(uid, uid, report.id, currency_id, second_currency_id, start_date, end_date, company_id, ac_date, journal_ids)
                self.env.cr.execute(sql)
                
                sql = _('''
                Insert Into trial_balance_detail (create_uid, create_date, write_uid, write_date,
                        coa_name, description,
                        begin_dr, begin_cr, period_dr, period_cr, ac_dr, ac_cr, end_dr, end_cr,
                        begin_dr_2rd, begin_cr_2rd, period_dr_2rd, period_cr_2rd, ac_dr_2rd, ac_cr_2rd, end_dr_2rd, end_cr_2rd,
                        
                        trial_id, com_currency_id, second_currency_id)
                        
                    SELECT %s, current_timestamp, %s, current_timestamp,
                        '' as coa_name, 'Tồng cộng' as description, 
                        sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                        sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                        
                        sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd,sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                        sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd,
                        %s, %s, %s
                    FROM (
                            select  
                                sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                                sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                                
                                sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd,sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                                sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd
                                
                                FROM (
                                SELECT  coa_code,
                                        sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                                        sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                                        
                                        sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd,sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                                        sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd
                                        
                                    FROM fin_trial_balance_report('%s', '%s', %s, '%s', '%s'::INT[])
                                    where acc_level <> 10
                                    %s --filter_aml_account_ids
                                    and (begin_dr notnull or begin_cr notnull
                                    or period_dr notnull or period_cr notnull
                                    or end_dr notnull or end_cr notnull)
                                    group by coa_code
                                    order by 1)x
                            union
                            select 
                                sum(begin_dr) begin_dr, sum(begin_cr) begin_cr, sum(period_dr) period_dr, sum(period_cr) period_cr, 
                                sum(ac_dr) ac_dr, sum(ac_cr) ac_cr, sum(end_dr) end_dr, sum(end_cr) end_cr,
                                
                                sum(begin_dr_2rd) begin_dr_2rd,sum(begin_cr_2rd) begin_cr_2rd,sum(period_dr_2rd) period_dr_2rd,sum(period_cr_2rd) period_cr_2rd,
                                sum(ac_dr_2rd) ac_dr_2rd, sum(ac_cr_2rd) ac_cr_2rd, sum(end_dr_2rd) end_dr_2rd,sum(end_cr_2rd) end_cr_2rd
                                
                                FROM fin_trial_balance_report('%s', '%s', %s, '%s', '%s'::INT[])
                                WHERE acc_level = 10
                                        %s --filter_aml_account_ids
                                        and (begin_dr notnull or begin_cr notnull
                                        or period_dr notnull or period_cr notnull
                                        or end_dr notnull or end_cr notnull)
                        )y
                ''')
                sql = sql%(uid, uid, report.id, currency_id, second_currency_id, start_date, end_date, company_id, ac_date, journal_ids, filter_aml_account_ids, \
                           start_date, end_date, company_id, ac_date, journal_ids, filter_aml_account_ids)
                self.env.cr.execute(sql)
            
            #THANH: Show tk cha
            if report.show_parent:
                full_accounts_dict = {}
                for line in report.tria_ids:
                    if line.coa_code:
                        full_accounts = account_obj.search_read([('id','!=',line.coa_id), ('parent_id','parent_of',line.coa_id), ('level','>=',2)],
                                                                ['code','type','name','level'], order='code,level')
                        for account in full_accounts:
                            if not full_accounts_dict.has_key(account['code']):
                                full_accounts_dict.update({account['code']: 
                                                           {'coa_code':account['code'], 'coa_name':account['name'], 'acc_type':account['type'], 'acc_level': account['level'],
                                                            'begin_dr': line.begin_dr, 
                                                            'begin_cr': line.begin_cr, 
                                                            'period_dr': line.period_dr, 
                                                            'period_cr': line.period_cr, 
                                                            'ac_dr': line.ac_dr, 
                                                            'ac_cr': line.ac_cr, 
                                                            'end_dr': line.end_dr, 
                                                            'end_cr': line.end_cr, 
                                                            
                                                            'begin_dr_2rd': line.begin_dr_2rd, 
                                                            'begin_cr_2rd': line.begin_cr_2rd, 
                                                            'period_dr_2rd': line.period_dr_2rd, 
                                                            'period_cr_2rd': line.period_cr_2rd, 
                                                            'ac_dr_2rd': line.ac_dr_2rd, 
                                                            'ac_cr_2rd': line.ac_cr_2rd, 
                                                            'end_dr_2rd': line.end_dr_2rd, 
                                                            'end_cr_2rd': line.end_cr_2rd, 
                                                            
                                                            'trial_id': report.id, 'com_currency_id': line.com_currency_id.id, 'second_currency_id': line.second_currency_id.id,
                                                            }})
                            else:
                                full_accounts_dict.update({account['code']: 
                                                           {'coa_code':account['code'], 'coa_name':account['name'], 'acc_type':account['type'], 'acc_level': account['level'],
                                                            
                                                            'begin_dr': full_accounts_dict[account['code']]['begin_dr'] + line.begin_dr, 
                                                            'begin_cr': full_accounts_dict[account['code']]['begin_cr'] + line.begin_cr, 
                                                            'period_dr': full_accounts_dict[account['code']]['period_dr'] + line.period_dr, 
                                                            'period_cr': full_accounts_dict[account['code']]['period_cr'] + line.period_cr, 
                                                            'ac_dr': full_accounts_dict[account['code']]['ac_dr'] + line.ac_dr, 
                                                            'ac_cr': full_accounts_dict[account['code']]['ac_cr'] + line.ac_cr, 
                                                            'end_dr': full_accounts_dict[account['code']]['end_dr'] + line.end_dr, 
                                                            'end_cr': full_accounts_dict[account['code']]['end_cr'] + line.end_cr, 
                                                            
                                                            'begin_dr_2rd': full_accounts_dict[account['code']]['begin_dr_2rd'] + line.begin_dr_2rd, 
                                                            'begin_cr_2rd': full_accounts_dict[account['code']]['begin_cr_2rd'] + line.begin_cr_2rd, 
                                                            'period_dr_2rd': full_accounts_dict[account['code']]['period_dr_2rd'] + line.period_dr_2rd, 
                                                            'period_cr_2rd': full_accounts_dict[account['code']]['period_cr_2rd'] + line.period_cr_2rd, 
                                                            'ac_dr_2rd': full_accounts_dict[account['code']]['ac_dr_2rd'] + line.ac_dr_2rd, 
                                                            'ac_cr_2rd': full_accounts_dict[account['code']]['ac_cr_2rd'] + line.ac_cr_2rd, 
                                                            'end_dr_2rd': full_accounts_dict[account['code']]['end_dr_2rd'] + line.end_dr_2rd, 
                                                            'end_cr_2rd': full_accounts_dict[account['code']]['end_cr_2rd'] + line.end_cr_2rd, 
                                                            
                                                            'trial_id': report.id, 'com_currency_id': line.com_currency_id.id, 'second_currency_id': line.second_currency_id.id,
                                                            }})
                line_obj = self.env['trial.balance.detail']
                for key, vals in full_accounts_dict.items():
                    line_obj.create(vals)
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
    
    name = fields.Char(string="Name", default='Trial Balance')
    show_parent = fields.Boolean(string='Show Parent', default=True)
    
    account_ids = fields.Many2many('account.account', 'trial_balance_report_account_rel', 'report_id', 'account_id', string='Accounts')
    
    ac_date = fields.Date(string='AC Date', default=time.strftime('%Y-%m-%d'))
    tria_ids = fields.One2many('trial.balance.detail','trial_id',string = "Trial Balance detail")
    tria_idsvn = fields.One2many('trial.balance.detail','trial_id',string = "Trial Balance detail")
    
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, 
                                   default=lambda self: self.env['account.journal'].search([]))
    
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    #THANH: help to show tab second currency, should be readonly because it will call update to res.company again (will rase error for normal user)
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', string="2nd Company Currency", readonly=True)
    
    @api.multi
    def load_journal(self):
        domain = []
        if self._context.get('journal_type', False):
            domain = [('internal_type','=',self._context['journal_type'])]
        self.journal_ids = self.env['account.journal'].search(domain)
        
class TrialBalanceDetail(models.TransientModel):
    _name = "trial.balance.detail"
    _description = "Trial Balance detail"
    _order = "coa_code,acc_level,id"

    trial_id = fields.Many2one('fin.trial.balance.report')
    
    acc_level = fields.Integer(string="Acc Level")
    acc_type = fields.Char(string="Acc Type")#THANH: store it view account
    coa_id = fields.Integer(string="Acc ID")
    coa_code = fields.Char(string="Acc Code")
    coa_name = fields.Char(string="Acc Name")
    description = fields.Char(string="Description")
    
    begin_dr = fields.Monetary(string="Begin Dr", currency_field='com_currency_id')
    begin_cr = fields.Monetary(string="Begin Cr", currency_field='com_currency_id')
    period_dr = fields.Monetary(string="Period Dr", currency_field='com_currency_id')
    period_cr = fields.Monetary(string="Period Cr", currency_field='com_currency_id')
    end_dr = fields.Monetary(string="End Dr", currency_field='com_currency_id')
    end_cr = fields.Monetary(string="End Cr", currency_field='com_currency_id')
    ac_dr = fields.Monetary(string="AC Dr", currency_field='com_currency_id')
    ac_cr = fields.Monetary(string="AC Cr", currency_field='com_currency_id')
    
    
    begin_dr_2rd = fields.Monetary(string="Begin Dr", currency_field='second_currency_id')
    begin_cr_2rd = fields.Monetary(string="Begin Cr", currency_field='second_currency_id')
    period_dr_2rd = fields.Monetary(string="Period Dr", currency_field='second_currency_id')
    period_cr_2rd = fields.Monetary(string="Period Cr", currency_field='second_currency_id')
    end_dr_2rd = fields.Monetary(string="End Dr", currency_field='second_currency_id')
    end_cr_2rd = fields.Monetary(string="End Cr", currency_field='second_currency_id')
    ac_dr_2rd = fields.Monetary(string="AC Dr", currency_field='second_currency_id')
    ac_cr_2rd = fields.Monetary(string="AC Cr", currency_field='second_currency_id')
    
    second_currency_id = fields.Many2one('res.currency', string="2nd Currency", readonly=True)
    com_currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)