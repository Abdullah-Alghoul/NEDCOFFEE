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
        self.partner_id = False
        self.date = 0.0
        self.localcontext.update({
            'get_date':self.get_date,
            'get_partner':self.get_partner,
            'get_todate':self.get_todate,
            'get_ned_no':self.get_ned_no,
            'get_supplier_no':self.get_supplier_no,
            'get_total_unfix':self.get_total_unfix,
            'get_lai':self.get_lai,
            'get_ngaythangnam':self.get_ngaythangnam,
            'acv':self.acv,
            'ack':self.ack
        })
    
    def get_ngaythangnam(self):
        self.get_header()
        if not self.date:
            now = time.strftime(DATE_FORMAT)
        now = datetime.strptime(self.date, DATE_FORMAT)
        current_year = now.year
        current_month = now.month
        current_day = now.day
        return str(current_day) + u' tháng ' + str(current_month)+  u' năm ' + str(current_year)
    
    def get_balance_net(self,net,gdp_net,delivery_net):
        return net - (gdp_net + delivery_net)
        
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_lai(self):
        supplier_no =0.0
        sql ='''
            SELECT irs.id
            FROM request_payment rp join purchase_contract pc on rp.purchase_contract_id = pc.id
                join interest_rate irs on irs.request_id = rp.id
            WHERE rp.type ='consign' and total_remain !=0
                and rp.partner_id = %s
                and pc.date_order <= '%s'
        '''%(self.partner_id,self.date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            supplier_no += self.pool.get('interest.rate').browse(self.cr,self.uid,i['id'])._compute_provisional_rate(self.date) or 0.0
        return supplier_no
    
    def get_ned_no(self):
        self.get_header()
        sql ='''
            SELECT sum(amount_total) amount_total 
            FROM purchase_contract where type = 'purchase'
                and state ='approved'
                and partner_id = %s
                and date_order <= '%s'
        '''%(self.partner_id,self.date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return i['amount_total'] or 0.0
        return 0
    
    def get_supplier_no(self):
        supplier_no = 0
        self.get_header()
        sql ='''
            SELECT  ap.id id
            FROM account_payment ap
                join purchase_contract po on  ap.purchase_contract_id = po.id
            WHERE
                po.type != 'purchase'
                and po.state ='approved'
                and po.partner_id = %s
                    and po.date_order <= '%s'
        '''%(self.partner_id,self.date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            supplier_no += self.pool.get('account.payment').browse(self.cr,self.uid,i['id']).open_advance or 0.0
        return supplier_no
    
    def get_total_unfix(self):
        qty_receive =0
        qty_fix = 0.0
        sql ='''
            SELECT id 
            from purchase_contract po
            WHERE po.type != 'purchase'
                and po.state ='approved'
                and po.partner_id = %s
                and po.date_order <= '%s'
        '''%(self.partner_id,self.date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty_receive += self.pool.get('purchase.contract').browse(self.cr,self.uid,i['id']).qty_received or 0.0
        
        self.cr.execute(sql)
        for i in self.pool.get('npe.nvp.relation').search(self.cr,1,[('partner_id','=',self.partner_id),('date_fixed','<=',self.date)]):
            k = self.pool.get('npe.nvp.relation').browse(self.cr,1,i)
            qty_fix += k.product_qty or 0.0
            
        return qty_receive - qty_fix
    
    def get_todate(self):
        self.get_header()
        return self.get_date(self.date)
    
    def get_partner(self):
        self.get_header()
        partner = self.pool.get('res.partner').browse(self.cr,self.uid,self.partner_id)
        return partner.name
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.partner_id = wizard_data['partner_id'] and wizard_data['partner_id'][0] or False
        self.date = wizard_data['date']  or False
        return True
    
    def acv(self):
        end_331108_cr = end_331108_dr = end_dr_2nd= end_cr_2nd = 0.0
        self.get_header()
        account_payable =self.pool.get('res.partner').browse(self.cr,1,self.partner_id)
        account_payable = account_payable.property_account_payable_id
        val = {'month': '11', 'date_end': self.date, 'date_start': '2016-01-01', 
               'company_id': 1, 'times': 'dates', 'fiscalyear_id': 2, 
               'partner_ids': [[6, False, [self.partner_id]]], 'quarter': '1', 'type': 'payable', 
               'extend_payment': 'none'}
        new_id =self.pool.get('report.partner.balance').create(self.cr,1,val)
        balance = self.pool.get('report.partner.balance').browse(self.cr,1,new_id)
        balance.load_general_balance()
        for line in balance.second_balance_lines:
            if line.end_cr_2nd:
                end_dr_2nd = line.end_cr_2nd or 0.0
            else:
                end_cr_2nd = line.end_dr_2nd or 0.0
        self.pool.get('report.partner.balance').unlink(self.cr,1,new_id)
        
        
        val = {'month': '11', 'date_end': self.date, 'date_start': '2016-01-01', 
               'company_id': 1, 'times': 'dates', 'fiscalyear_id': 2, 
               'partner_ids': [[6, False, [self.partner_id]]], 'quarter': '1', 'type': 'payable', 
               'extend_payment': 'none'}
        new_id =self.pool.get('report.partner.balance').create(self.cr,1,val)
        balance = self.pool.get('report.partner.balance').browse(self.cr,1,new_id)
        balance.load_general_balance()
        for line in balance.second_balance_lines:
            if line.end_cr_2nd:
                end_331108_cr = line.end_cr_2nd or 0.0
            else:
                end_331108_dr = line.end_dr_2nd or 0.0
        
        self.pool.get('report.partner.balance').unlink(self.cr,1,new_id)
                
        return (end_331108_dr + end_dr_2nd) - (end_cr_2nd - end_331108_cr)
    
    def ack(self):
        self.get_header()
        end_cr_2nd = 0.0
        account_advance_payable =self.pool.get('res.partner').browse(self.cr,1,self.partner_id)
        account_advance_payable = account_advance_payable.property_vendor_advance_acc_id
        val = {'month': '11', 'date_end': self.date, 'date_start': '2016-01-01', 
               'company_id': 1, 'times': 'dates', 'fiscalyear_id': 2, 
               'partner_ids': [[6, False, [self.partner_id]]], 'quarter': '1', 'type': 'payable', 
               'extend_payment': 'none'}
        new_id =self.pool.get('report.partner.balance').create(self.cr,1,val)
        balance = self.pool.get('report.partner.balance').browse(self.cr,1,new_id)
        balance.load_general_balance()
        for line in balance.second_balance_lines:
            if line.end_cr_2nd:
                end_cr_2nd = line.end_cr_2nd or 0.0
            else:
                end_cr_2nd =  line.end_dr_2nd or 0.0
        
        self.pool.get('report.partner.balance').unlink(self.cr,1,new_id)
        
        return end_cr_2nd
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
