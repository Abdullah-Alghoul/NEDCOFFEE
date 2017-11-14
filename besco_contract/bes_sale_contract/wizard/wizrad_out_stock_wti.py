# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizrad_out_stock_wti(models.TransientModel):
    _name = "wizrad.out.stock.wti"
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, readonly=True)
    wizard_ids = fields.One2many('wizrad.out.stock.wti.line', 'wizard_id', 'Wizard Lines')
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            picking_obj = self.env['stock.picking'].browse(active_id)
            res = {'picking_id': active_id}
            for line in picking_obj.move_lines:
                vars.append((0, 0, {'move_id': line.id, 'product_id':line.product_id.id, 'product_uom':line.product_uom.id,
               'product_qty': line.product_uom_qty, 'out_stock_wti': line.product_uom_qty}))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_update(self):
        var = []
        active_id = self._context.get('active_id')
        if active_id:
           picking_obj = self.env['stock.picking'].browse(active_id)
           for line in self.wizard_ids:
               if line.out_stock_wti > line.product_qty:
                   raise UserError(_('Qty Received is not greater than the Product Qty %s at Product Name %s.') % (int(line.product_qty), line.product_id.name))
               line.move_id.write({'out_stock_wti': line.out_stock_wti})
        return True
    
class wizrad_out_stock_wti_line(models.TransientModel):
    _name = "wizrad.out.stock.wti.line"
    
    move_id = fields.Many2one('stock.move', string='Move')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure')
    product_qty = fields.Float(string='Qty', default=1.0)
    out_stock_wti = fields.Float(string='Out stock WTI', required=True, default=1.0)
    wizard_id = fields.Many2one('wizard.stock.move', 'Wizard stock.move', required=False, ondelete='cascade', index=True, copy=False)
    
    
    
