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
        self.production_id = False
        self.production_shift = False
        self.from_date = False
        self.to_date = False
        self.production_id = False
        self.localcontext.update({
            'get_line':self.get_line,
            'get_totalqty':self.get_totalqty,
            'get_production':self.get_production,
            'get_datetime':self.get_datetime,
            'get_forproduct':self.get_forproduct,
            'get_stdate':self.get_stdate,
            'get_si':self.get_si,
            'get_gip':self.get_gip,
            'get_state':self.get_state
        })
    
    def get_state(self,picking):
        return (picking.state or '') +' - ' + (picking.state_kcs or '')
    def get_stdate(self):
        self.get_header()
        return self.get_date(self.from_date) +' - ' + self.get_date(self.to_date)
    
    
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
    
    def get_toproductkcs(self,production_id):
        qty = 0
        sql ='''
            SELECT sum(line.total_qty) product_qty
                FROM stock_picking line
                WHERE
                    production_id = %s
                    and state_kcs = 'approved'
                    and picking_type_code ='production_in'
                    and state ='done'
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
    
    def get_topgip(self,production_id):
        qty = 0
        sql ='''
            SELECT sum(line.total_qty) product_qty
                FROM stock_picking line
                WHERE
                    production_id = %s
                    and picking_type_code ='production_out'
                    and state ='done'
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
    
    def get_toproductreject(self,production_id):
        qty = 0
        sql ='''
            SELECT sum(line.total_qty) product_qty
                FROM stock_picking line
                WHERE
                    production_id = %s
                    and state_kcs = 'reject'
                    and picking_type_code ='production_in'
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
    
    def get_toproduction(self,production_id):
        qty = 0
        sql ='''
            SELECT sum(line.total_qty) product_qty
                FROM stock_picking line
                WHERE
                    production_id = %s
                    and picking_type_code ='production_in'
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
    
    def get_production(self):
        self.get_header()
        val =[]
        if self.production_id:
            sql ='''
                SELECT id,name from mrp_production
                WHERE 
                    id = %s
                Order by date_planned desc
            '''%(self.production_id)
        else:
            sql ='''
                SELECT id,name from mrp_production
                WHERE 
                    date(timezone('UTC',date_planned::timestamp)) between '%s' and '%s'
                Order by date_planned desc
            '''%(self.from_date,self.to_date)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty_kcsed = self.get_toproductkcs(i['id'])
            qty_reject= self.get_toproductreject(i['id'])
            qty = self.get_toproduction(i['id'])
            gip_qty = self.get_topgip(i['id']) or 0.0
            val.append({
                'name':i['name'],
                'id':i['id'],
                'to_qty_kcsed':qty_kcsed,
                'to_qty_reject':qty_reject,
                'to_qty': qty,
                'to_qty_notkcs': qty - (qty_kcsed + qty_reject),
                'gip_qty':gip_qty
            })
        return val
    
    def get_totalqty(self,production_id):
        mrp = self.pool.get('mrp.production').browse(self.cr,self.uid,production_id)
        return mrp.product_received
    
    def get_si(self,picking_id):
        if picking_id:
            sql ='''
                SELECT id FROM
                mrp_operation_result_produced_product
                WHERE 
                    picking_id = %s
            '''%(picking_id)
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                mrp = self.pool.get('mrp.operation.result.produced.product').browse(self.cr,self.uid,i['id'])
                si = mrp.si_id and mrp.si_id.name or ''
                return si
        return ''
        
    def get_line(self,production_id):
        self.get_header()
        move_is =[]
        sql ='''
            SELECT sm.id from stock_move sm join stock_picking sp on sm.picking_id = sp.id
                 where sm.production_id = %s and picking_type_code ='production_in' 
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            move_is.append(i['id'])
        return self.pool.get('stock.move').browse(self.cr,self.uid,move_is)
    
    def get_gip(self,production_id):
        self.get_header()
        move_is =[]
        mrp = self.pool.get('mrp.production').browse(self.cr,self.uid,production_id)
        for move in mrp.move_lines:
            move_is.append(move.id)
        return self.pool.get('stock.move').browse(self.cr,self.uid,move_is)
    
    def getproductkcs(self,production_id,product_id):
        qty = 0
        sql ='''
            SELECT sum(sp.total_qty) product_qty
                FROM stock_picking sp join stock_move sm on sp.id = sm.picking_id  
                join product_product pp on sm.product_id = pp.id
                WHERE
                    sp.production_id = %s
                    and sp.state = 'done'
                    and state_kcs ='approved'
                    and picking_type_code ='production_in'
                    and sm.product_id = %s
        '''%(production_id,product_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
    
    def getproductreject(self,production_id,product_id):
        qty = 0
        sql ='''
            SELECT sum(sp.total_qty) product_qty
                FROM stock_picking sp join stock_move sm on sp.id = sm.picking_id  
                join product_product pp on sm.product_id = pp.id
                WHERE
                    sp.production_id = %s
                    and sp.state_kcs ='reject'
                    and picking_type_code ='production_in'
                    and sm.product_id = %s
        '''%(production_id,product_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty = i['product_qty'] or 0.0
        return qty
        
    
    def get_forproduct(self,production_id):
        val =[]
        sql ='''
            SELECT pp.id,sum(sp.total_qty) product_qty, pp.default_code
                FROM stock_picking sp join stock_move sm on sp.id = sm.picking_id
                 join product_product pp on sm.product_id = pp.id
                WHERE
                    sp.production_id = %s
                    and picking_type_code ='production_in'
                Group by pp.default_code,pp.id
            
        '''%(production_id)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            qty_kcsed = self.getproductkcs(production_id, i['id'])
            qty_reject = self.getproductreject(production_id, i['id'])
            val.append({
                        'name_template':i['default_code'],
                        'product_qty':i['product_qty'],
                        'qty_kcsed':qty_kcsed,
                        'qty_reject':qty_reject,
                        'qty':i['product_qty'] - qty_kcsed - qty_reject
            })
        return val
            
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.from_date = wizard_data['start_date'] or False
        self.to_date = wizard_data['end_date'] or False
        self.production_shift = wizard_data['production_shift'] and wizard_data['production_shift'][0]  or False
        self.production_id = wizard_data['production_id'] and wizard_data['production_id'][0]  or False
        return True