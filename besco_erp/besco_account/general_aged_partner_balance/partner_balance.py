# -*- coding: utf-8 -*-
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.misc import formatLang
import time

class account_account(models.Model):
    _inherit = "account.account"
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('filter_type'):
            #THANH: filter 331108, 131108 (doi ung cong no mua hang va ban hang)
            cp_account_ids = []
            product_category = self.env['ir.model'].search([('model','=','product.category')])
            if product_category:
                category_ids = self.env['product.category'].search([('property_account_expense_categ_id','!=',False)])
                cp_account_ids = len(category_ids) and [x.property_account_expense_categ_id.id for x in category_ids] or []
                
            if context['filter_type'] == 'both':
                type = ['receivable', 'payable']
            else:
                type = [context['filter_type']]
            args += ['|', ('type', 'in', type), ('id', 'in', cp_account_ids)]
        return super(account_account, self).search(args, offset, limit, order, count=count)
    
class report_partner_balance(models.TransientModel):
    _name = "report.partner.balance"
    @api.model 
    def create(self, vals): 
        result = super(report_partner_balance, self).create(vals) 
        return result
    
    
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
    
    type = fields.Selection([
              ('receivable','Receivable'),
              ('payable','Payable'),
              ('both','Receivable & Payable'),
              ], string='Account Type', required=True, default='both')
    partner_ids = fields.Many2many('res.partner', 'report_partner_balance_partner_rel', 'balance_id', 'partner_id', string='Partners')
    account_ids = fields.Many2many('account.account', 'report_partner_balance_rel', 'balance_id', 'account_id', string='Accounts')
        
    balance_lines = fields.One2many('report.partner.balance.line', 'balance_id', 'Balances', readonly=True)
    second_balance_lines = fields.One2many('report.partner.balance.line', 'balance_id', '2nd Balances', readonly=True)
    
    invoice_balance_lines = fields.One2many('report.partner.invoice', 'balance_id', 'Invoice Balances',readonly=True)
    ledger_detail_lines = fields.One2many('report.partner.ledger.detail', 'balance_id',string = "Ledger Details")
    
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    #THANH: help to show tab second currency, should be readonly because it will call update to res.company again (will rase error for normal user)
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', string="2nd Company Currency", readonly=True)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=lambda self: self.env['account.journal'].search([]))
    
    name = fields.Char(string="Name", default='Partner Balance')
    extend_payment = fields.Selection([
        ('none', 'All'),
        ('payment', 'Payment'),
        ('advance', 'Advance'),
    ],  string='Payment Mode', readonly=False, default='none')
    
    @api.multi
    def print_report_balance(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_partner_general_balance'}
    
    @api.multi
    def print_report_partner_invoice(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_partner_invoice_balance'}
    
    @api.multi
    def print_report_ledger_detail(self):
        return {'type' : 'ir.actions.report.xml', 'report_name' : 'report_partner_ledger_detail'}
    
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
    def load_general_balance(self):
        for report in self:
            cr = self.env.cr
            uid = self.env.user.id
            
            cr.execute('''
                BEGIN;
                DELETE FROM report_partner_balance_line WHERE balance_id=%s;
                COMMIT;
            '''%(report.id))
            
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            if not len(report.account_ids):
                #THANH: filter 331108, 131108 (doi ung cong no mua hang va ban hang)
#                 cp_account_ids = []
#                 product_category = self.env['ir.model'].search([('model','=','product.category')])
#                 if product_category:
#                     category_ids = self.env['product.category'].search([('property_account_expense_categ_id','!=',False)])
#                     cp_account_ids = len(category_ids) and [x.property_account_expense_categ_id.id for x in category_ids] or []
                
                domain = []
                if report.type == 'both':
                    type = ['receivable', 'payable']
                else:
                    type = [report.type]
                domain = [
#                             '|', 
                            ('type', 'in', type), 
#                           ('id', 'in', cp_account_ids)
                        ]
                account_ids = [x.id for x in self.env['account.account'].search(domain)]
            else:
                account_ids = [x.id for x in report.account_ids]
            
            company_id = report.company_id.id
            com_currency_id = report.company_id.currency_id.id
            second_currency_id = report.company_id.second_currency_id and report.company_id.second_currency_id.id or False
            
            #THANH: change second_currency_id into 0 when it is null to prevent sql condition
            if not second_currency_id:
                second_currency_id = 'null'
            
            if account_ids:
                for account_id in account_ids:
                    if len(report.partner_ids):
                        for partner_id in report.partner_ids:
                            sql ='''
                                INSERT INTO report_partner_balance_line(create_uid, create_date, write_uid, write_date,
                                    balance_id, partner_id, account_code, 
                                    begin_dr, begin_cr, period_dr, period_cr, end_dr, end_cr, 
                                    begin_dr_2nd, begin_cr_2nd, period_dr_2nd, period_cr_2nd, end_dr_2nd, end_cr_2nd, 
                                    com_currency_id, second_currency_id)
                                SELECT %s, current_timestamp, %s, current_timestamp,
                                    %s,fin.partner_id, 
                                    (select code from account_account where id=%s), 
                                    begin_dr,begin_cr,period_dr,period_cr,end_dr,end_cr, 
                                    begin_dr_2nd, begin_cr_2nd, period_dr_2nd, period_cr_2nd, end_dr_2nd, end_cr_2nd, 
                                    %s, %s
                                FROM fin_report_partner_balance('%s','%s',%s,%s,%s) fin
                            '''%(uid, uid, report.id, account_id, com_currency_id, second_currency_id, start_date, end_date, account_id, partner_id.id, company_id)
                            cr.execute(sql)
                    else:
                        sql ='''
                            INSERT INTO report_partner_balance_line(create_uid, create_date, write_uid, write_date,
                                balance_id, partner_id, account_code, 
                                begin_dr, begin_cr, period_dr, period_cr, end_dr, end_cr, 
                                begin_dr_2nd, begin_cr_2nd, period_dr_2nd, period_cr_2nd, end_dr_2nd, end_cr_2nd, 
                                com_currency_id, second_currency_id)
                            SELECT %s, current_timestamp, %s, current_timestamp,
                                %s, fin.partner_id, 
                                (select code from account_account where id=%s), 
                                begin_dr,begin_cr,period_dr,period_cr,end_dr,end_cr, 
                                begin_dr_2nd, begin_cr_2nd, period_dr_2nd, period_cr_2nd, end_dr_2nd, end_cr_2nd, 
                                %s, %s
                            FROM fin_report_partner_balance('%s','%s',%s,%s,%s) fin
                        '''%(uid, uid, report.id, account_id, com_currency_id, second_currency_id, start_date, end_date, account_id, 0, company_id)
                        cr.execute(sql)
        
    @api.multi
    def load_partner_invoice(self):
        for report in self:
            cr = self.env.cr
            
            cr.execute('''
                BEGIN;
                
                DELETE FROM report_partner_customer_invoice_rel where report_id=%s;
                DELETE FROM report_partner_vendor_invoice_rel where report_id=%s;
                DELETE FROM report_partner_invoice WHERE balance_id=%s;
                
                COMMIT;
            '''%(report.id, report.id, report.id))
    
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            where_invoice_date = ''
            where_invoice_date += ''' and inv.date_invoice <= '%s'
                --and inv.state not in ('')
            '''%(end_date)
            
            where_invoice_type = ''
            if report.type == 'receivable':
                where_invoice_type = " and inv.type='out_invoice'"
            if report.type == 'payable':
                where_invoice_type = " and inv.type='in_invoice'"
            if report.type == 'both':
                where_invoice_type = " and inv.type in ('in_invoice', 'out_invoice')"
                
            if not len(self.partner_ids):
                sql = '''
                    SELECT distinct partner_id
                    FROM account_invoice inv
                    WHERE 1=1 and state not in ('draft','paid','cancel')
                '''
                sql += where_invoice_date
                sql += where_invoice_type
                cr.execute(sql)
                partner_ids = [x[0] for x in cr.fetchall()]
            else:
                partner_ids = [x.id for x in self.partner_ids]
                
            for partner_id in partner_ids:
                balance_line_id = self.env['report.partner.invoice'].create({'balance_id': self.id, 'partner_id': partner_id}).id
                
                if report.type in ['receivable', 'both']:
                    #Thanh: Insert Customer Invoices
                    sql = '''
                        INSERT INTO report_partner_customer_invoice_rel(report_id, invoice_id)
                        SELECT %(report_id)s, foo.invoice_id
                        FROM
                            (
                                SELECT inv.id invoice_id
                                FROM account_invoice inv
                                WHERE inv.partner_id = %(partner_id)s AND inv.type='out_invoice' 
                                    %(where_invoice_date)s and inv.state not in ('draft','paid','cancel')
                            ) foo
                    '''%({'partner_id': partner_id,
                          'where_invoice_date': where_invoice_date,
                          'report_id': balance_line_id})
                    cr.execute(sql)
                
                if report.type in ['payable', 'both']:
                    #Thanh: Insert Supplier Invoices
                    sql = '''
                        INSERT INTO report_partner_vendor_invoice_rel(report_id, invoice_id)
                        SELECT %(report_id)s, foo.invoice_id
                        FROM
                            (
                                SELECT inv.id invoice_id
                                FROM account_invoice inv
                                WHERE inv.partner_id = %(partner_id)s AND inv.type='in_invoice' 
                                    %(where_invoice_date)s and inv.state not in ('draft','paid','cancel')
                            ) foo
                    '''%({'partner_id': partner_id,
                          'where_invoice_date': where_invoice_date,
                          'report_id': balance_line_id})
                    cr.execute(sql)
        
    @api.multi
    def load_ledger_detail(self):
        for report in self:
#             if not report.partner_ids:
#                 raise UserError(_('Please select Partner first.'))
                
            cr = self.env.cr
            uid = self.env.user.id
            
            cr.execute('''
                BEGIN;
                DELETE FROM report_partner_ledger_detail WHERE balance_id=%s;
                COMMIT;
            '''%(report.id))
            
            start_date, end_date = self.get_period(report)
            report.date_start = start_date
            report.date_end = end_date
            
            if not len(report.account_ids):
                #THANH: filter 331108, 131108 (doi ung cong no mua hang va ban hang)
                cp_account_ids = []
                product_category = self.env['ir.model'].search([('model','=','product.category')])
                if product_category:
                    category_ids = self.env['product.category'].search([('property_account_expense_categ_id','!=',False)])
                    cp_account_ids = len(category_ids) and [x.property_account_expense_categ_id.id for x in category_ids] or []
                
                domain = []
                if report.type == 'both':
                    type = ['receivable', 'payable']
                else:
                    type = [report.type]
                domain = ['|', ('type', 'in', type), ('id', 'in', cp_account_ids)]
                account_ids = [x.id for x in self.env['account.account'].search(domain)]
            else:
                account_ids = [x.id for x in report.account_ids]
                
            account_ids = (','.join(map(str, account_ids)))
            
            company_id = report.company_id.id
            com_currency_id = report.company_id.currency_id.id
            second_currency_id = report.company_id.second_currency_id and report.company_id.second_currency_id.id or False
            
            #THANH: change second_currency_id into 0 when it is null to prevent sql condition
            if not second_currency_id:
                second_currency_id = 'null'
            
            partner_ids = [x.id for x in report.partner_ids]
            if not len(partner_ids):
                partner_ids.append('null')
            journal_ids = [x.id for x in report.journal_ids]
            journal_ids = (','.join(map(str, journal_ids)))
            #THANH: Insert table details
            self.env['sql.partner.ledger.detail'].get_line(start_date, end_date, journal_ids, account_ids, True, partner_ids, company_id, second_currency_id, report = report)
            
class report_partner_balance_line(models.TransientModel):
    _name ="report.partner.balance.line"
    _order = "partner_id,account_code"
    
    balance_id = fields.Many2one('report.partner.balance', string='Related Partner Balance')
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_code = fields.Char('Account Code')
    
    begin_dr = fields.Monetary(string='Open Dr', currency_field='com_currency_id')
    begin_cr = fields.Monetary(string='Open Cr', currency_field='com_currency_id')
    period_dr = fields.Monetary(string='Period Dr', currency_field='com_currency_id')
    period_cr = fields.Monetary(string='Period Cr', currency_field='com_currency_id')
    end_dr = fields.Monetary(string='Balance Dr', currency_field='com_currency_id')
    end_cr = fields.Monetary(string='Balance Cr', currency_field='com_currency_id')
    
    begin_dr_2nd = fields.Monetary(string='Open Dr', currency_field='second_currency_id')
    begin_cr_2nd = fields.Monetary(string='Open Cr', currency_field='second_currency_id')
    period_dr_2nd = fields.Monetary(string='Period Dr', currency_field='second_currency_id')
    period_cr_2nd = fields.Monetary(string='Period Cr', currency_field='second_currency_id')
    end_dr_2nd = fields.Monetary(string='Balance Dr', currency_field='second_currency_id')
    end_cr_2nd = fields.Monetary(string='Balance Cr', currency_field='second_currency_id')
    
    second_currency_id = fields.Many2one('res.currency', string="Second Currency")
    com_currency_id = fields.Many2one('res.currency', string="Company Currency")

class report_partner_invoice(models.TransientModel):
    _name ="report.partner.invoice"
    
    @api.one
    def _get_due_amount(self):
        self.due_amount = 0.0
        self.due_30_day = 0.0
        self.due_60_day = 0.0
        self.due_90_day = 0.0
        self.due_120_day = 0.0
        today = datetime.today()
        
        sign = 1
        if self.balance_id.type == 'payable':
            sign = -1
        if self.partner_id.id == 73:
            a = 1
            
        for invoice in self.customer_invoice_line:
            self.due_amount += invoice.residual_signed
            self.invoice_amount += invoice.amount_total_company_signed
            self.paid_amount += (invoice.amount_total_company_signed - invoice.residual_signed)
            
            date_invoice = invoice.date_invoice or datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if not invoice.date_invoice:
                date_invoice = str(datetime.today()).split(' ')[0]
            date_invoice = datetime.strptime(date_invoice, DEFAULT_SERVER_DATE_FORMAT)
            diff = today - date_invoice
            if diff.days > 30 and diff.days <= 60:
                self.due_30_day += invoice.residual_signed
            if diff.days > 60 and diff.days <= 90:
                self.due_60_day += invoice.residual_signed
            if diff.days > 90 and diff.days <= 120:
                self.due_90_day += invoice.residual_signed
            if diff.days > 120:
                self.due_120_day += invoice.residual_signed
        
        for invoice in self.vendor_invoice_line:
            self.due_amount -= invoice.residual_signed
            self.invoice_amount -= invoice.amount_total_company_signed
            self.paid_amount -= (invoice.amount_total_company_signed - invoice.residual_signed)
            
            date_invoice = invoice.date_invoice or datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if not invoice.date_invoice:
                date_invoice = str(datetime.today()).split(' ')[0]
            date_invoice = datetime.strptime(date_invoice, DEFAULT_SERVER_DATE_FORMAT)
            diff = today - date_invoice
            if diff.days > 30 and diff.days <= 60:
                self.due_30_day -= invoice.residual_signed
            if diff.days > 60 and diff.days <= 90:
                self.due_60_day -= invoice.residual_signed
            if diff.days > 90 and diff.days <= 120:
                self.due_90_day -= invoice.residual_signed
            if diff.days > 120:
                self.due_120_day -= invoice.residual_signed
        
        self.due_amount *= sign
        self.invoice_amount *= sign
        self.paid_amount *= sign
        self.due_30_day *= sign
        self.due_60_day *= sign
        self.due_90_day *= sign
        self.due_120_day *= sign
    
    balance_id = fields.Many2one('report.partner.balance', string='Related Partner Balance')
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    due_amount = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Due Amount', readonly=True)
    invoice_amount = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Due Amount', readonly=True)
    paid_amount = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Due Amount', readonly=True)
    
    due_30_day = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Over 30 Days', readonly=True)
    due_60_day = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Over 60 Days', readonly=True)
    due_90_day = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Over 90 Days', readonly=True)
    due_120_day = fields.Monetary(compute='_get_due_amount', currency_field='com_currency_id', string='Over 120 Days', readonly=True)
        
    customer_invoice_line = fields.Many2many('account.invoice', 'report_partner_customer_invoice_rel', 'report_id', 'invoice_id', string='Customer Invoices', readonly=True)
    vendor_invoice_line = fields.Many2many('account.invoice', 'report_partner_vendor_invoice_rel', 'report_id', 'invoice_id', string='Vendor Invoices', readonly=True)
    com_currency_id = fields.Many2one('res.currency', string="Company Currency")
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.one
    def _get_invoice_amount(self):
        self.over_30_day = False
        self.over_60_day = False
        self.over_90_day = False
        self.over_120_day = False
            
        date_invoice = self.date_invoice or False
        if not date_invoice:
            date_invoice = str(datetime.today()).split(' ')[0]
        today = datetime.today()
        date_invoice = datetime.strptime(date_invoice, DEFAULT_SERVER_DATE_FORMAT)
        diff = today - date_invoice
        if diff.days > 30 and diff.days <= 60:
            self.over_30_day = True
        if diff.days > 60 and diff.days <= 90:
            self.over_60_day = True
        if diff.days > 90 and diff.days <= 120:
            self.over_90_day = True
        if diff.days > 120:
            self.over_120_day = True
    
    #THANH: Show in balance report
    over_30_day = fields.Boolean(compute='_get_invoice_amount', string='Over 30 Days', readonly=True)
    over_60_day = fields.Boolean(compute='_get_invoice_amount', string='Over 60 Days', readonly=True)
    over_90_day = fields.Boolean(compute='_get_invoice_amount', string='Over 90 Days', readonly=True)
    over_120_day = fields.Boolean(compute='_get_invoice_amount', string='Over 120 Days', readonly=True)

class report_partner_ledger_detail(models.TransientModel):
    _name = "report.partner.ledger.detail"
    _description = "Partner Ledger Detail"
    _order = "id,seq"
    
    balance_id = fields.Many2one('report.partner.balance')
    seq = fields.Integer(string="Sequence")
    
    gl_date = fields.Date(string="GL Date")
    doc_date = fields.Date(string="Doc Date")
    date_due = fields.Date(string="Due Date")
    doc_no = fields.Char(string="Doc No", size=64)
    description = fields.Char(string="Description")
    acc_code = fields.Char(string="Acc")
    cp_acc_code = fields.Char(string="CP Acc")
    
    debit = fields.Monetary(string="Dr",currency_field='com_currency_id')
    credit = fields.Monetary(string="Cr",currency_field='com_currency_id')
    
    debit_second = fields.Monetary(string="2nd Dr",currency_field='second_currency_id')
    credit_second = fields.Monetary(string="2nd Cr",currency_field='second_currency_id')
    second_ex_rate = fields.Monetary(string="FX",currency_field='second_currency_id')
    
    partner_id = fields.Many2one('res.partner', string="Partner")
    
    com_currency_id = fields.Many2one('res.currency', string="Company Currency")
    second_currency_id = fields.Many2one('res.currency', string="Second Currency")