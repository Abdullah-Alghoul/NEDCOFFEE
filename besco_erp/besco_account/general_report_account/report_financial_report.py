# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT as DF
from openerp.tools.misc import formatLang
import time
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

class account_financial_report(models.Model):
    _inherit = "account.financial.report"
    _description = "Account Report"
    _order = "report_id,sequence"
    
    report_id = fields.Many2one('account.financial.report', string='Report Header')
    thuyet_minh = fields.Char(string="Description")
    ma_so = fields.Char(string="Code")
    account_except_ids = fields.Many2many('account.account', 'account_account_except_financial_report', 'report_line_id', 'account_id', 'Except Accounts')
    report_type = fields.Selection([
        ('bs', 'B/S'),
        ('pl','P/L'),
        ('cashflow','Direct Cashflow'),
        ('cashflow_indirect','Indirect Cashflow'),
        ('other','Others'),], string='Report Type', default='other')
    
    balance_value = fields.Selection([
        ('begin_value', 'Begining Value'),
        ('periodical_value','Periodical Value'),
        ('end_value','Ending Value')], string='Balance Value', default='periodical_value')
    
    balance_side = fields.Selection([
        ('balance', 'Balance'),
        ('balance_dr','Dr Balance'),
        ('balance_cr','Cr Balance')], string='Balance Side', default='balance')
    
    #THANH: group by partner (get data the same from partner balance). Other will group by account
    group_by = fields.Selection([
        ('account', 'Account'),
        ('partner', 'Partner'),
        ], string='Group by', default='account')
    
    #THANH: lay luon but toan ket chuyen trong truong hop 421b cua BS (lay tu tk 4212, mac dinh la remove ket chuyen
    remove_regularization = fields.Boolean(string='Remove Regularization', default=True)
    
    account_cpp_ids = fields.Many2many('account.account', 'account_account_cpp_financial_report', 'report_line_id', 'account_id', 'Counterpart Accounts')
    account_cpp2_ids = fields.Many2many('account.account', 'account_account_cpp2_financial_report', 'report_line_id', 'account_id', 'Counterpart Accounts 2')
    
    account_report_ids = fields.Many2many('account.financial.report', 'account_financial_report_relation', 
                                          'report_id', 'report_relation_id', 'Report Values')
    journal_ids = fields.Many2many('account.journal', string='Journals')
    
class ReportAccountFinancial(models.TransientModel):
    _name = "report.account.financial"
    _description = "Report Account Financial"
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    @api.model
    def _get_compare_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        compare_fiscalyear = self.env['account.fiscalyear'].search([('date_stop', '<', fiscalyear.date_start)], limit=1, order="date_stop desc")
        return compare_fiscalyear or fiscalyear
    
    @api.model
    def _get_financial_id(self):
        default_report_type = self._context.get('default_report_type', False)
        if not default_report_type:
            return False
        return self.env['account.financial.report'].search([('report_type','=',default_report_type)], limit=1)
    
    @api.model
    def _get_report_name(self):
        report_name =  {'bs': 'B/S',
                        'pl': 'P/L',
                        'cashflow':'Direct Cashflow',
                        'cashflow_indirect':'Indirect Cashflow',
                        }
        
        default_report_type = self._context.get('default_report_type', False)
        return report_name.get(default_report_type,'')
    
    @api.model
    def _get_current_month(self):
        return time.strftime('%m')
            
    times = fields.Selection([
        ('dates','Date'),
        ('month', 'Month'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='years')
    
    #THANH: Current Period
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
    
    #THANH: Compare Period
    compare_fiscalyear_id = fields.Many2one('account.fiscalyear', string='Compare Fiscalyear', default=_get_compare_fiscalyear)
    compare_date_start = fields.Date(string='Compare Date start', default=time.strftime('%Y-%m-%d'))
    compare_date_end = fields.Date(string='Compare Date end', default=time.strftime('%Y-%m-%d'))
    compare_month = fields.Selection([
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
        ('12','12')], string='Compare Month', default=_get_current_month)
    compare_quarter = fields.Selection([
        ('1', '1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Compare Quarter', default='1')
    
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    #THANH: help to show tab second currency, should be readonly because it will call update to res.company again (will rase error for normal user)
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', string="2nd Company Currency", readonly=True)
    
    report_type = fields.Selection([
        ('bs', 'B/S'),
        ('pl','P/L'),
        ('cashflow','Direct Cashflow'),
        ('cashflow_indirect','Indirect Cashflow'),
        ('other','Others'),], string='Report Type')
    
    financial_report_ids = fields.One2many('account.financial.report.detail','report_id', string="Details", readonly=True)
    financial_report_2rd_ids = fields.One2many('account.financial.report.detail','report_id', string="2nd Details", readonly=True)
    
    name = fields.Char(string="Name", default=_get_report_name)
    financial_id = fields.Many2one('account.financial.report', string='Financial Report', 
                                   domain="[('parent_id', '=',False)]",
                                   required=False, default=_get_financial_id)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, 
                                   default=lambda self: self.env['account.journal'].search([]))
    
    @api.multi
    def load_journal(self):
        domain = []
        if self._context.get('journal_type', False):
            domain = [('internal_type','=',self._context['journal_type'])]
        self.journal_ids = self.env['account.journal'].search(domain)
        
    @api.multi
    def print_report(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_financial_report'}
    
    @api.onchange('quarter')
    def onchange_quarter(self):
        if self.times == 'quarter' and self.compare_fiscalyear_id:
            compare_quarter = int(self.quarter) > 1 and int(self.quarter) - 1 or 4
            self.compare_quarter = '%s' % compare_quarter
    
    @api.onchange('month')
    def onchange_month(self):
        if self.times == 'month' and self.compare_fiscalyear_id:
            compare_month = int(self.month) > 1 and int(self.month) - 1 or 12
            self.compare_month = '%%0%sd' % 2 % compare_month
    
    @api.onchange('compare_fiscalyear_id')
    def onchange_compare_fiscalyear_id(self):
        if not self.compare_fiscalyear_id:
            self.compare_month = False
            self.compare_quarter = False
            self.compare_date_start = False
            self.compare_date_end = False
            
    @api.multi
    def get_date(self, report):
        prior_sdate, prior_edate, start_date, end_date = False, False, False, False
        if report.times == 'dates':
            start_date = report.date_start
            end_date = report.date_end
            prior_sdate = report.compare_date_start
            prior_edate = report.compare_date_end
        else:
            year = report.fiscalyear_id.date_stop.split('-')[0]
            compare_year = report.compare_fiscalyear_id and report.compare_fiscalyear_id.date_stop.split('-')[0] or False
            
            if report.times == 'month':
                date = date_object(int(year), int(report.month), 01)
                start_date = year + '-%s-01'%(report.month)
                end_date = date + relativedelta(day=1, months=+1, days=-1)
                end_date = end_date.strftime('%Y-%m-%d')
                
                if report.compare_fiscalyear_id and report.compare_month:
                    prior_sdate = (datetime.strptime(start_date, DF) + relativedelta(months=-1)).strftime(DF)
                    prior_edate = (datetime.strptime(prior_sdate, DF) + relativedelta(months=+1, days=-1)).strftime(DF)
            
            if report.times == 'years':
                start_date = report.fiscalyear_id.date_start
                end_date   = report.fiscalyear_id.date_stop
                
                if report.compare_fiscalyear_id:
                    prior_sdate = report.compare_fiscalyear_id.date_start
                    prior_edate = report.compare_fiscalyear_id.date_stop
                
            if report.times == 'quarter':
                if report.quarter == '1':
                    start_date = year + '-01-01'
                    end_date = year + '-03-31'
                    if compare_year:
                        prior_sdate = compare_year + '-01-01'
                        prior_edate = compare_year + '-03-31'
                elif report.quarter == '2':
                    start_date = year + '-04-01'
                    end_date = year + '-06-30'
                elif report.quarter == '3':
                    start_date = year + '-07-01'
                    end_date = year + '-09-30'
                else:
                    start_date = year + '-10-01'
                    end_date = year + '-12-31'
                
                if compare_year and report.compare_quarter:
                    if report.compare_quarter == '1':
                        prior_sdate = compare_year + '-01-01'
                        prior_edate = compare_year + '-03-31'
                    elif report.compare_quarter == '2':
                        prior_sdate = compare_year + '-04-01'
                        prior_edate = compare_year + '-06-30'
                    elif report.compare_quarter == '3':
                        prior_sdate = compare_year + '-07-01'
                        prior_edate = compare_year + '-09-30'
                    else:
                        prior_sdate = compare_year + '-10-01'
                        prior_edate = compare_year + '-12-31'
        if report.fiscalyear_id == report.compare_fiscalyear_id:
            report.compare_fiscalyear_id = False
            prior_sdate, prior_edate = False, False
        return [prior_sdate,prior_edate,start_date,end_date]
    
    @api.multi
    def compute_report_last_line(self, report_line, dates, journal_ids):
        #THANH: Chỉ tính duy nhất chỉ tiêu con có Type là Accounts
        company_id = self.company_id.id
        second_currency_id = self.company_id.second_currency_id and self.company_id.second_currency_id.id or 0
        
        res = {'prior_value': 0.0,
                'curr_value': 0.0,
                'prior_value_2rd': 0.0,
                'curr_value_2rd': 0.0}
        
        #THANH: over write journal ids if report config has force to use another journals
        if report_line.journal_ids:
            journal_ids = [x.id for x in report_line.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
            
        account_ids = []
        if report_line.account_ids:
            for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report_line.account_ids])]):
                account_ids.append(acc.id)
                
        account_except_ids = []
        if report_line.account_except_ids:
            for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report_line.account_except_ids])]):
                account_except_ids.append(acc.id)
        
        if len(account_except_ids):
            account_ids = tuple(set(account_ids) - set(account_except_ids))
        
        cp_account_ids = []
        cp2_account_ids = []
        if len(report_line.account_cpp_ids):
            for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report_line.account_cpp_ids])]):
                cp_account_ids.append(acc.id)
            cp_account_ids = (','.join(map(str, cp_account_ids)))
            if len(report_line.account_cpp2_ids):
                for acc in self.env['account.account'].search([('parent_id', 'child_of', [x.id for x in report_line.account_cpp2_ids])]):
                    cp2_account_ids.append(acc.id)
                cp2_account_ids = (','.join(map(str, cp2_account_ids)))
        
        if len(account_ids):
            account_ids = (','.join(map(str, account_ids)))
            if dates[0] and dates[1]:
                for line in self.env['sql.financial.report'].get_line(dates[0], dates[1], account_ids, journal_ids,
                        second_currency_id, company_id, cp_account_ids, cp2_account_ids, report_line):
                    res['prior_value'] = report_line.sign * (line['balance'] or 0.0)
                    res['prior_value_2rd'] = report_line.sign * (line['balance_2rd'] or 0.0)
                    
            for line in self.env['sql.financial.report'].get_line(dates[2], dates[3], account_ids, journal_ids,
                        second_currency_id, company_id, cp_account_ids, cp2_account_ids, report_line):
                res['curr_value'] = report_line.sign * (line['balance'] or 0.0)
                res['curr_value_2rd'] = report_line.sign * (line['balance_2rd'] or 0.0)
        return res
    
    @api.multi
    def compute_report_line(self, report_line, dates, journal_ids):
        #THANH: Tính các chi tiểu con và chỉ tiêu tổng
        global computed_lines
        
        if not computed_lines:
            computed_lines = {}
            
        value = {'prior_value': 0.0,
                 'curr_value': 0.0,
                 'prior_value_2rd': 0.0,
                 'curr_value_2rd': 0.0}
        
        if report_line.type == 'accounts':
            if computed_lines.has_key(report_line.ma_so):
                value = {
                        'prior_value': computed_lines[report_line.ma_so]['prior_value'],
                        'curr_value': computed_lines[report_line.ma_so]['curr_value'],
                        'prior_value_2rd': computed_lines[report_line.ma_so]['prior_value_2rd'],
                        'curr_value_2rd': computed_lines[report_line.ma_so]['curr_value_2rd'],
                    }
            else:
                value = self.compute_report_last_line(report_line, dates, journal_ids)
                computed_lines.update({report_line.ma_so: {
                        'report_id':self.id,
                        'seq': report_line['sequence'],
                        'name': report_line['name'],
                        'ma_so': report_line['ma_so'],
                        'thuyet_minh': report_line['thuyet_minh'],
                        'financial_id': report_line['id'],
                        'prior_value': value['prior_value'],
                        'curr_value': value['curr_value'],
                        'prior_value_2rd': value['prior_value_2rd'],
                        'curr_value_2rd': value['curr_value_2rd'],
                        'com_currency_id': self.company_id.currency_id.id,
                        'second_currency_id': self.second_currency_id and self.second_currency_id.id or False,
                        'type': report_line.type
                    }})
            return value
        
        if report_line.type == 'account_report':
            for line in report_line.account_report_ids:
                result = self.compute_report_line(line, dates, journal_ids)
                value['prior_value'] += result['prior_value']
                value['curr_value'] += result['curr_value']
                value['prior_value_2rd'] += result['prior_value_2rd']
                value['curr_value_2rd'] += result['curr_value_2rd']
            return value
            
        if report_line.type == 'sum':
            for line in self.env['account.financial.report'].search([('id', 'child_of', report_line.id), ('type', '!=', 'sum')]):
                if computed_lines.has_key(line.ma_so):
                    value['prior_value'] += computed_lines[line.ma_so]['prior_value']
                    value['curr_value'] += computed_lines[line.ma_so]['curr_value']
                    value['prior_value_2rd'] += computed_lines[line.ma_so]['prior_value_2rd']
                    value['curr_value_2rd'] += computed_lines[line.ma_so]['curr_value_2rd']
                else:
                    result = self.compute_report_line(line, dates, journal_ids)
                    value['prior_value'] += result['prior_value']
                    value['curr_value'] += result['curr_value']
                    value['prior_value_2rd'] += result['prior_value_2rd']
                    value['curr_value_2rd'] += result['curr_value_2rd']
        return value
    
    @api.multi
    def print_report_profit_and_loss(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_profit_and_loss'}
        
    #THANH: Global variable => Để lưu trữ dữ liệu tính toán của từng chỉ tiêu
    computed_lines = {}
    @api.multi
    def load_data(self):
        global computed_lines
        report_type = self.env['account.financial.report']
        for report in self:
            computed_lines = {}
            
            dates = self.get_date(report)
            sql = '''
                DELETE from account_financial_report_detail where report_id = %s;
                SELECT id
                FROM  account_financial_report 
                WHERE report_id = %s
                ORDER BY sequence
            '''%(report.id,report.financial_id.id)
            self.env.cr.execute(sql)
            report_line_ids = [x[0] for x in self.env.cr.fetchall()]
            
            journal_ids = [x.id for x in report.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
        
            for line in report_type.browse(report_line_ids):
                #THANH: Khi chỉ tiêu tổng hiển thị trên báo cáo trước các chỉ tiểu con,
                #do đó chỉ tiêu con đã đc tính trong hàm compute_report_line()
                #chỉ cần kiểm trả trong dict computed_lines có key nghĩa là đã tính rồi và lấy ra thôi
                if line.ma_so and computed_lines.has_key(line.ma_so):
                    #THANH: Dùng trong báo cáo Balance Sheet, chỉ tiêu tổng hiển thị trước chỉ tiêu con
                    vals = computed_lines[line.ma_so]
                else:
                    value = self.compute_report_line(line, dates, journal_ids)
                    #THANH: Dùng trong báo cáo Profit Loss, chỉ tiêu tổng hiển thị sau chỉ tiêu con
                    vals = {'report_id':report.id,
                            'seq': line['sequence'],
                            'name': line['name'],
                            'ma_so': line['ma_so'],
                            'thuyet_minh': line['thuyet_minh'],
                            'financial_id': line['id'],
                            'prior_value': value['prior_value'],
                            'curr_value': value['curr_value'],
                            'prior_value_2rd': value['prior_value_2rd'],
                            'curr_value_2rd': value['curr_value_2rd'],
                            'com_currency_id': report.company_id.currency_id.id,
                            'second_currency_id': report.second_currency_id and report.second_currency_id.id or False,
                            'type': line.type
                        }
                    computed_lines.update({line.ma_so:vals})
                self.env['account.financial.report.detail'].create(vals)

class ReportAccountFinancialDetail(models.TransientModel):
    _name = "account.financial.report.detail"
    _description = "Report Account Financial Detail"
    
    
    financial_id = fields.Many2one('account.financial.report', string='Financial Report', required=False)
    report_id  = fields.Many2one('report.account.financial', string='Financial Report', ondelete='cascade', required=False)
    seq = fields.Integer(string ='Sequence')
    name = fields.Char(string ='Title')
    ma_so = fields.Char(string ='Code')
    type = fields.Char(string ='Type')#THANH: type = view will display as blue color
    thuyet_minh = fields.Char(string ='Description',size =256)
    
    prior_value = fields.Monetary(string ='Compare Period',currency_field='com_currency_id')
    curr_value = fields.Monetary(string ='Current Period',currency_field='com_currency_id')
    
    prior_value_2rd = fields.Monetary(string='Compare Period',currency_field='second_currency_id')
    curr_value_2rd = fields.Monetary(string='Current Period',currency_field='second_currency_id')
    
    com_currency_id = fields.Many2one('res.currency', string="Company Currency")
    second_currency_id = fields.Many2one('res.currency', string="Second Currency")
    