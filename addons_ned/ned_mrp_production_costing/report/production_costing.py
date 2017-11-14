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
        self.picking_id =[]
        self.getkiemtras = []
        self.localcontext.update({
            'get_allocation':self.get_allocation,
            'get_nvp':self.get_nvp,
            'get_currencyen':self.get_currencyen,
            'get_grn':self.get_grn,
            'get_stock_allocation':self.get_stock_allocation,
            'getkiemtra':self.getkiemtra,
            'get_line':self.get_line
        })
    
    def get_line(self,line):
        return line
    
    def get_stock_allocation(self,picking_id):
        return self.pool.get('stock.picking').browse(self.cr,SUPERUSER_ID,picking_id).allocation_ids
    
    def getkiemtra(self,production):
        allocation_ids =[]
        contract_ids = []
        for line in production:
            for i in line.direct_materials_ids:
                for j in i.material_ids:
                    for k in j.allocation_ids:
                        allocation_ids.append(k.id)
        sql ='''
            SELECT id 
                FROM stock_move_allocation 
                WHERE id in (%s)
                order by in_date
        '''%(','.join(map(str, allocation_ids)))
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            grn = ''
            grn_qty =0.0
            allocation = self.pool.get('stock.move.allocation').browse(self.cr,self.uid,i['id'])
            stock_allocation = self.pool.get('stock.allocation').search(self.cr,self.uid,[('contract_id','=',allocation.picking_id.purchase_contract_id.id)],limit =1)
            if stock_allocation:
                allocated = self.pool.get('stock.allocation').browse(self.cr,self.uid,stock_allocation[0])
                grn = allocated.picking_id and allocated.picking_id.name or ''
                grn_qty = allocated.picking_id.total_qty or 0.0
            else:
                npe = allocation.picking_id.purchase_contract_id.nvp_ids and allocation.picking_id.purchase_contract_id.nvp_ids[0].npe_contract_id
                stock_allocation = self.pool.get('stock.allocation').search(self.cr,self.uid,[('contract_id','=',npe.id)],limit =1)
                if stock_allocation:
                    allocated = self.pool.get('stock.allocation').browse(self.cr,self.uid,stock_allocation[0])
                    grn = allocated.picking_id and allocated.picking_id.name or ''
                    grn_qty = allocated.picking_id.total_qty or 0.0
                
            
            contract_ids.append({
                'in_date':allocation.in_date,
                'pick':allocation.picking_id.name,
                'grn':grn,
                'grn_qty':grn_qty or 0.0,
                'contract_name':allocation.picking_id.purchase_contract_id.name,
                'fixed_qty':allocation.picking_id.purchase_contract_id.qty_received or 0.0,
                'allocated_qty':allocation.allocated_qty,
                'allocated_value':allocation.allocated_value,
                'product_id':allocation.product_id.name,
                })
        self.getkiemtras = contract_ids
        return contract_ids
        
    def get_grn(self,mrps):
        stack = []
        grn = []
        for mrp in mrps:
            for move in mrp.name.move_lines:
                if move.stack_id.id in stack:
                    continue
                stack.append(move.stack_id.id)
        if stack:
            sql = '''
                SELECT sp.id picking_id,sp.name picking_name,pp.name_template ,uom.name uom_name,init_qty,product_uom_qty
                FROM stock_move sm 
                    join stock_location sl1 on sm.location_id = sl1.id and sl1.usage ='supplier'
                    join stock_location sl2 on sm.location_dest_id = sl2.id and sl2.usage = 'procurement'
                    join stock_picking sp on sm.picking_id = sp.id
                    join product_product pp on sm.product_id = pp.id
                    join product_uom uom on sm.product_uom = uom.id
                WHERE sm.stack_id in (%s)
            '''%(','.join(map(str, stack)))
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                grn.append({
                    'picking_id':i['picking_id'],
                    'picking_name':i['picking_name'],
                    'name_template':i['name_template'],
                    'uom_name':i['uom_name'],
                    'begin_qty':0,
                    'trans_qty':0,
                    'init_qty':i['init_qty'],
                    'product_uom_qty':i['product_uom_qty']
                            })
                self.picking_id.append(i['picking_id'])
            sql = '''
                SELECT sp.id picking_id,sp.name picking_name,pp.name_template ,uom.name uom_name,init_qty,product_uom_qty
                FROM stock_move sm 
                    join stock_location sl1 on sm.location_id = sl1.id and sl1.usage ='transit'
                    join stock_location sl2 on sm.location_dest_id = sl2.id and sl2.usage = 'procurement'
                    join stock_picking sp on sm.picking_id = sp.id
                    join product_product pp on sm.product_id = pp.id
                    join product_uom uom on sm.product_uom = uom.id
                WHERE sm.stack_id in (%s)
            '''%(','.join(map(str, stack)))
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                origin  = ''
                begin_qty = ''
                trans_qty = ''
                picking_id = False
                pick = self.pool.get('stock.picking').browse(self.cr,1,i['picking_id'])
                for trans in pick.picking_transfer_internal_ids:
                    origin  = trans.origin or ''
                    begin_qty = trans.move_lines[0].init_qty
                    trans_qty = trans.total_qty
                    for transs in trans.picking_transfer_internal_ids:
                        picking_id = transs.id
                        
                        
                
                grn.append({
                            'picking_id':picking_id,
                            'picking_name':origin,
                            'name_template':i['name_template'],
                            'uom_name':i['uom_name'],
                            'begin_qty':begin_qty,
                            'trans_qty':trans_qty,
                            'init_qty':i['init_qty'],
                            'product_uom_qty':i['product_uom_qty']
                            })
            
            return grn
            
        
    def get_currencyen(self,origin,amount):
        users = self.pool.get('res.users').browse(self.cr, self.uid,1)
        sql ='''
            Select date(timezone('UTC',date::timestamp))  date
            FROM stock_picking 
            WHERE origin= '%s'
        '''%(origin)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            date = i['date']
        a = users.company_id.second_currency_id.with_context(date=date).compute(amount,  users.company_id.currency_id)
        return users.company_id.second_currency_id.with_context(date=date).compute(amount,  users.company_id.currency_id)
    
    def get_nvp(self,period):
        nvp_ids =[]
        sql ='''
            select id from purchase_contract 
            WHERE
                date_order between '%s' and '%s'
                and type ='purchase'
            order by date_order ,name
        '''%(period.date_start,period.date_stop)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            nvp_ids.append(i['id'])
        return self.pool.get('purchase.contract').browse(self.cr,self.uid,nvp_ids)
            
            
    def get_allocation(self, line):
        if not line:
            return {}
        res =[]
        move_ids =[]
        for i in line:
            for j in i.material_ids:
                if not j.move_id.id:
                    continue
                move_ids.append(j.move_id.id)
        if move_ids:
            sql ='''
                SELECT sml.in_date,sp.name picking_name,pp.name_template,sml.allocated_qty,sml.allocated_value,
                    sp.origin
                FROM
                    stock_move_allocation  sml 
                    join product_product pp on pp.id =sml.product_id
                    left join stock_picking sp on sml.picking_id = sp.id
                WHERE to_move_id in (%s)
                order by sml.in_date,sp.name
            '''%(','.join(map(str, move_ids)))
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                res.append({
                   'origin':i['origin'],
                   'in_date':i['in_date'],
                   'picking_name':i['picking_name'],
                   'name_template':i['name_template'],
                   'allocated_qty':i['allocated_qty'],
                   'allocated_value':i['allocated_value']
               })
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
