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
        self.from_date = False
        self.to_date = False
        self.production_id = False
        self.localcontext.update({
            'get_date':self.get_date,
            'get_line':self.get_line,
            'get_destart':self.get_destart,
            'get_destrt':self.get_destrt,
            'get_issued_qty':self.get_issued_qty,
            'get_to_be_issued':self.get_to_be_issued,
            'get_stack_qty':self.get_stack_qty,
            'get_zone':self.get_zone,
            'get_stack':self.get_stack
        })
    
    
    def get_to_be_issued(self,re_qty,isue_qty):
        return re_qty - isue_qty
    
    def get_issued_qty(self,request_id):
        line = self.pool.get('request.materials.line').browse(self.cr,self.uid,request_id)
        return line.basis_qty
    
    def get_stack_qty(self,request_id):
        line = self.pool.get('request.materials.line').browse(self.cr,self.uid,request_id)
        return line.stack_id.init_qty
    
    def get_zone(self,request_id):
        line = self.pool.get('request.materials.line').browse(self.cr,self.uid,request_id)
        return line.stack_id.zone_id.name 
    
    def get_stack(self,request_id):
        line = self.pool.get('request.materials.line').browse(self.cr,self.uid,request_id)
        return line.stack_id.code or line.stack_id.name
    
    
        
    def get_line(self):
        self.get_header()
        if self.production_id:
            sql ='''
                SELECT rml.id request_id,mrp.name name_mrp, rm.name rm_name,rm.request_date, pp.default_code,
                rml.product_qty request_qty,rml.state
                FROM request_materials rm 
                    join request_materials_line rml on rm.id =  rml.request_id
                    join product_product pp on rml.product_id = pp.id
                    join mrp_production mrp on mrp.id = rm.production_id
                WHERE mrp.id = %s
            '''%(self.production_id)
        else:
            sql ='''
                SELECT rml.id request_id,mrp.name name_mrp, rm.name rm_name,rm.request_date, pp.default_code,
                rml.product_qty request_qty,rml.state
                FROM request_materials rm 
                    join request_materials_line rml on rm.id =  rml.request_id
                    join product_product pp on rml.product_id = pp.id
                    join mrp_production mrp on mrp.id = rm.production_id
                WHERE rm.request_date between '%s' and '%s'
            '''%(self.from_date,self.to_date)
        self.cr.execute(sql)
        return self.cr.dictfetchall()
    
    def get_destart(self):
        self.get_header()
        return self.get_date(self.from_date)
    
    def get_destrt(self):
        self.get_header()
        return self.get_date(self.to_date)
        
        
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
    
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.from_date = wizard_data['from_date'] or False
        self.to_date = wizard_data['to_date'] or False
        self.production_id = wizard_data['production_id'] and wizard_data['production_id'][0] or False
        return True
    
    
    
            
        
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
