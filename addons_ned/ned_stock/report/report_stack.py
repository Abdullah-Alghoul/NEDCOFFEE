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
        self.grn_net_qty = 0
        self.grn_basis_qty = 0
        self.gip_net_qty = 0
        self.gip_basis_qty = 0
        self.localcontext.update({
            'get_gip':self.get_gip,
            'get_grn':self.get_grn,
            'sum_grn_net_qty':self.sum_grn_net_qty,
            'sum_grn_basis_qty':self.sum_grn_basis_qty,
            'sum_gip_net_qty':self.sum_gip_net_qty,
            'sum_gip_basis_qty':self.sum_gip_basis_qty,
        })
    
    
    def sum_grn_net_qty(self):
        return self.grn_net_qty
    
    def sum_grn_basis_qty(self):
        return self.grn_basis_qty
    
    def sum_gip_net_qty(self):
        return self.gip_net_qty
    
    def sum_gip_basis_qty(self):
        return self.gip_basis_qty
    
    def get_gip(self,move_ids):
        val =[]
        for line in move_ids:
            if line.date>= '2017-03-01 00:00:00' and line.state == 'done' and line.location_dest_id.id != 61:
                
                self.gip_net_qty += line.init_qty
                self.gip_basis_qty += line.product_uom_qty
                val.append({
                    'date':line.date,
                    'gip':line.picking_id.name,
                    'product':line.product_id.default_code,
                    'net_qty':line.init_qty,
                    'basis_qty':line.product_uom_qty
                    })
        return val
    
    def get_grn(self,move_ids):
        val =[]
        for line in move_ids:
            if line.state == 'done' and line.location_dest_id.id == 61:
                self.grn_net_qty += line.init_qty
                self.grn_basis_qty += line.product_uom_qty
                val.append({
                    'date':line.date,
                    'gip':line.picking_id.name,
                    'product':line.product_id.default_code,
                    'net_qty':line.init_qty,
                    'basis_qty':line.product_uom_qty
                    })
        return val