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
        self.picking_type_id = False
        self.from_date = False
        self.to_date = False
        self.init_qty= 0.0
        self.basis_qty =0.0
        self.init_qty_nm = 0.0
        self.basis_qty_nm =0.0
        self.loss_init_qty =0.0
        self.loss_basis_qty = 0.0
        self.total_loss = 0.0
        self.localcontext.update({
            'get_line':self.get_line,
            'get_datetime':self.get_datetime,
            'get_init_qty':self.get_init_qty,
            'get_basis_qty':self.get_basis_qty,
            'get_init_qty_nm':self.get_init_qty_nm,
            'get_basis_qty_nm':self.get_basis_qty_nm,
            'get_loss_init_qty':self.get_loss_init_qty,
            'get_loss_basis_qty':self.get_loss_basis_qty
        })
    
    def get_init_qty(self):
        return self.init_qty
    
    def get_basis_qty(self):
        return self.basis_qty
    
    def get_init_qty_nm(self):
        return self.init_qty_nm
    
    def get_basis_qty_nm(self):
        return self.basis_qty_nm
    
    def get_loss_init_qty(self):
        return self.loss_init_qty
    
    def get_loss_basis_qty(self):
        return self.loss_basis_qty
    
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.picking_type_id = wizard_data['picking_type_id'] and wizard_data['picking_type_id'][0] or False
        self.from_date = wizard_data['from_date']
        self.to_date = wizard_data['to_date']
    
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
        
    def get_line(self):
        res =[]
        self.get_header()
        sql ='''
            SELECT * 
            FROM 
                stock_picking 
            WHERE date(timezone('UTC',date_done::timestamp)) between  '%s' and '%s'
            and picking_type_id = %s
            and state ='done'
            order by date_done
        '''%(self.from_date,self.to_date,self.picking_type_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            pick =self.pool.get('stock.picking').browse(self.cr,1,line['id'])
            grn_nm =False
            init_qty =0.0
            product_qty= 0.0
            date_nm = False
            sql ='''
                SELECT picking_id from transfer_internal_res 
                    where transfer_id = %s
            '''%(line['id'])
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                sql='''
                    SELECT picking_id from transfer_internal_res 
                        where transfer_id = %s
                '''%(i['picking_id'])
                self.cr.execute(sql)
                for j in self.cr.dictfetchall():
                    pick =self.pool.get('stock.picking').browse(self.cr,1,j['picking_id'])
                    grn_nm = pick.name
                    init_qty = pick.total_init_qty
                    product_qty = pick.total_qty
                    date_nm = self.get_datetime(pick.date_done)
                    
            self.init_qty += line['total_init_qty']
            self.basis_qty += line['total_qty']
            self.init_qty_nm += init_qty
            self.basis_qty_nm += product_qty
            
            self.loss_init_qty += line['total_init_qty'] - init_qty
            self.loss_basis_qty += line['total_qty'] - product_qty
            
            res.append({
                'name_tram':line['name'],
                'grn_nm':grn_nm,
                'date_tram':self.get_datetime(line['date_done']),
                'init_qty':line['total_init_qty'],
                'product_qty':line['total_qty'],
                'date_nm':date_nm,
                'product_qty_nm':product_qty,
                'init_qty_nm':init_qty,
                'loss_init':line['total_init_qty'] - init_qty,
                'loss_basis':line['total_qty'] - product_qty
            })
        
        return res
    
    
    
        
        
        