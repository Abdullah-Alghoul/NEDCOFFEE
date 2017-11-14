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
            'get_destrt':self.get_destrt
        })
    
        
        
    def get_line(self):
        self.get_header()
        if self.production_id:
            sql ='''
                SELECT mrp.name mrp_name,re.name request_name,sp.name pick_name,pp.default_code,zone.name zone_name,
                    sta.name stack_name,sp.total_init_qty re_qty,sp.total_qty qty,
                    date(timezone('UTC',sp.date_done ::timestamp)) date_issue         
                FROM stock_picking sp 
                    join  picking_request_move_ref refs on sp.id = refs.request_id 
                    join request_materials_line line on line.id = refs.picking_id
                    join request_materials re on re.id = line.request_id
                    join mrp_production mrp on mrp.id = re.production_id
                    join product_product pp on pp.id = line.product_id
                    join stock_zone zone on zone.id = sp.zone_id
                    join stock_stack sta on sta.id = sp.stack_id
                    where mrp.id = %s
                          and sp.state ='done'
            '''%(self.production_id)
        else:
            sql ='''
                SELECT mrp.name mrp_name,re.name request_name,sp.name pick_name,pp.default_code,zone.name zone_name,
                    sta.name stack_name,sp.total_init_qty  re_qty,sp.total_qty qty,
                    date(timezone('UTC',sp.date_done ::timestamp)) date_issue         
                FROM stock_picking sp 
                    join  picking_request_move_ref refs on sp.id = refs.request_id 
                    join request_materials_line line on line.id = refs.picking_id
                    join request_materials re on re.id = line.request_id
                    join mrp_production mrp on mrp.id = re.production_id
                    join product_product pp on pp.id = line.product_id
                    join stock_zone zone on zone.id = sp.zone_id
                    join stock_stack sta on sta.id = sp.stack_id
                    where date(timezone('UTC',sp.date_done ::timestamp)) between '%s' and '%s'
                          and sp.state ='done'
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
