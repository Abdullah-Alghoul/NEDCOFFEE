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
            'get_asv':self.get_asv,
            'get_npe_nvl':self.get_npe_nvl,
            'get_songay':self.get_songay,
            'centificate':self.centificate,
            'centificavn':self.centificavn,
            'centificaen':self.centificaen
        })
    
    def centificavn(self,o):
        if o.certificate_id:
            return u'Đạt chứng nhận '+o.certificate_id.code
        else:
            return ''
    
    def centificaen(self,o):
        if o.certificate_id:
            return o.certificate_id.code + ' certified.'
        else:
            return ''
    def centificate(self,o):
        line =[]
        if o.certificate_id:
            line.append({
                        'code':o.certificate_id.code
            })
            return line
        return line
    
    def get_npe_nvl(self,o):
        printf =''
        for line in o.nvp_ids:
            for j in line.npe_contract_id.npe_ids:
                if j.contract_id.id == o.id:
                    printf += line.npe_contract_id.name + ': ' +str(int(j.product_qty)) +' Kg; '
        return printf
    
    
    def get_asv(self,name):
        sql ='''
            SELECT id
            FROM res_partner
            WHERE name = '%s'
        '''%(name)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            partner = self.pool.get('res.partner').browse(self.cr,1,line['id'])
            return partner.child_ids and partner.child_ids[0].name or ''
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
        chuoi = users.amount_to_text(o.amount_sub_total, 'vn')
        chuoi = chuoi[0].upper() + chuoi[1:]
        return chuoi
    
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
    
    def get_songay(self,o):
        sql ='''
            SELECT '%s'::date + %s as songay
        '''%(o.date_order,o.so_ngay)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            return self.get_date(line['songay'])
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
