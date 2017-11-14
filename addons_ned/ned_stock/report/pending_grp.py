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
        self.localcontext.update({
            'get_header':self.get_header,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_datetime':self.get_datetime
        })
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        picking_ids = wizard_data['active_ids'] and wizard_data['active_ids'] or False
        self.pool.get('stock.picking').browse(self.cr,self.uid,picking_ids)
        return self.pool.get('stock.picking').browse(self.cr,self.uid,picking_ids)
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
            
             
    def get_company_name(self):
        users_obj = self.pool.get('res.users').browse(self.cr, self.uid,self.uid)
        return users_obj.company_id.name or ''
    
    def get_company_address(self):
        users_obj = self.pool.get('res.users').browse(self.cr, self.uid,self.uid)
        return users_obj.company_id.street or ''