# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time
import math

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    production_id = fields.Many2one('mrp.production', string='Production Order', readonly=True, states={'draft': [('readonly', False)]})
    operation_id = fields.Many2one('mrp.production.workcenter.line', string='Operation', readonly=True, states={'draft': [('readonly', False)]})
    result_id = fields.Many2one('mrp.operation.result', string='Result', readonly=True)
    
    @api.multi
    def button_loading(self):
        moves = self.env['stock.move'] 
        vals = {}
        for this in self:
            if this.move_lines:
                self.env.cr.execute("DELETE FROM stock_move WHERE id in (SELECT id FROM stock_move WHERE picking_id = %s)" % (this.id))
            if this.picking_type_id.code == 'production_out':
                if this.production_id:
                    for i in this.production_id.product_lines:
                        vals = {'picking_id': this.id, 'name': i.product_id.name, 'product_id': i.product_id.id,
                                'production_id': this.production_id.id, 'product_uom': i.product_uom.id,
                                'product_uom_qty': i.product_qty, 'product_finished_goods':this.production_id.product_id.id,
                                'picking_type_id': self.picking_type_id.id, 'location_id': self.location_id.id,
                                'location_dest_id': self.location_dest_id.id, 'date': self.min_date,
                                'type': 'production_out', 'state': 'draft', 'scrapped': False}
                        moves.create(vals)
            if this.picking_type_id.code == 'production_in':
                if this.operation_id:
                    vals = {'picking_id': this.id, 'name': this.operation_id.product_id.name, 'product_id': this.operation_id.product_id.id,
                            'production_id': this.production_id.id, 'product_uom': this.operation_id.product_uom.id,
                            'product_uom_qty': this.operation_id.reached_qty, 'product_finished_goods': this.production_id.product_id.id,
                            'picking_type_id': self.picking_type_id.id, 'location_id': self.location_id.id,
                            'location_dest_id': self.location_dest_id.id, 'date': self.min_date,'type': self.picking_type_id.code, 'state': 'draft'}
                    moves.create(vals)
        return True
    
class StockMove(models.Model):
    _inherit = 'stock.move'
    
    product_finished_goods = fields.Many2one('product.product', string='Product Finished Goods', readonly=True, states={'draft': [('readonly', False)]})
    result_id = fields.Many2one('mrp.operation.result', string='Operation Result', readonly=True, states={'draft': [('readonly', False)]})
    operation_id = fields.Many2one('mrp.production.workcenter.line', string='Operation', readonly=True, states={'draft': [('readonly', False)]})
    consume_move_id = fields.Many2one('stock.move', string='Consume Mode', copy=False)

    
