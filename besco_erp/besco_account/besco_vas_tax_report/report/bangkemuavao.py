# -*- coding: utf-8 -*-
from datetime import datetime
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
        self.amount = 0
        self.total_amount = 0
        self.shop_ids = False
        self.tax_ids =[]
        self.journal_ids = []
        
        self.curr_amount_untaxed = 0
        self.curr_amount_tax = 0
        self.curr_amount_total = 0
        
        self.second_amount_untaxed = 0
        self.second_amount_tax = 0
        self.second_amount_total = 0
        
        self.sum_curr_amount_untaxed = 0
        self.sum_second_amount_untaxed = 0
        self.sum_curr_amount_tax = 0
        self.sum_second_amount_tax = 0
        
        self.com_curr = False
        self.second_curr = False
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            
            'get_line':self.get_line,
            'get_total_amount_tax':self.get_total_amount_tax,
            'get_total_amount':self.get_total_amount,
            'get_total_amount_total': self.get_total_amount_total,
            
            'get_sum_amount':self.get_sum_amount,
            'get_sum_amount_tax':self.get_sum_amount_tax,

            'get_month': self.get_month,
            'get_quater': self.get_quater,
            'get_year': self.get_year,
            
            'get_com_curr': self.get_com_curr,
            'get_second_curr': self.get_second_curr,
            'get_2nd_decimal_places': self.get_2nd_decimal_places,
        })
    
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
            self.second_curr = company_obj.second_currency_id or False
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
        self.show_invoice = wizard_data['show_invoice']
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
    
    def get_sum_amount(self, curr):
        if curr == 1:
            return self.sum_curr_amount_untaxed
        else:
            return self.sum_second_amount_untaxed
    
    def get_sum_amount_tax(self, curr):
        if curr == 1:
            return self.sum_curr_amount_tax
        else:
            return self.sum_second_amount_tax
    
    def get_total_amount_tax(self, curr):
        if curr == 1:
            self.sum_curr_amount_tax = self.sum_curr_amount_tax + self.curr_amount_tax
            return self.curr_amount_tax
        else:
            self.sum_second_amount_tax = self.sum_second_amount_tax + self.second_amount_tax
            return self.second_amount_tax
    
    def get_total_amount(self, curr):
        if curr == 1:
            self.sum_curr_amount_untaxed = self.sum_curr_amount_untaxed + self.curr_amount_untaxed
            return self.curr_amount_untaxed
        else:
            self.sum_second_amount_untaxed = self.sum_second_amount_untaxed + self.second_amount_untaxed
            return self.second_amount_untaxed
    
    def get_total_amount_total(self, curr):
        if curr == 1:
            return self.curr_amount_untaxed + self.curr_amount_tax
        else:
            return self.second_amount_untaxed + self.second_amount_tax
        
    def get_line(self):
        tax_lines, curr_amount_untaxed, curr_amount_tax, second_amount_untaxed, second_amount_tax = self.compute_lines()
        return tax_lines
    
    def compute_lines(self):
        res = []
        self.curr_amount_untaxed = 0
        self.curr_amount_tax = 0
        self.second_amount_untaxed = 0
        self.second_amount_tax = 0
        
        from_invoice = ''
        from_voucher = ''
        if len(self.tax_ids):
            #THANH" Show invoice and purchase receipt has specified taxes
            from_invoice += " join account_invoice_tax ait on ai.id = ait.invoice_id and ait.tax_id in (%s)"%(','.join(map(str, self.tax_ids)))
            from_voucher += " join account_payment_invoice_account_tax_rel api_at_rel on api_at_rel.account_payment_invoice_id = api.id and api_at_rel.account_tax_id in (%s)"%(','.join(map(str, self.tax_ids)))
        else:
            #THANH" Show all invoices and purchase receipts in any kinds of taxes
            from_invoice += " join account_invoice_tax ait on ai.id = ait.invoice_id"
            from_voucher += " join account_payment_invoice_account_tax_rel api_at_rel on api_at_rel.account_payment_invoice_id = api.id"
        
        #THANH" Show invoice and purchase with no tax (not tax 0%)
        sql_untax_invoice = '''
                SELECT 
                    ai.reference,
                    ai.supplier_inv_date date_invoice,
                    rp.name partner_name,
                    rp.vat vat_code,
                    array_to_string(ARRAY(SELECT DISTINCT ail.name
                                          FROM account_invoice_line ail
                                          WHERE ail.invoice_id = ai.id), ', ') AS product,
                    '' AS tax,
                    CASE WHEN ai.type ='in_invoice' then       
                    ai.amount_untaxed 
                    ELSE 
                    ai.amount_untaxed * (-1) end amount_untaxed,  
                    CASE WHEN ai.type ='in_invoice' then    
                     ai.amount_tax 
                     else
                     ai.amount_tax * (-1) end amount_tax,
                    ai.comment as notes,
                    ai.number as number,
                    rc.name as currency,
                    
                    array_to_string(ARRAY(SELECT DISTINCT 
                            CASE WHEN aj.type = 'cash' then       
                                'TM'::text
                            ELSE 
                                'CK'::text end
                          FROM account_invoice_payment_rel apl
                              join account_payment ap on apl.invoice_id=ai.id and apl.payment_id=ap.id
                              join account_journal aj on ap.journal_id = aj.id), ', ') AS pay_type,
                    ai.currency_id
                              
                FROM account_invoice ai 
                        left join res_currency rc on rc.id = ai.currency_id
                    join res_partner rp on rp.id = ai.partner_id
                WHERE  ai.state in ('open','paid')
                       and ai.date_invoice between '%s' and '%s'
                       and ai.type in ('in_invoice','in_refund')
                       and NOT EXISTS (select ait.invoice_id from account_invoice_tax ait where ai.id = ait.invoice_id)
                       and ai.journal_id in (%s)
                       --and ai.reference is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
           UNION ALL 
                
                SELECT 
                    api.number as reference,
                    api.date date_invoice,
                    rp.name partner_name,
                    rp.vat vat_code,
                    api.narration product,
                    '' AS tax,
                    api.sub_total amount_untaxed,
                    CASE WHEN api.tax_correction != 0.0 then       
                        api.tax_correction
                    ELSE 
                        api.tax_amount end amount_tax,
                    ap.communication as notes,
                    ap.name as number,
                    rc.name as currency,
                    
                    array_to_string(ARRAY(SELECT   
                                CASE WHEN aj.type = 'cash' then       
                                    'TM'::text
                                ELSE 
                                    'CK'::text end
                              FROM account_journal aj
                              WHERE ap.journal_id = aj.id), ', ') AS pay_type,
                    api.currency_id
                              
                FROM account_payment_invoice api 
                        join account_payment ap on ap.id = api.line_id
                        left join res_currency rc on rc.id = api.currency_id
                        left join res_partner rp on rp.id = api.partner_id
                WHERE ap.state in ('posted')
                    and ap.payment_type = 'outbound'
                    and ap.payment_date between '%s' and '%s'
                    and NOT EXISTS (select api_at_rel.account_payment_invoice_id from account_payment_invoice_account_tax_rel api_at_rel where api_at_rel.account_payment_invoice_id = api.id)
                    and api.journal_id in (%s)
                    --and api.number is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                    
        '''%(self.start_date, self.end_date, self.journal_ids,
             self.start_date, self.end_date, self.journal_ids)
        
        sql_vat_invoice = '''
            SELECT 
                ai.reference,
                ai.supplier_inv_date date_invoice,
                rp.name partner_name,
                rp.vat vat_code,
                array_to_string(ARRAY(SELECT DISTINCT ail.name
                                      FROM account_invoice_line ail
                                      WHERE ail.invoice_id = ai.id), ', ') AS product,
                
                array_to_string(ARRAY(SELECT CAST (CAST (atx.amount as integer) as text)
                                  FROM account_invoice_tax ait
                                      join account_tax atx on ait.tax_id = atx.id and ai.id = ait.invoice_id), ', ') AS tax,
                                          
                CASE WHEN ai.type ='in_invoice' then       
                ai.amount_untaxed 
                ELSE 
                ai.amount_untaxed * (-1) end amount_untaxed,  
                CASE WHEN ai.type ='in_invoice' then    
                 ai.amount_tax 
                 else
                 ai.amount_tax * (-1) end amount_tax,
                ai.comment as notes,
                ai.number as number,
                rc.name as currency,
                
                array_to_string(ARRAY(SELECT DISTINCT 
                            CASE WHEN aj.type = 'cash' then       
                                'TM'::text
                            ELSE 
                                'CK'::text end
                          FROM account_invoice_payment_rel apl
                              join account_payment ap on apl.invoice_id=ai.id and apl.payment_id=ap.id
                              join account_journal aj on ap.journal_id = aj.id), ', ') AS pay_type,
                ai.currency_id
                              
            FROM account_invoice ai
                    left join res_currency rc on rc.id = ai.currency_id
                %s
                join res_partner rp on rp.id = ai.partner_id
            WHERE  ai.state in ('open','paid')
                   and ai.date_invoice between '%s' and '%s'
                   and ai.type in ('in_invoice','in_refund')
                   and ai.journal_id in (%s)
                   --and ai.reference is not null --THANH: 17032017 Thao ben NED muon show ra het hoa don co thue
                   
            UNION ALL 
            
            SELECT 
                api.number as reference,
                api.date date_invoice,
                rp.name partner_name,
                rp.vat vat_code,
                api.narration product,
                array_to_string(ARRAY(SELECT DISTINCT CAST (CAST (atx.amount as integer) as text)
                  FROM account_payment_invoice_account_tax_rel api_at_rel
                      join account_tax atx on  api_at_rel.account_tax_id = atx.id 
                          and api_at_rel.account_payment_invoice_id = api.id), ', ') AS tax,
                api.sub_total amount_untaxed,
                CASE WHEN api.tax_correction != 0.0 then       
                    api.tax_correction
                ELSE 
                    api.tax_amount end amount_tax,
                ap.communication as notes,
                ap.name as number,
                rc.name as currency,
                
                array_to_string(ARRAY(SELECT   
                                CASE WHEN aj.type = 'cash' then       
                                    'TM'::text
                                ELSE 
                                    'CK'::text end
                              FROM account_journal aj
                              WHERE ap.journal_id = aj.id), ', ') AS pay_type,
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
        '''%(from_invoice, self.start_date, self.end_date, self.journal_ids,
             from_voucher, self.start_date, self.end_date, self.journal_ids)
        
        sql = ''
        if self.show_invoice == 'all':
            sql = 'SELECT * from ( ' + \
                sql_untax_invoice + \
                ' UNION ALL ' + \
                sql_vat_invoice + \
                ')x ORDER BY date_invoice, reference, tax'
        else:
            if self.show_invoice == 'vat':
                sql = sql_vat_invoice
            else:
                sql = sql_untax_invoice
            sql = 'SELECT * from ( ' + sql + ')x ORDER BY date_invoice, reference, tax'
                
        currency_obj = self.pool.get('res.currency')
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            #THANH: compute 2nd currency
            curr_amount_untaxed = line['amount_untaxed']
            curr_amount_tax = line['amount_tax']
            second_amount_untaxed = line['amount_untaxed']
            second_amount_tax = line['amount_tax']
            second_rate = 1
            
            
            if line['currency_id']:
                currency = currency_obj.browse(self.cr, self.uid, line['currency_id'])
                if line['currency_id'] != self.company.currency_id.id:
                    curr_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.currency_id)
                    curr_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.currency_id)
                    
                if self.company.second_currency_id and line['currency_id'] != self.company.second_currency_id.id:
                    second_amount_untaxed = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.second_currency_id)
                    second_amount_tax = currency.with_context({'date':line['date_invoice']}).compute(line['amount_tax'], self.company.second_currency_id)
                    second_rate = self.company.second_currency_id.round(second_amount_untaxed / line['amount_untaxed'])
                    
            res.append({
                 'vat_code':line['vat_code'],
                 'reference':line['reference'] or '',
                 'product': line['product'] or '',
                 'tax': line['tax'] or '',
                 'date_invoice':self.get_vietname_date(line['date_invoice']),
                 'partner_name':line['partner_name'],
                 'price_subtotal':line['amount_untaxed'] or 0.0 ,
                 'amount_tax': line['amount_tax'] or 0.0,
                 
                 'curr_amount_untaxed': curr_amount_untaxed,
                 'curr_amount_tax': curr_amount_tax,
                 'curr_amount_total': curr_amount_untaxed + curr_amount_tax,
                 
                 'second_amount_untaxed': second_amount_untaxed,
                 'second_amount_tax': second_amount_tax,
                 'second_amount_total': second_amount_untaxed + second_amount_tax,
                 
                 'second_rate': second_rate,
                     
                 'notes': line['notes'] or '',
                 'number': line['number'] or '',
                 'currency': line['currency'] or '',
                 'pay_type': line['pay_type'] or '',
                 })
            
            self.curr_amount_untaxed += curr_amount_untaxed
            self.curr_amount_tax += curr_amount_tax
            self.curr_amount_total += curr_amount_tax + curr_amount_untaxed
            
            self.second_amount_untaxed += second_amount_untaxed
            self.second_amount_tax += second_amount_tax
            self.second_amount_total += second_amount_untaxed + second_amount_tax
                
        return res, self.curr_amount_untaxed, self.curr_amount_tax, self.second_amount_untaxed, self.second_amount_tax
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
