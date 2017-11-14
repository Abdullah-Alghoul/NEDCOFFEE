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
            'get_line':self.get_line,
            'get_total_qty':self.get_total_qty,
            'getmo_name':self.getmo_name
        })
    
    def get_line(self,this):
        vark =[]

        sql ='''
            SELECT id ,name
            FROM mrp_production
            WHERE state ='done'
                and date(timezone('UTC',date_planned::timestamp)) between '%s' and '%s'
        '''%(this.name.date_start,this.name.date_stop)
        self.cr.execute(sql)
        for line in this.production_order_ids:
            varGrp =[]
            varGrn =[]
            
            tm= {
                'grp_default_code':'',
                'grp_mo_name':'',
                'grn_mo_name':'',
                'grp':'',
                'grp_init_qty':'',
                'grp_product_uom_qty':'',
                'grp_date':'',
                'grn':'',
                'grn_init_qty':'',
                'grn_product_uom_qty':'',
                'grn_date':'',
                'grn_default_code':''
            }
            vark.append(tm)
            
            sql='''
                SELECT sp.date_done grn_date,pp.default_code,
                    sp.name grn,sm.init_qty grn_init_qty,sm.product_uom_qty grn_product_uom_qty
                    FROM stock_move  sm
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'internal'
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'internal' 
                        join stock_picking sp on sm.picking_id = sp.id
                        join product_product pp on pp.id = sm.product_id
                    where 
                        sm.production_id = %s
                        and sm.state ='done'
                        and product_uom_qty !=0
                        and init_qty !=0
                        and pp.default_code not in ('FR','GTR-13B2','GTR-13B3','GTR-16B2','GTR-16B3','GTR-18B2','GTR-18B3','HUSKS','PCR','STONES','WP Dust')
            '''%(line['id'])
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                varGrn.append({
                    'grn_mo_name':line['name'],
                    'grn':i['grn'],
                    'grn_init_qty':i['grn_init_qty'],
                    'grn_product_uom_qty':i['grn_product_uom_qty'],
                    'grn_date':self.get_date(i['grn_date']),
                    'grn_default_code':i['default_code']
                })
            
            
            sql='''
                SELECT sp.name picking_name, init_qty grp_init_qty,product_uom_qty grp_product_uom_qty,sm.date grp_date,pp.default_code
                FROM stock_move  sm 
                    join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'production'
                    join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'internal'
                    join stock_picking sp on sm.picking_id = sp.id
                    join product_product pp on sm.product_id = pp.id
                where sm.production_id = %s
                    and sm.state ='done'
                    and product_uom_qty !=0
                    and init_qty !=0
                    and pp.default_code not in ('FR','GTR-13B2','GTR-13B3','GTR-16B2','GTR-16B3','GTR-18B2','GTR-18B3','HUSKS','PCR','STONES','WP Dust')
            '''%(line['id'])
            self.cr.execute(sql)
            for i in self.cr.dictfetchall():
                varGrp.append({
                    'grp_default_code':i['default_code'],
                    'grp_mo_name':line['name'],
                    'grp':i['picking_name'],
                    'grp_init_qty':i['grp_init_qty'],
                    'grp_product_uom_qty':i['grp_product_uom_qty'],
                    'grp_date':self.get_date(i['grp_date'])
                })
            if len(varGrn) > len(varGrp):
                for i in varGrn:
                    if varGrp:
                        i.update(varGrp.pop())
                        vark.append(i)
                    else:
                        Grn_tm ={
                            'grp_default_code':'',
                            'grp_mo_name':line['name'],
                            'grp':'',
                            'grp_init_qty':'',
                            'grp_product_uom_qty':'',
                            'grp_date':''
                        }
                        i.update(Grn_tm)
                        vark.append(i)
            else:
                for i in varGrp:
                    if varGrn:
                        i.update(varGrn.pop())
                        vark.append(i)
                    else:
                        Grn_tm ={
                            'grn_mo_name':line['name'],
                            'grn':'',
                            'grn_init_qty':'',
                            'grn_product_uom_qty':'',
                            'grn_date':'',
                            'grn_default_code':''
                        }
                        i.update(Grn_tm)
                        vark.append(i)
                    
        
        return vark
    
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')

    
    def get_total_qty(self,this):
        
        total_qty = 0
        for i in this.premium_ids:
            total_qty += i.product_qty 
        
        return total_qty
    
    def getmo_name(self,grn_mo,grp_mo):
        if grn_mo:
            return grn_mo
        else:
            return grp_mo
        
        
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
