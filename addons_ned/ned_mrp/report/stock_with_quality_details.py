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
        self.product_id = False
        self.type= False
        self.localcontext.update({
            'get_date':self.get_date,
            'get_line':self.get_line,
            'get_gdp_net':self.get_gdp_net,
            'get_balance_net':self.get_balance_net,
        })
    def get_balance_net(self,net,gdp_net,delivery_net):
        return net - (gdp_net + delivery_net)
        
    def get_gdp_net(self,grp):
        sql='''
            SELECT sum(init_qty) init_qty
            FROM
                stock_move 
            WHERE grp_id = %s
            and state ='done'
        '''%(grp)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return i['init_qty'] or 0.0
        return 0
    
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
    
    def get_line(self):
        self.get_header()
        res =[]
        if self.product_id:
            if self.type =='all':
                sql ='''
                    SELECT  id from stock_stack where product_id = %s
                '''%(self.product_id)
            else:
                sql ='''
                    SELECT  id from stock_stack where product_id = %s and init_qty!= 0 and remaining_qty != 0
                '''%(self.product_id)
        else:
            if self.type =='all':
                sql ='''
                        SELECT  id from stock_stack 
                    '''
            else:
                sql ='''
                        SELECT  id from stock_stack where init_qty!= 0 and remaining_qty != 0
                    '''
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            delivery_net = delivery_basis = 0.0
            gip_net= gip_basis = 0.0
            grp_net= grp_basis = 0.0
            remarks = ''
            packing_name = ''
            mc = immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = excelsa = cherry = mold = fm = black = brown = broken = 0.0
            stack = self.pool.get('stock.stack').browse(self.cr,self.uid,i['id'])
            count =0
            for pick in stack.move_ids:
                if pick.picking_type_id.code =='outgoing':
                    delivery_basis += pick.product_qty
                    delivery_net += pick.init_qty
                
                if pick.picking_type_id.code == 'production_out':
                    gip_net += pick.init_qty
                    gip_basis += pick.product_qty
                
                if pick.picking_type_id.code in ('production_in','transfer_in','incoming'):
                    grp_net += pick.init_qty
                    grp_basis += pick.product_qty
                    if pick.picking_id.note:
                        remarks += pick.picking_id.note +' '
                    packing_name = pick.packing_id and pick.packing_id.name or ''
                        
                
                if pick.picking_type_id.code in ('production_in','transfer_in','incoming'):
                    for line in pick.picking_id.kcs_line:
                        mc += line.mc  
                        fm += line.fm  
                        black += line.black  
                        broken += line.broken  
                        brown +=  line.brown  
                        mold += line.mold  
                        cherry += line.cherry  
                        excelsa += line.excelsa  
                        screen18 += line.screen18  
                        screen16 += line.screen16  
                        screen13 += line.screen13  
                        belowsc12 += line.belowsc12  
                        burned += line.burned  
                        eaten += line.eaten  
                        immature += line.immature 
                        count += 1
                        
            mc = count and mc/count or 0.0
            fm = count and fm/count or 0.0
            black = count and black/count or 0.0
            broken = count and broken/count or 0.0
            brown = count and brown/count or 0.0
            mold = count and mold/count or 0.0
            cherry = count and cherry/count or 0.0
            excelsa = count and excelsa/count or 0.0
            screen18 = count and screen18/count or 0.0
            screen16 = count and screen16/count or 0.0
            screen13 = count and screen13/count or 0.0
            belowsc12 = count and belowsc12/count or 0.0
              
            burned = count and burned/count or 0.0
            eaten = count and eaten/count or 0.0
            immature = count and immature/count or 0.0
#             stick_count = count and stick_count/count or 0.0
#             stone_count = count and stone_count/count or 0.0
                
                
                    
            res.append({
               #'source':picking.districts_id and picking.districts_id.name or '',
               #'batch_no':batch,
               'product':stack.product_id.default_code,
               'date_in':self.get_date(stack.date),
               'net_qty': grp_net, 
               'basis_qty':grp_basis,
               'zone':stack.zone_id.name,
               'stack':stack.name,
               'pledged':stack.pledged,
                'mc':mc,
                'fm':fm,
                'black':black,
                'broken':broken,
                'brown':brown,
                'mold':mold,
                'cherry': cherry,
                'screen18':screen18,
                'screen16':screen16,
                'screen13':screen13,
                'belowsc12':belowsc12,
                'burned':burned,
                'eaten':eaten,
                'immature':immature,
                'excelsa':excelsa,
#                'stick_count':kcs and kcs.stick_count,
#                'stone_count':kcs and kcs.stone_count,
               'note':remarks or '',
#                'maize_yn':kcs and kcs.maize_yn and 'Y' or 'N',
               'delivery_net':delivery_net,
               'delivery_basis':delivery_net,
               'balance_net':stack.init_qty,
               'balance_basis':stack.remaining_qty,
               'gdp_net':delivery_net,
               'gdp_basis':delivery_basis,
               'gip_net':gip_net,
               'gip_basis':gip_basis,
               'packing_name':packing_name
            })
        
        return res
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.production_id = wizard_data['production_id'] and wizard_data['production_id'][0] or False
        self.product_id = wizard_data['product_id'] and wizard_data['product_id'][0] or False 
        self.type = wizard_data['type']
        return True
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
