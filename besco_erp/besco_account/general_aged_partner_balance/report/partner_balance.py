# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.account_id =False
        self.times = False
        self.start_date = False
        self.end_date = False
        self.company_name = False
        self.company_address = False
        self.showdetail = False
        self.vat = False
        self.shop_ids = []
        self.truoc_credit = 0.0
        self.truoc_debit = 0.0
        self.sau_credit = 0.0
        self.sau_debit = 0.0
        self.sum_credit = 0.0
        self.is_customer = False
        self.sum_debit = 0.0
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date, 
            'get_line':self.get_line,
            'get_header':self.get_header,
            'get_account':self.get_account,
            'get_start_date':self.get_start_date,
            'get_end_date':self.get_end_date,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            'get_truoc_credit':self.get_truoc_credit,
            'get_truoc_debit':self.get_truoc_debit,
            'get_sau_debit':self.get_sau_debit,
            'get_sau_credit':self.get_sau_credit,
            'get_sum_debit':self.get_sum_debit,
            'get_sum_credit':self.get_sum_credit,
            'get_account':self.get_account,
        })
    
    def get_truoc_credit(self):
        return self.truoc_credit
    
    def get_truoc_debit(self):
        return self.truoc_debit
    
    def get_sau_debit(self):
        return self.sau_debit
    
    def get_sau_credit(self):
        return self.sau_credit
    def get_sum_credit(self):
        return self.sum_credit
    def get_sum_debit(self):
        return self.sum_debit
    
    def get_company(self, company_id):
        if company_id:
            company_obj = self.pool.get('res.company').browse(self.cr, self.uid,company_id)
            self.company_name = company_obj.name or ''
            self.company_address = company_obj.street or ''
            self.vat = company_obj.vat or ''
        return True
             
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
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.times = wizard_data['times']
        #Get company info
        self.company_id = wizard_data['company_id'] and wizard_data['company_id'][0] or False
        self.get_company(self.company_id)
        
        if self.times =='periods':
            self.start_date = self.pool.get('account.period').browse(self.cr,self.uid,self.get_id('period_id_start')).date_start
            self.end_date   = self.pool.get('account.period').browse(self.cr,self.uid,self.get_id('period_id_start')).date_stop
        elif self.times == 'years':
            self.start_date = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).date_start
            self.end_date   = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).date_stop
        elif self.times == 'dates':
            self.start_date = wizard_data['date_start']
            self.end_date   = wizard_data['date_end']
            
        else:
            quarter = wizard_data['quarter'] or False
            year = self.pool.get('account.fiscalyear').browse(self.cr,self.uid,self.get_id('fiscalyear_start')).name
            self.get_quarter_date(year, quarter)
            
        self.is_customer = wizard_data['is_customer'] or False
            
    def get_start_date(self):
        self.get_header()
        return self.get_vietname_date(self.start_date) 
    
    def get_end_date(self):
        return self.get_vietname_date(self.end_date) 
    
    def get_account(self):
        if self.is_customer == 'customer':
            return u'131 - Phải thu của khách hàng'
        else:
            return u'331 - Phải trả người bán'
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
        
    def get_line(self):
        if not self.start_date:
            self.get_header()
        if self.is_customer =='customer':
            sql ='''
                SELECT rp.name,rp.ref,sum(truoc_total) truoc_total,sum(sum_debit) sum_debit, sum(sum_credit) sum_credit,sum(sau_total) sau_total
                FROM (
                    select partner_id,sum(debit)-sum(credit) truoc_total,0 sum_debit, 0 sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date < '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,sum(debit) sum_debit, sum(credit) sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date between '%s' and '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,0 sum_debit, 0 sum_credit,sum(debit)-sum(credit) sau_total from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date < '%s'
                        group by partner_id) x join res_partner rp on x.partner_id = rp.id and rp.customer = true
                GROUP BY rp.name,rp.ref
                HAVING sum(truoc_total) !=0 or sum(sum_debit) !=0 or sum(sum_credit) !=0 or sum(sau_total) !=0 
            '''%(self.start_date,self.start_date,self.end_date,self.end_date)
        elif self.is_customer =='supplier':
            sql ='''
                SELECT rp.name,rp.ref,sum(truoc_total) truoc_total,sum(sum_debit) sum_debit, sum(sum_credit) sum_credit,sum(sau_total) sau_total
                FROM (
                    select partner_id,sum(debit)-sum(credit) truoc_total,0 sum_debit, 0 sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date < '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,sum(debit) sum_debit, sum(credit) sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date between '%s' and '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,0 sum_debit, 0 sum_credit,sum(debit)-sum(credit) sau_total from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date <= '%s'
                        group by partner_id) x join res_partner rp on x.partner_id = rp.id and rp.supplier = true
                GROUP BY rp.name,rp.ref
                HAVING sum(truoc_total) !=0 or sum(sum_debit) !=0 or sum(sum_credit) !=0 or sum(sau_total) !=0 
            '''%(self.start_date,self.start_date,self.end_date,self.end_date)
        else:
            sql='''
            SELECT rp.name,rp.ref,sum(truoc_total) truoc_total,sum(sum_debit) sum_debit, sum(sum_credit) sum_credit,sum(sau_total) sau_total
                FROM (
                    select partner_id,sum(debit)-sum(credit) truoc_total,0 sum_debit, 0 sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date < '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,sum(debit) sum_debit, sum(credit) sum_credit, 0 sau_total
                        from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date between '%s' and '%s'
                        group by partner_id
                    union all
                    select partner_id,0 truoc_total,0 sum_debit, 0 sum_credit,sum(debit)-sum(credit) sau_total from account_move_line aml join account_account acc on aml.account_id = acc.id
                        join account_account_type acc_type on acc.user_type_id = acc_type.id and acc_type.type in ('payable','receivable')
                        where aml.date <= '%s'
                        group by partner_id) x join res_partner rp on x.partner_id = rp.id 
                GROUP BY rp.name,rp.ref
                HAVING sum(truoc_total) !=0 or sum(sum_debit) !=0 or sum(sum_credit) !=0 or sum(sau_total) !=0 
            '''%(self.start_date,self.start_date,self.end_date,self.end_date)
            
        self.cr.execute(sql)
        res =[]
        for i in self.cr.dictfetchall():
            if  i['truoc_total'] < 0:
                truoc_credit = i['truoc_total']
                self.truoc_credit += abs(truoc_credit)
                truoc_debit = 0.0
            else:
                truoc_credit = 0.0
                truoc_debit = i['truoc_total']
                self.truoc_debit += abs(truoc_debit)
            
            if i['sau_total']> 0:
                sau_debit =  i['sau_total']
                sau_credit = 0.0 
                self.sau_debit += abs(sau_debit)
            else:
                sau_debit = 0.0
                sau_credit = i['sau_total']
                self.sau_credit += abs(sau_credit)
            
            self.sum_credit += i['sum_credit']
            self.sum_debit += i['sum_debit']
                
            res.append({
               'partner_name':i['name'],
               'internal_code':i['ref'],
               'truoc_debit':abs(truoc_debit),
               'truoc_credit':abs(truoc_credit),
               'sum_debit': i['sum_debit'],
               'sum_credit': i['sum_credit'],
               'sau_debit': abs(sau_debit) or 0.0,
               'sau_credit': abs(sau_credit) or 0.0,
               })
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
