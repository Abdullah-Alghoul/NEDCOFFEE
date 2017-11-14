# -*- coding: utf-8 -*-
from datetime import datetime

from openerp.osv import osv
from openerp.report import report_sxw
import time
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
            'get_string_amount':self.get_string_amount,
            'get_date':self.get_date,
            'get_capacity':self.get_capacity,
            'get_buyer':self.get_buyer,
            'get_recipient':self.get_recipient,
            'get_delivery_place':self.get_delivery_place
        })
    def get_string_amount(self, qty):
        users =self.pool.get('res.users').browse(self.cr,self.uid,SUPERUSER_ID)
        chuoi = users.amount_to_text(qty, 'vn')
        chuoi = chuoi.replace(u'đồng',u'kilogram')
        a = chuoi[0].upper()
        chuoi = chuoi[0].upper() + chuoi[1:]
        return chuoi
    
    def get_delivery_place(self,o):
        if o.delivery_place_id:
            return o.delivery_place_id.name or ''
        if o.contract_id.shipping_id:
            return o.contract_id.shipping_id.delivery_place_id and o.contract_id.shipping_id.delivery_place_id.name or ''
        else:
            return o.warehouse_id.name
        
            
    
    def get_recipient(self,o):
        if o.type == 'Sale':
            return u'Công ty TNHH Cà Phê Hà Lan Việt Nam (Trạm TP.HCM)'
        else:
            return u'Công ty TNHH Cà Phê Hà Lan Việt Nam'
        
    def get_buyer(self,o):
        if o.type == 'Sale':
            return u'NEDCOFFEE BV'
        else:
            return '            '
    
    def get_date(self, o):
        if o.type == 'Sale':
            date = datetime.strptime(o.received_date, DATE_FORMAT)
        else:
            date = datetime.strptime(o.date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_capacity(self,o):
        if o.delivery_order_ids[0].packing_id and o.delivery_order_ids[0].packing_id.capacity:
            return round(o.total_qty / o.delivery_order_ids[0].packing_id.capacity,0)
        else:
            return o.total_qty
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
