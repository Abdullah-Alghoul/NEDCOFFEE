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
            'get_lai':self.get_lai
        })
    
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
        qty =0
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
            qty += self.pool.get('purchase.contract').browse(self.cr,self.uid,i['id']).qty_unfixed or 0.0
        return qty
    
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
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
