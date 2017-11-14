# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp import SUPERUSER_ID

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.bank_name =False
        self.partner = False
        self.account_holder = False
        self.acc_number = False
        self.localcontext.update({
            'get_account_holder':self.get_account_holder,
            'get_bank_name':self.get_bank_name,
            'get_acc_number':self.get_acc_number,
            'get_string_amount':self.get_string_amount,
            'get_date':self.get_date,
            'get_term': self.get_term,
            'get_date_mos':self.get_date_mos,
            'get_dates_mos':self.get_dates_mos
        })
    
    def get_account_holder(self,partner):
        if not self.account_holder:
            self.get_partner_banks(partner)
        return self.account_holder or ''
    
    def get_bank_name(self,partner):
        if not self.bank_name:
            self.get_partner_banks(partner)
        return self.bank_name or ''
    
    def get_string_amount(self, o):
        users =self.pool.get('res.users').browse(self.cr,self.uid,SUPERUSER_ID)
        return users.amount_to_text(o.request_amount, 'vn')
    
    def get_acc_number(self,partner):
        if not self.acc_number:
            self.get_partner_banks(partner)
        return self.acc_number or ''
    
    def get_partner_banks(self,partner):
        sql ='''
            SELECT rp.name account_holder, rb.name bank_name,acc_number,* 
            FROM res_partner_bank rpb join res_bank rb on rpb.bank_id = rb.id 
                join res_partner rp on rpb.partner_id= rp.id
            WHERE partner_id = %s
        '''%(partner.id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            self.account_holder = line['account_holder']
            self.bank_name = line['bank_name']
            self.acc_number = line['acc_number']
            
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_date_mos(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%b, %Y')
    
    def get_dates_mos(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%b, %d, %Y')
    
    
    def get_term(self, status):
        if status in ('fOB','FOB'):
            term = 'FOB'
        else:
            term = 'Allocated'
        return term
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
