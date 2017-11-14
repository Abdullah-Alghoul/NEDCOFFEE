# -*- coding: utf-8 -*-
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from openerp import _

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.start_date = False
        self.end_date = False
        
        self.company = False
        self.company_name = False
        self.company_address = False
        self.vat = False
        self.group_by_partner = {}
        self.group_by_currency = {}
        
        self.currency_name = ''
        self.second_currency_name = ''
        
        self.currency_value = 0.0
        self.second_currency_value = 0.0
        self.second_rate = 1
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_header':self.get_header,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            'currency_name': self.get_currency_name,
            'second_currency_name': self.get_second_currency_name,
            
            'get_partners': self.get_partners,
            'get_currency': self.get_currency,
            'get_cash': self.get_cash,
            'get_currency_total': self.get_currency_total,
            
            'get_currency_value': self.get_currency_value,
            'get_second_currency_value': self.get_second_currency_value,
            'get_second_rate': self.get_second_rate,
            'get_vay_rate': self.get_vay_rate,
        })
    
    def get_company(self):
        if self.company_id:
            company_obj = self.pool.get('res.company').browse(self.cr, self.uid, self.company_id)
            self.company_name = company_obj.name or ''
            self.company_address = company_obj.street or ''
            self.vat = company_obj.vat or ''
            self.currency_name = company_obj.currency_id.name
            self.second_currency_name = company_obj.second_currency_id and company_obj.second_currency_id.name or ''
            self.company = company_obj
        return True
    
    def get_second_currency_name(self):
        return self.second_currency_name

    def get_currency_name(self):
        return self.currency_name
    
    def get_company_name(self):
        self.get_header()
        return self.company_name
    
    def get_company_address(self):
        return self.company_address     
    
    def get_company_vat(self):
        return self.vat
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.start_date = wizard_data['date_start']
        self.end_date = wizard_data['date_end']
        date_type = wizard_data['date_type']
        state = wizard_data['state']
        self.company_id = wizard_data['company_id'][0]
        self.get_company()
        
        #THANH: Load all data
        cash_date = 'cd.date_start' #THANH: default filter asset by entry date
        if date_type == 'due_date':
            cash_date = 'cd.date_stop'
            
        filter_date = ''
        if self.start_date and self.end_date:
            filter_date += " and %(cash_date)s between '%(start_date)s' and '%(end_date)s'"%({'cash_date': cash_date, 
                                                                                               'start_date': self.start_date, 'end_date': self.end_date})
        if self.start_date and not self.end_date:
            filter_date += " and %(asset_date)s >= '%(start_date)s'"%({'cash_date': cash_date, 'start_date': self.start_date})
        if not self.start_date and self.end_date:
            #THANH: Can not filter
            return False
        
        filter_state = ''
        if state:
            filter_date += " and cd.state = '%(state)s'"%({'state': state})
        
        sql = _(u'''
            select cd.id cash_id, rp.name partner_name, cd.name number, cd.date_start, cd.date_stop, cd.payment_date,
                cd.amount_main, rc.name currency_name,
                (select sum(amount)
                    from account_cash_operation_in_out io 
                    where io.out_cash_id = cd.id and io.state = 'confirm') as paid_amount
                    
            from account_cash_operation cd
                left join res_partner rp on rp.id = cd.partner_id
                left join res_currency rc on rc.id = cd.currency_id
                left join res_company com on com.id = cd.company_id
                
            where cd.type = '%(type)s'
                %(filter_date)s
                %(filter_state)s
                and cd.company_id = %(company_id)s
            ORDER BY cd.date_start, cd.date_stop
        ''')
        sql = sql%({
                    'filter_state': filter_state,
                    'filter_date': filter_date,
                    'type': wizard_data['operation_type'],
                    'company_id': self.company_id,
                  })
        self.cr.execute(sql)
        
        group_by_partner = {}
        group_by_currency = {}
        for line in self.cr.dictfetchall():
            paid_amount = line['paid_amount'] or 0.0
            line.update({'remain_amount': line['amount_main'] - paid_amount})
            
            if not group_by_partner.has_key(line['partner_name']):
                group_by_partner.update({line['partner_name']:[line]})
            else:
                group_by_partner[line['partner_name']].append(line)
            
            if not group_by_currency.has_key(line['currency_name']):
                group_by_currency.update({line['currency_name']:[line]})
            else:
                group_by_currency[line['currency_name']].append(line)
        
        self.group_by_partner = group_by_partner
        self.group_by_currency = group_by_currency
    
    def get_vay_rate(self, cash_id, amount_main):
        cash = self.pool.get('account.cash.operation').browse(self.cr, self.uid, cash_id)
        vay_rate = 1
        self.currency_value = amount_main
        self.second_currency_value = amount_main
        self.second_rate = 1
        if cash.currency_id != cash.company_id.currency_id:
            convert = cash.currency_id.with_context({'date':cash.date_start}).compute(amount_main, self.company.currency_id)
            vay_rate = self.company.currency_id.round(convert > amount_main and convert / amount_main or amount_main / convert)
            self.currency_value = convert
            
        if cash.company_id.second_currency_id and cash.currency_id != cash.company_id.second_currency_id:
#             ex_rate, rate = self.pool.get('res.currency')._get_conversion_rate(self.cr, self.uid, cash.currency_id, cash.company_id.second_currency_id, context={'date':cash.date_start})
            convert = cash.currency_id.with_context({'date':cash.date_start}).compute(amount_main, self.company.second_currency_id)
            self.second_rate = self.company.second_currency_id.round(convert > amount_main and convert / amount_main or amount_main / convert)
            self.second_currency_value = convert
            
        if cash.company_id.second_currency_id and cash.currency_id == cash.company_id.second_currency_id:
            self.second_rate = vay_rate
        return vay_rate
    
    def get_currency_value(self):
        return self.currency_value
    
    def get_second_rate(self):
        return self.second_rate
    
    def get_second_currency_value(self):
        return self.second_currency_value
    
    def get_partners(self):
        partner = []
        for key, val in self.group_by_partner.items():
            partner.append(key)
        return partner
    
    def get_currency(self):
        currency = []
        for key, val in self.group_by_currency.items():
            currency.append(key)
        return currency
    
    def get_currency_total(self, c):
        total = 0.0
        for line in self.group_by_currency[c]:
            total += line['amount_main']
        return total
    
    def get_cash(self, partner):
        return self.group_by_partner[partner]
        
    def get_start_date(self):
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    def get_vietname_date(self, date):
        if not date:
            return ''
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
