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
            'get_partner_address':self.get_partner_address,
            'get_warehouse_address': self.get_warehouse_address,
            'get_datetime':self.get_datetime,
            'get_users':self.get_users,
            'get_state': self.get_state
        })
    
    def get_users(self):
        users = self.pool.get('res.users').browse(self.cr,self.uid,self.uid)
        return users.name or ''
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_partner_address(self, partner_id):
        address = ''
        if partner_id:
            address += partner_id.street or ''
            address += partner_id.state_id and ', ' + partner_id.state_id.name or ''
            address += partner_id.city and ', ' + partner_id.city or ''
            address += partner_id.country_id and ', ' + partner_id.country_id.name or ''
        return address
    
    def get_warehouse_address(self, warehouse_id):
        address = ''
        if warehouse_id.partner_id:
            address += warehouse_id.partner_id.street or ''
            address += warehouse_id.partner_id.state_id and ', ' + warehouse_id.partner_id.state_id.name or ''
            address += warehouse_id.partner_id.city and ', ' + warehouse_id.partner_id.city or ''
            address += warehouse_id.partner_id.country_id and ', ' + warehouse_id.partner_id.country_id.name or ''
        return address
    
    def get_state(self, state):
        call = ''
        if state:
            if state in ('draft','sent'):
                call = u'Nháp'
            elif state == 'to approve':
                call = u'Chờ Xác Nhận'
            elif state == 'purchase':
                call = u'Đã Xác Nhận'
            elif state == 'done':
                call = u'Hoàn Tất'
            elif state == 'cancel':
                call = u'Huỷ'
        return call
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
