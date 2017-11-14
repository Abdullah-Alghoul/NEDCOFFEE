# -*- coding: utf-8 -*-
from datetime import datetime

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
from openerp.exceptions import UserError

from lxml import etree
import base64
import xlrd


class stock_onhand_report(osv.osv):
    _name = "stock.onhand.report"
    _description = "Stock Onhand Report"
    _auto = False
    
    _columns = {
            'location_name':fields.char(string="Location Name"),
            'location_id':fields.many2one('stock.location','Location'),
            'product_id':fields.many2one('product.product','Product'),
            'onhand':fields.float('On hand'),
            'val':fields.float('Values'),
            'uom_id':fields.many2one('product.uom','UoM'),
            'categ_id':fields.many2one('product.category','Product Category'),
    }
    def init(self, cr):
        cr.execute("""        
        create or replace view stock_onhand_report as 
        (
             SELECT ROW_NUMBER() OVER() id, location_id, location_name, 
               pc.seq, pt.categ_id, foo.product_id, pt.name, uom.id as uom_id,
               sum(onhand_qty) as onhand,sum(price_unit * onhand_qty) val
            FROM
            (
                select stm.product_id,
                case when loc2.usage = 'internal'
                then loc2.name
                else
                case when loc1.usage = 'internal'
                    then loc1.name
                else '' end
                end location_name,              
                case when loc2.usage = 'internal'
                then loc2.id
                else
                case when loc1.usage = 'internal'
                    then loc1.id
                else null end
                end location_id,                
                case when (loc2.usage = 'internal')
                then stm.product_qty
                else
                case when loc1.usage = 'internal'
                    then -1*stm.product_qty 
                else 0.0 end
                end onhand_qty,stm.date,
                stm.price_unit
                from stock_move stm 
                join stock_location loc1 on stm.location_id=loc1.id
                join stock_location loc2 on stm.location_dest_id=loc2.id
                left join stock_picking sp on sp.id = stm.picking_id
                where stm.state ='done'
            ) foo
                join product_product p on foo.product_id = p.id
                join product_template pt on p.product_tmpl_id=pt.id
                join product_uom uom on pt.uom_id=uom.id
                join product_category pc on pt.categ_id = pc.id               
            GROUP BY  location_name, pc.seq, pt.categ_id, foo.product_id, pt.name, uom.id,location_id            
            HAVING coalesce(sum(onhand_qty),0) != 0
            ORDER bY pc.seq        
        )
        """)
stock_onhand_report()