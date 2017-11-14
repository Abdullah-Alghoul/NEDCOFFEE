# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_request_materials(models.TransientModel):
    _name = "wizard.request.materials"
    
    production_id = fields.Many2one('mrp.production',string ='Manufacturing Orders')
    request_date = fields.Date(string='Date')
    warehouse_id = fields.Many2one('stock.warehouse',string ='Warehouse')
    request_line = fields.One2many('wizard.request.materials.line','request_id',string="Request Line")
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars=[]
        active_id = self._context.get('active_id')
        if active_id:
            production_obj = self.env['mrp.production'].browse(active_id)
            res = {'production_id': active_id, 'request_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   'warehouse_id':production_obj.warehouse_id.id}
            for line in production_obj.product_lines:
                vars.append((0, 0, {'product_id':line.product_id.id, 'product_uom':line.product_uom.id,'product_qty' :line.product_qty}))
            res.update({'request_line':vars})
        return res
    
    @api.multi
    def button_request(self):
        for production in self:
            if not production.request_line:
                raise UserError(_("Materials is not Null"))
            for line in production.request_line:
                if line.product_qty == 0:
                    raise UserError(_("Request Qty is not Null"))
            val ={
                  'production_id':production.production_id.id,
                  'request_user_id':self.env.uid,
                  'state':'draft'
                }
            request_id = self.env['request.materials'].create(val)
            
            for line in production.request_line:
                vals ={
                    'product_id':line.product_id.id,
                    'product_uom':line.product_uom.id,
                    'product_qty':line.product_qty or 0.0,
                    'request_id':request_id.id
                    }
                self.env['request.materials.line'].create(vals)
            
            
            
            val ={
                  'picking_type_id':request_id.warehouse_id.production_out_type_id.id,
                  'location_id':request_id.warehouse_id.production_out_type_id.default_location_src_id.id,
                  'location_dest_id':request_id.warehouse_id.production_out_type_id.default_location_dest_id.id,
                  'production_id':request_id.production_id.id,
                  'origin':request_id.name or '',
                  'request_materials_id':request_id.id
                  }
            picking_id = self.env['stock.picking'].create(val)
            request_id.picking_id = picking_id
            for line in request_id.request_line:
                vals ={
                       'name': line.product_id.name or '',
                       'picking_id':picking_id.id,
                       'product_id':line.product_id.id,
                       'product_uom_qty':line.product_qty,
                       'product_uom':line.product_uom.id,
                       'state':'draft',
                       'location_id': picking_id.location_id.id,
                       'location_dest_id': picking_id.location_dest_id.id,
                       'type': request_id.warehouse_id.production_in_type_id.code,
                       'state':'draft',
                       'scrapped': False,
                       'warehouse_id':request_id.warehouse_id.id,
                       
                   }
                self.env['stock.move'].create(vals)
            request_id.state = 'approved'
                

class wizard_request_materials_line(models.TransientModel):
    _name = "wizard.request.materials.line"
    

    request_id = fields.Many2one('wizard.request.materials',string ='Request')
    product_id = fields.Many2one('product.product',string ='Product')
    product_uom = fields.Many2one('product.uom',string ='UoM')
    product_qty = fields.Float(string ='Qty',digits=(16, 0))
    #product_qty = fields.Float(related='stack_id.remaining_qty',string ='Qty',digits=(16, 0))
    
