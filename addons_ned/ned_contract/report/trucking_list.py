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
            'get_date':self.get_date,
            'get_header':self.get_header,
            'get_capacity':self.get_capacity,
            'get_tota_qty':self.get_tota_qty,
            'get_total_capacity':self.get_total_capacity,
            'get_title':self.get_title,
            'get_qty_string':self.get_qty_string,
            'get_do':self.get_do,
            'get_total_bag':self.get_total_bag,
            'get_capacity':self.get_capacity
        })
    
    def get_do(self,line):
        do_ids = []
        for i in line:
            for j in i.delivery_ids:
                if j.id not in do_ids:
                    do_ids.append(j.id)
        return self.pool.get('delivery.order').browse(self.cr,self.uid,do_ids)
    
    def get_qty_string(self,line):
        qty =  self.get_tota_qty(line)
        users =self.pool.get('res.users').browse(self.cr,self.uid,SUPERUSER_ID)
        chuoi = users.amount_to_text(qty, 'vn')
        chuoi = chuoi.replace(u'đồng',u'kilogram')
        chuoi = chuoi[0].upper() + chuoi[1:]
        return chuoi
    
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_header(self):
        wizard_data = self.localcontext['data']['model']
        return self.pool.get('delivery.order').browse(self.cr,self.uid,wizard_data)
    
    def get_capacity(self,o):
        if o.delivery_order_ids[0].packing_id and o.delivery_order_ids[0].packing_id.capacity:
            return round(o.total_qty / o.delivery_order_ids[0].packing_id.capacity,0)
        else:
            return 0
        
    def get_title(self):
        wizard_data = self.localcontext['data']['model']
        wizard_data = wizard_data and wizard_data[0] or False
        return self.pool.get('delivery.order').browse(self.cr,self.uid,wizard_data)
    
    def get_total_bag(self,line):
        do_ids = []
        total_bag =0.0
        for i in line:
            for j in i.delivery_ids:
                if j.id not in do_ids:
                    do_ids.append(j.id)
        for k in self.pool.get('delivery.order').browse(self.cr,self.uid,do_ids):
            if k.delivery_order_ids[0].packing_id and k.delivery_order_ids[0].packing_id.capacity:
                total_bag += round(k.total_qty / k.delivery_order_ids[0].packing_id.capacity,0)
        return total_bag
    
    def get_tota_qty(self,line):
        do_ids = []
        total_qty =0.0
        for i in line:
            for j in i.delivery_ids:
                if j.id not in do_ids:
                    do_ids.append(j.id)
        for k in self.pool.get('delivery.order').browse(self.cr,self.uid,do_ids):
            total_qty += k.total_qty
        return total_qty
    
    def get_total_capacity(self):
        wizard_data = self.localcontext['data']['model']
        qty =0.0
        for delivery in self.pool.get('delivery.order').browse(self.cr,self.uid,wizard_data):
            for line in delivery.delivery_order_ids:
                if line.packing_id and line.packing_id.capacity:
                    qty += round(delivery.total_qty / line.packing_id.capacity,0)
                else:
                    qty += line.product_qty
        return qty
    

    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
