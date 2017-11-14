# -*- coding: utf-8 -*-
import  time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.times = False
        self.start_date = False
        self.end_date = False
        self.company = False
        self.company_name = False
        self.company_address = False
        self.vat = False
        self.cr = cr
        self.uid = uid
        self.shop_ids = False
        self.tax_ids =[]
        self.journal_ids = []
        
        self.com_curr = False
        self.second_curr = False
        
        self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax = 0.0, 0.0, 0.0, 0.0
        self.curr_amount_untaxed_0, self.curr_amount_tax_0, self.second_amount_untaxed_0, self.second_amount_tax_0 = 0.0, 0.0, 0.0, 0.0
        self.curr_amount_untaxed_5, self.curr_amount_tax_5, self.second_amount_untaxed_5, self.second_amount_tax_5 = 0.0, 0.0, 0.0, 0.0
        self.curr_amount_untaxed_10, self.curr_amount_tax_10, self.second_amount_untaxed_10, self.second_amount_tax_10 = 0.0, 0.0, 0.0, 0.0
        self.curr_amount_untaxed_20, self.curr_amount_tax_20, self.second_amount_untaxed_20, self.second_amount_tax_20 = 0.0, 0.0, 0.0, 0.0
        
        self.curr_total_tax_22, self.second_total_tax_22 = 0.0, 0.0
        self.curr_total_tax_25, self.second_total_tax_25 = 0.0, 0.0
        self.curr_total_tax_35, self.second_total_tax_35 = 0.0, 0.0
        self.curr_total_tax_36, self.second_total_tax_36 = 0.0, 0.0
        self.curr_total_tax_41, self.second_total_tax_41 = 0.0, 0.0
        self.curr_total_tax_42, self.second_total_tax_42 = 0.0, 0.0
        self.curr_total_tax_43, self.second_total_tax_43 = 0.0, 0.0
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            'get_total_amt_tax_vat_in':self.get_total_amt_tax_vat_in,
            'get_total_amt_vat_in':self.get_total_amt_vat_in,
            'get_month': self.get_month,
            'get_quater': self.get_quater,
            'get_year': self.get_year,
            'get_com_curr': self.get_com_curr,
            'get_second_curr': self.get_second_curr,
            'get_total_amt_vat_out':self.get_total_amt_vat_out,
            'get_total_amt_tax_vat_out':self.get_total_amt_tax_vat_out,
            'get_total_amt_vat_outs':self.get_total_amt_vat_outs,
            'get_total_amt_tax_vat_outs':self.get_total_amt_tax_vat_outs,
            'get_curr_amount_10':self.get_curr_amount_10,
            'get_curr_amount_20':self.get_curr_amount_20,
            'get_curr_amount_5':self.get_curr_amount_5,
            'get_curr_amount_0':self.get_curr_amount_0,
            'get_curr_vat_amount_10':self.get_curr_vat_amount_10,
            'get_curr_vat_amount_5': self.get_curr_vat_amount_5,
            'get_amt_vat_22': self.get_amt_vat_22,
            'get_aml_27': self.get_aml_27,
            'get_aml_tax_27': self.get_aml_tax_27,
            
            'get_amt_vat_36': self.get_amt_vat_36,
            'get_total_amt_tax_41': self.get_total_amt_tax_41,
            'get_total_amt_tax_43': self.get_total_amt_tax_43,
            
            'get_2nd_decimal_places': self.get_2nd_decimal_places,
        })
    
    def format_amount(self, amount):
        lang_ids = self.pool.get('res.lang').search(self.cr, self.uid, [])
        string = self.pool.get('res.lang').format(self.cr, self.uid, [lang_ids[0]], '%d', amount, grouping=True, monetary=True)
        return string
    
    def get_month(self):
        if not self.start_date:
            self.get_header()
            
        start_date = datetime.strptime(self.start_date, DATE_FORMAT)
        m = start_date.strftime('%m')
        return m
    
    def get_quater(self):
        start_date = datetime.strptime(self.start_date, DATE_FORMAT)
        m = start_date.strftime('%m')
        quarter = (int(m) -1) / 3 + 1
        return str(quarter)
    
    def get_year(self):
        start_date = datetime.strptime(self.start_date, DATE_FORMAT)
        y = start_date.strftime('%y')
        return y
    
    def get_company(self, company_id):
        if company_id:
            company_obj = self.pool.get('res.company').browse(self.cr, self.uid,company_id)
            self.company_name = company_obj.name or ''
            self.company_address = company_obj.street or ''
            self.vat = company_obj.vat or ''
            self.com_curr = company_obj.currency_id
            self.second_curr = company_obj.second_currency_id or ''
            self.company = company_obj
        return True
    
    def get_second_curr(self):
        return self.second_curr
    
    def get_com_curr(self):
        return self.com_curr
    
    def get_2nd_decimal_places(self):
        if self.second_curr:
            return self.second_curr.round_decimal_places
        return 2
    
    def get_company_name(self):
        self.get_header()
        return self.company_name
    
    def get_company_address(self):
        return self.company_address    
    
    def get_company_vat(self):
        return self.vat    
    
    def get_id(self,get_id):
        wizard_data = self.localcontext['data']['form']
        period_id = wizard_data[get_id][0] or wizard_data[get_id][0] or False
        if not period_id:
            return 1
        else:
            return period_id
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.times = wizard_data['times']
        #Get company info
        self.company_id = wizard_data['company_id'] and wizard_data['company_id'][0] or False
        self.get_company(self.company_id)
        self.tax_ids = wizard_data['tax_ids']
        self.ded_vat_account_ids = wizard_data['ded_vat_account_ids']
        self.show_invoice = wizard_data['show_invoice']
        self.times = wizard_data['times']
        self.fiscalyear_id = wizard_data['fiscalyear_id']
        self.month = wizard_data['month'], 
        self.start_date = wizard_data['start_date']
        self.end_date   = wizard_data['end_date']
        self.journal_ids = wizard_data['journal_ids']
        
    def get_quarter_date(self,year,quarter):
        self.start_date = False
        self.end_date  = False
        if quarter == '1':
            self.start_date = '''%s-01-01'''%(year)
            self.end_date = year + '-03-31'
        elif quarter == '2':
            self.start_date = year+'-04-01'
            self.end_date =year+'-06-30'
        elif quarter == '3':
            self.start_date = year+'-07-01'
            self.end_date = year+'-09-30'
        else:
            self.start_date = year+'-10-01'
            self.end_date = year+'-12-31'
            
    def get_start_date(self):
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    def get_vietname_date(self, date):
        if not date:
            return ''
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_aml_27(self,curr):
        if curr == 2:
            return self.second_amount_untaxed_0+  self.second_amount_untaxed_5 + self.second_amount_untaxed_10
        else:
            return self.curr_amount_untaxed_0+  self.curr_amount_untaxed_5 + self.curr_amount_untaxed_10 + self.curr_amount_tax_0 + self.curr_amount_tax_5 + + self.curr_amount_tax_10
    
    def get_aml_tax_27(self,curr):
        if curr == 2:
            self.second_total_tax_35 = self.second_amount_tax_0 + self.second_amount_tax_5 + + self.second_amount_tax_10
            return self.second_total_tax_35 #THANH: chi tieu 27 = 35
        else:
            self.curr_total_tax_35 = self.curr_amount_tax_0 + self.curr_amount_tax_5 + + self.curr_amount_tax_10
            return self.curr_total_tax_35 #THANH: chi tieu 27 = 35
    
    def get_total_amt_vat_in(self, curr):
        self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax = self.compute_vatin_lines()
        if curr == 1:
            return self.curr_amount_untaxed #+ self.curr_amount_tax
        else:
            return self.second_amount_untaxed #+ self.second_amount_tax
        
    def get_total_amt_tax_vat_in(self, curr):
        if curr == 1:
            self.curr_total_tax_25 = self.curr_amount_tax
            return self.curr_total_tax_25
        else:
            self.second_total_tax_25 = self.second_amount_tax
            return self.second_total_tax_25
        
    def compute_vatin_lines(self):
        self.curr_amount_untaxed = 0
        self.curr_amount_tax = 0
        self.second_amount_untaxed = 0
        self.second_amount_tax = 0
        
        sql='''
            SELECT * from (
                SELECT 
                    CASE WHEN ai.type ='in_invoice' then       
                    ai.amount_untaxed 
                    ELSE 
                    ai.amount_untaxed * (-1) end amount_untaxed,  
                    
                    CASE WHEN ai.type ='in_invoice' then    
                     ai.amount_tax 
                     else
                     ai.amount_tax * (-1) end amount_tax,
                    
                    ai.currency_id,
                    ai.date_invoice date_invoice
                                  
                FROM account_invoice ai
                        left join res_currency rc on rc.id = ai.currency_id
                    join res_partner rp on rp.id = ai.partner_id
                WHERE  ai.state in ('open','paid')
                       and ai.date_invoice between '%s' and '%s'
                       and ai.type in ('in_invoice','in_refund')
                       and ai.journal_id in (%s)
                       --and ai.reference is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                       and ai.amount_tax != 0.0 --THANH: do not show invoice with amount_tax = 0.0
                       
                UNION ALL 
                
                SELECT 
                    api.sub_total amount_untaxed,
                    CASE WHEN api.tax_correction != 0.0 then       
                        api.tax_correction
                    ELSE 
                        api.tax_amount end amount_tax,
                    api.currency_id,
                    ap.payment_date date_invoice
                                  
                FROM account_payment_invoice api 
                    join account_payment ap on ap.id = api.line_id
                    left join res_currency rc on rc.id = api.currency_id
                    left join res_partner rp on rp.id = api.partner_id
                WHERE ap.state in ('posted')
                    and ap.payment_type = 'outbound'
                    and ap.payment_date between '%s' and '%s'
                    and api.journal_id in (%s)
                    --and api.number is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                    and (api.tax_amount != 0.0 or api.tax_correction != 0.0) --THANH: do not show invoice with amount_tax = 0.0
                )x
        '''%(self.start_date, self.end_date, self.journal_ids,
             self.start_date, self.end_date, self.journal_ids)
        currency_obj = self.pool.get('res.currency')
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            #THANH: compute 2nd currency
            curr_amount_untaxed = line['amount_untaxed']
            curr_amount_tax = line['amount_tax']
            second_amount_untaxed = line['amount_untaxed']
            second_amount_tax = line['amount_tax']
            
            if line['currency_id']:
                currency = currency_obj.browse(self.cr, self.uid, line['currency_id'])
                if line['currency_id'] != self.company.currency_id.id:
                    curr_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.currency_id)
                    curr_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.currency_id)
                    
                if self.company.second_currency_id and line['currency_id'] != self.company.second_currency_id.id:
                    second_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.second_currency_id)
                    second_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.second_currency_id)
                    
            self.curr_amount_untaxed += curr_amount_untaxed
            self.curr_amount_tax += curr_amount_tax
            self.second_amount_untaxed += second_amount_untaxed
            self.second_amount_tax += second_amount_tax
        return self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax
    
    #THANH: VAT OUT
    def get_total_amt_vat_out(self, curr,vat = None):
        self.curr_amount_untaxed_20, self.curr_amount_tax_20, self.second_amount_untaxed_20, self.second_amount_tax_20 =0,0,0,0
        self.get_total_amt_vat_outs(curr)
        self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax = self.compute_vatout_lines()
        if curr == 1:
            return self.curr_amount_untaxed #+ self.curr_amount_tax
        else:
            return self.second_amount_untaxed #+ self.second_amount_tax
        
    def get_total_amt_tax_vat_out(self, curr):
        if curr == 1:
            return self.curr_amount_tax
        else:
            return self.second_amount_tax
    
    def get_curr_amount_20(self,curr):
        if curr ==1:
            return self.curr_amount_untaxed_20 #+ self.curr_amount_tax_20
        else:
            return self.second_amount_untaxed_20 #+ self.second_amount_tax_20
    
    def get_curr_amount_0(self,curr):
        if curr ==1:
            return self.curr_amount_untaxed_0 #+ self.curr_amount_tax_0
        else:
            return self.second_amount_untaxed_0 #+ self.second_amount_tax_0
    
    def get_curr_amount_5(self,curr):
        if curr ==1:
            return self.curr_amount_untaxed_5 #+ self.curr_amount_tax_5
        else:
            return self.second_amount_untaxed_5 #+ self.second_amount_tax_5
    
    def get_curr_amount_10(self,curr):
        if curr ==1:
            return self.curr_amount_untaxed_10 #+ self.curr_amount_tax_10
        else:
            return self.second_amount_untaxed_10 #+ self.second_amount_tax_10
        
    def get_curr_vat_amount_5(self,curr):
        if curr ==1:
            return self.curr_amount_tax_5
        else:
            return self.second_amount_tax_5
        
    def get_curr_vat_amount_10(self,curr):
        if curr ==1:
            return self.curr_amount_tax_10
        else:
            return self.second_amount_tax_10
        
    def get_total_amt_vat_outs(self,curr):
        total_vn = 0.0
        total_usd = 0.0
        self.curr_amount_untaxed_0, self.curr_amount_tax_0, self.second_amount_untaxed_0, self.second_amount_tax_0 = 0,0,0,0
        self.curr_amount_untaxed_5, self.curr_amount_tax_5, self.second_amount_untaxed_5, self.second_amount_tax_5 = 0,0,0,0
        self.curr_amount_untaxed_10, self.curr_amount_tax_10, self.second_amount_untaxed_10, self.second_amount_tax_10 = 0,0,0,0
        self.curr_amount_untaxed_20, self.curr_amount_tax_20, self.second_amount_untaxed_20, self.second_amount_tax_20 = 0,0,0,0
        for line in (0,5,10,20):
            if line ==20:
                self.curr_amount_untaxed_20, self.curr_amount_tax_20, self.second_amount_untaxed_20, self.second_amount_tax_20 = self.compute_vatout_lines()
                if curr == 1:
                    total_usd += self.curr_amount_untaxed_20 #+  self.curr_amount_tax_20 
                else:
                    total_vn += self.second_amount_untaxed_20 #+  self.second_amount_tax_20 
            elif line== 0:
                self.curr_amount_untaxed_0, self.curr_amount_tax_0, self.second_amount_untaxed_0, self.second_amount_tax_0 = self.compute_vatout_lines(line)
                if curr == 1:
                    total_usd += self.curr_amount_untaxed_0 #+  self.curr_amount_tax_0 
                else:
                    total_vn += self.second_amount_untaxed_0 #+  self.second_amount_tax_0 
            elif line== 5:
                self.curr_amount_untaxed_5, self.curr_amount_tax_5, self.second_amount_untaxed_5, self.second_amount_tax_5 = self.compute_vatout_lines(line)
                if curr == 1:
                    total_usd += self.curr_amount_untaxed_5 #+  self.curr_amount_tax_5 
                else:
                    total_vn += self.second_amount_untaxed_5 #+  self.second_amount_tax_5 
            else:
                self.curr_amount_untaxed_10, self.curr_amount_tax_10, self.second_amount_untaxed_10, self.second_amount_tax_10 = self.compute_vatout_lines(line)
                if curr == 1:
                    total_usd += self.curr_amount_untaxed_10 #+  self.curr_amount_tax_10
                else:
                    total_vn += self.second_amount_untaxed_10 #+  self.second_amount_tax_10
        
        if curr == 1:
            return total_usd
        else:
            return total_vn
    
    def get_total_amt_tax_vat_outs(self,curr):
        if curr == 1:
            return self.curr_total_tax_35
        else:
            return self.second_total_tax_35
        
    def compute_vatout_lines(self, tax=None):
        self.curr_amount_untaxed = 0
        self.curr_amount_tax = 0
        self.second_amount_untaxed = 0
        self.second_amount_tax = 0
        
        sql = ''
        if tax != None:
            result = self.pool.get('account.tax').search(self.cr, self.uid, [('amount','=',tax),('type_tax_use','=','sale'),('transaction_type','=','none')])
            report_tax_id = result and result[0] or False
            from_invoice = " join account_invoice_tax ait on ai.id = ait.invoice_id and ait.tax_id = %s"%(report_tax_id)
            from_voucher = " join account_payment_invoice_account_tax_rel api_at_rel on api_at_rel.account_payment_invoice_id = api.id and api_at_rel.account_tax_id = %s"%(report_tax_id)
            sql = '''
                SELECT * from (
                    SELECT 
                        ai.date_invoice,
                        CASE WHEN ai.type ='out_invoice' then       
                        ai.amount_untaxed 
                        ELSE 
                        ai.amount_untaxed * (-1) end amount_untaxed,  
                        CASE WHEN ai.type ='out_invoice' then    
                         ai.amount_tax 
                         else
                         ai.amount_tax * (-1) end amount_tax,
                        ai.currency_id
                    FROM account_invoice ai
                            left join res_currency rc on rc.id = ai.currency_id
                        %s
                        join res_partner rp on rp.id = ai.partner_id
                    WHERE  ai.state in ('open','paid')
                           and ai.date_invoice between '%s' and '%s'
                           and ai.type in ('out_invoice','out_refund')
                           and ai.journal_id in (%s)
                           --and ai.reference is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                    UNION ALL 
                    SELECT 
                        api.date date_invoice,
                        api.sub_total amount_untaxed,
                        CASE WHEN api.tax_correction != 0.0 then       
                            api.tax_correction
                        ELSE 
                            api.tax_amount end amount_tax,
                        api.currency_id
                    FROM account_payment_invoice api 
                        %s
                        join account_payment ap on ap.id = api.line_id
                        left join res_currency rc on rc.id = api.currency_id
                        left join res_partner rp on rp.id = api.partner_id
                    WHERE ap.state in ('posted')
                        and ap.payment_type = 'outbound'
                        and ap.payment_date between '%s' and '%s'
                        and api.journal_id in (%s)
                        --and api.number is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                    )x
            '''%(from_invoice, self.start_date, self.end_date, self.journal_ids,
                 from_voucher, self.start_date, self.end_date, self.journal_ids)
        currency_obj = self.pool.get('res.currency')
        if len(sql):
            self.cr.execute(sql)
            sql_result = self.cr.dictfetchall()
            for line in sql_result:
                #THANH: compute 2nd currency
                curr_amount_untaxed = line['amount_untaxed']
                curr_amount_tax = line['amount_tax']
                second_amount_untaxed = line['amount_untaxed']
                second_amount_tax = line['amount_tax']
                
                if line['currency_id']:
                    currency = currency_obj.browse(self.cr, self.uid, line['currency_id'])
                    if line['currency_id'] != self.company.currency_id.id:
                        curr_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.currency_id)
                        curr_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.currency_id)
                        
                    if self.company.second_currency_id and line['currency_id'] != self.company.second_currency_id.id:
                        second_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.second_currency_id)
                        second_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.second_currency_id)
                    
                self.curr_amount_untaxed += curr_amount_untaxed
                self.curr_amount_tax += curr_amount_tax
                self.second_amount_untaxed += second_amount_untaxed
                self.second_amount_tax += second_amount_tax
        return self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax
    
    def get_amt_vat_22(self, curr):
        if not self.company_id:
            self.get_header()
        
        if not self.curr_total_tax_22:
            account_ids = self.ded_vat_account_ids
            if len(account_ids):
                vals = {'times': self.times, 'fiscalyear_id': self.fiscalyear_id[0], 'month': self.month[0], 
                       'date_start': self.start_date, 
                       'date_end': self.end_date, 
                       'company_id': self.company_id, 
                       'account_ids': [[6, False, account_ids]], 
                       'quarter': '1', 
                       'type': 'none', 
                       'extend_payment': 'none'}
                new_id = self.pool.get('report.account.ledger').create(self.cr, 1, vals)
                balance = self.pool.get('report.account.ledger').browse(self.cr, 1, new_id)
                balance.load_data()
                for line in balance.general_ledger_ids:
                    if line.description == u'Số dư đầu kỳ':
                        self.curr_total_tax_22 = line.debit or line.credit
                        self.second_total_tax_22 = line.debit_second or line.credit_second
                    
        if curr == 1:
            return self.curr_total_tax_22
        else:
            return self.second_total_tax_22
    
    def get_amt_vat_36(self, curr):
        if curr == 1:
            self.curr_total_tax_36 = self.curr_total_tax_35 - self.curr_total_tax_25
            return self.curr_total_tax_36
        else:
            self.second_total_tax_36 = self.second_total_tax_35 - self.second_total_tax_25
            return self.second_total_tax_36
    
    def get_total_amt_tax_41(self, curr):
        if curr == 1:
            self.curr_total_tax_41 = self.curr_total_tax_36 - self.curr_total_tax_22
            return abs(self.curr_total_tax_41)
        else:
            self.second_total_tax_41 = self.second_total_tax_36 - self.second_total_tax_22
            return abs(self.second_total_tax_41)
    
    def get_total_amt_tax_43(self, curr):
        if curr == 1:
            return abs(self.curr_total_tax_41 - self.curr_total_tax_42)
        else:
            return abs(self.second_total_tax_41 - self.second_total_tax_42)
        
