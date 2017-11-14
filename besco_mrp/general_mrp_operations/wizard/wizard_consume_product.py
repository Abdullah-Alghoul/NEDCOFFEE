# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools import float_compare
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time
from datetime import datetime, timedelta

class wizard_consume_product(osv.osv_memory):
    _name = "wizard.consume.product"
    _description = "Consume Products"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', required=True),
        'product_uom': fields.many2one('product.uom', 'Uom', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'move_id': fields.many2one('stock.move', 'Consume Move'),
    }

    def default_get(self, cr, uid, fields, context=None):
        move_pool = self.pool.get('stock.move')
        if context is None:
            context = {}
        res = super(wizard_consume_product, self).default_get(cr, uid, fields, context=context)
        move_id = context['active_id']
        move = move_pool.browse(cr, uid, move_id, context=context)
        
        if 'move_id' in fields:
            res.update({'move_id': move_id})
        if 'product_id' in fields:
            res.update({'product_id': move.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': move.product_uom.id})
        if 'location_id' in fields:
            res.update({'location_id': move.location_dest_id.id})
            
        new_qty = product_uom_qty = 0.0
        if 'product_qty' in fields:
            consume_move_ids = move_pool.search(cr, uid, [('consume_move_id', '=', move_id)])
            if consume_move_ids:
                for consume_move in move_pool.browse(cr, uid, consume_move_ids):
                    if consume_move.product_uom_qty:
                        product_uom_qty += consume_move.product_uom_qty or 0.0
            new_qty = move.product_uom_qty - product_uom_qty or 0.0
            res.update({'product_qty': new_qty})
        return res

    def do_move_consume(self, cr, uid, ids, context=None):
        move = self.pool.get('stock.move')

        if context is None:
            context = {}
        for this in self.browse(cr, uid, ids):
            move_obj = move.browse(cr, uid, context['active_id'], context=context)
            
            vals = {'name': this.product_id.name or '', 'product_id': this.product_id.id or False, 'price_unit': 0.0,
                    'product_uom': this.product_uom.id or False, 'product_uom_qty': this.product_qty or 0.0,
                    'location_id': this.location_id.id or False, 'production_id': move_obj.production_id.id or False,
                    'location_dest_id': this.product_id.property_stock_production.id or False, 'consume_move_id': context['active_id'],
                    'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                    'company_id': move_obj.company_id.id, 'state':'done', 'scrapped': False, 'warehouse_id': move_obj.warehouse_id.id or False}
            new_id = move.create(cr, uid, vals, context=context)
            cr.execute('''INSERT INTO mrp_production_consumed_products_move_ids (production_id,move_id) VALUES (%s,%s)
                ''' % (move_obj.production_id.id, new_id))
            
            move.write(cr, uid, [context['active_id']], {'qty_consume': this.product_qty})
        return {'type': 'ir.actions.act_window_close'}
