# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
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
            'get_rate': self.get_rate,
            'get_date_end': self.get_date_end,
            'get_total_qty': self.get_total_qty,
            'get_songay':self.get_songay
        })
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_songay(self,date,so_ngay):
        sql ='''
            SELECT '%s'::date + %s as songay
        '''%(date,so_ngay)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            return self.get_date(line['songay'])
        return ''
        
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
        return
            
    
    def get_rate(self, request_id):
        rate = 0.0
        if not request_id:
            return rate
        sql ='''
            SELECT rate 
            FROM interest_rate 
            WHERE request_id = %s
            AND month = '1'
        '''%(request_id)
        self.cr.execute(sql)
        result = self.cr.dictfetchall()
        rate = result and result[0] and result[0]['rate'] or 0.0
        return rate
    
    def get_date_end(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        date_end = date + timedelta(days=120)
        date_end = date_end.strftime('%d/%m/%Y')
        return date_end

    def get_total_qty(self, purchase_contract_id):
        total_qty = 0.0
        if not purchase_contract_id:
            return total_qty
        sql ='''
            SELECT sum(sm.product_uom_qty) total_qty
            FROM stock_picking sp join stock_move sm on sm.picking_id = sp.id
            WHERE sp.state = 'done' AND sp.purchase_contract_id = %s
        '''%(purchase_contract_id)
        self.cr.execute(sql)
        result = self.cr.dictfetchall()
        total_qty = result and result[0] and result[0]['total_qty'] or 0.0
        return total_qty
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
