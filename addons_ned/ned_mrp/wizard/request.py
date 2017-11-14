
# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizard_stock_picking(models.TransientModel):
    _inherit = "wizard.stock.picking"
    
    bag_qty = fields.Float(string="bag Qty",digits=(12, 0))
    real_mc = fields.Float(string="Real MC",digits=(12, 2))
    real_weight = fields.Float(string="Real Wweight",digits=(12, 0))
    
    @api.multi
    def button_create_picking_consumable(self):
        for this in self:
            active_id = self._context.get('active_ids')
            result_obj = self.env['request.materials.line'].browse(active_id)
#             if this.state =='cancel':
#                 raise UserError(u'Request Have been Canceled')
            if this.product_qty > result_obj.product_qty -result_obj.basis_qty:
                raise UserError(u'Request Qty is over')
            result_obj = self.env['request.materials.line'].browse(active_id)
            company = self.env.user.company_id.id or False
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            var = {
               'real_mc':this.real_mc,
               'real_weight':this.real_weight,
               'name': '/', 
               'picking_type_id': self.picking_type_id.id, 
               'min_date': self.date or False, 
               'date_done':self.date, 
               'partner_id': False, 
               'picking_type_code': self.picking_type_id.code or False,
               'location_id': self.location_id.id or False, 
               'production_id': self.production_id.id or False, 
               'location_dest_id': self.location_dest_id.id or False,
               'request_materials_id':this.request_materials_id.id,
               'state':'draft'
            }  
            
            new_id = self.env['stock.picking'].create(var)
            product_uom_qty =0.0
            if this.stack_id:
                product_uom_qty = round(this.product_qty - (this.product_qty * abs(this.stack_id.avg_deduction/100)),0)
            else:
                product_uom_qty = this.product_qty
                
            name = '[' + this.product_id.default_code + '] ' + this.product_id.name or '' 
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': this.product_id.uom_id.id or False,
                'product_uom_qty': product_uom_qty or 0.0, 
                'init_qty': this.product_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': self.picking_type_id.id or False,
                'location_id': self.location_id.id or False,
                'date_expected': self.date or False, 'partner_id': False,
                'location_dest_id': self.location_dest_id.id or False,
                'type': self.picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': this.stack_id.zone_id.id or False, 
                'product_id': this.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'state':'draft', 
                'warehouse_id': warehouse_id.id or False,
                'stack_id':this.stack_id.id,
                'bag_no':this.bag_qty
                
                })
            result_obj.write({'picking_ids': [(4, new_id.id)]})
            new_id.action_done()
            result_obj = self.env['request.materials.line'].browse(active_id)
            if result_obj.product_qty == result_obj.basis_qty:
                result_obj.request_id.state = 'done'
            
        return True
    
    @api.model
    def default_get(self, fields):
        res = {}
        active_ids = self._context.get('active_ids')
        if active_ids:
            warehouse_id = self.env['stock.warehouse'].search([('name', '=', 'Factory - BMT')], limit=1)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id.id)
            
            for active in active_ids:
                result_obj = self.env['request.materials.line'].browse(active)
                if result_obj.request_id.type == 'consu':
                    picking_type_id = warehouse.production_out_type_consu_id.id or False
                else:
                    picking_type_id = warehouse.production_out_type_id.id or False
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                
                
                if result_obj.state =='cancel':
                    raise UserError(u'Request Have been Canceled')
                res = {'picking_type_id': picking_type_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   'production_id': result_obj.request_id.production_id.id or False,
                   'location_id': picking_type.default_location_src_id.id or False, 
                   'product_qty':result_obj.product_qty -result_obj.basis_qty,
                   'basis_qty':result_obj.basis_qty,
                   'product_id':result_obj.product_id.id,
                   'stack_id':result_obj.stack_id.id,
                   'request_materials_id':result_obj.request_id.id,
                   'location_dest_id': picking_type.default_location_dest_id.id or False}
                 
        return res
    
    