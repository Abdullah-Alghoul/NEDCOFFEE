# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    @api.depends('request_ids')
    def _compute_requests(self):
        for mrp in self:
            requests = self.env['request.materials']
            for line in mrp.request_ids: 
                requests =  (line.filtered(lambda r: r.state != 'cancel'))
            mrp.request_ids = requests
            mrp.request_count = len(requests)
    
    request_count = fields.Integer(compute='_compute_requests', string='Receptions', default=0)
    request_ids = fields.One2many('request.materials', 'production_id', string='Request Materials', copy=False)
    
    @api.multi
    def button_request_materials(self):
        for production in self:
            if not production.product_lines:
                raise UserError(_("Materials is not Null"))
            
            val ={
                  'production_id':production.id,
                  'request_user_id':self.env.uid,
                  'state':'draft'
                }
            request_id = self.env['request.materials'].create(val)
            
            for line in production.product_lines:
                vals ={
                    'product_id':line.product_id.id,
                    'product_uom':line.product_uom.id,
                    'product_qty':line.product_qty or 0.0,
                    'request_id':request_id.id
                    }
                self.env['request.materials.line'].create(vals)
            
        return
    
    @api.multi
    def action_view_request(self):
        request_ids = self.mapped('request_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('general_mrp_operations.action_request_materials')
        list_view_id = imd.xmlid_to_res_id('general_mrp_operations.view_request_materials_tree')
        form_view_id = imd.xmlid_to_res_id('general_mrp_operations.view_request_materials_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(request_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % request_ids.ids
        elif len(request_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = request_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
class RequestMaterials(models.Model):
    _name = "request.materials"
    _description = "Request Materials"
    _order = 'id desc'
    
    name = fields.Char(string="Request")
    production_id = fields.Many2one('mrp.production', string='Manufacturing Orders',
       readonly=True, states={'draft': [('readonly', False)]}, required=False,)
    
    warehouse_id = fields.Many2one(related='production_id.warehouse_id', string='Warehouse', readonly=True,store=True)
    request_date = fields.Date("Request Date",default=fields.Datetime.now)
    request_user_id = fields.Many2one('res.users', string='Request Users',
       readonly=True, states={'draft': [('readonly', False)]}, required=False,default=lambda self: self._uid)
    request_line = fields.One2many('request.materials.line', 'request_id', string='Request Lines', 
                       readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    origin= fields.Char('Origin')
    notes = fields.Text(string='Notes')
    state = fields.Selection([('draft', 'New'),('scale','Scale'), ('approved', 'Approved'), ('done', 'Done'),('cancel','Canceled')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
    type = fields.Selection([('consu', 'Consumable'), ('mrp', 'Production')], string='Type',
                             default='mrp')
    
    def _total_qty(self):
        for order in self:
            total_qty = 0.0
            for line in order.request_line:
                total_qty += line.product_qty
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Qty')
    
    @api.model
    def create(self, vals):
        if vals.get('type',False) == 'consu':
            vals['name'] = self.env['ir.sequence'].next_by_code('request.materials.consu')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('request.materials')
        result = super(RequestMaterials, self).create(vals)
        return result
    
    @api.multi
    def button_draft(self):
        for request in self:
            if request.picking_id and request.picking_id.state !='draft':
                raise UserError(_("Picking (%s) was approved") % (request.picking_id.name))
            request.picking_id.unlink()
            self.state = 'draft'
            
    @api.multi
    def button_cancel(self):
        self.state = 'cancel'
    
    @api.multi
    def button_done(self):
        self.state = 'done'
                
    @api.multi
    def button_approve(self):
        for request in self:
            val ={
                  'picking_type_id':request.warehouse_id.production_out_type_id.id,
                  'location_id':request.warehouse_id.production_out_type_id.default_location_src_id.id,
                  'location_dest_id':request.warehouse_id.production_out_type_id.default_location_dest_id.id,
                  'production_id':request.production_id.id,
                  'origin':request.name or '',
                  }
            picking_id = self.env['stock.picking'].create(val)
            request.picking_id = picking_id
            for line in request.request_line:
                vals ={
                       'name': line.product_id.name or '',
                       'picking_id':picking_id.id,
                       'product_id':line.product_id.id,
                       'product_uom_qty':line.product_qty,
                       'product_uom':line.product_uom.id,
                       'state':'draft',
                       'location_id': picking_id.location_id.id,
                       'location_dest_id': picking_id.location_dest_id.id,
                       'type': request.warehouse_id.production_in_type_id.code,
                       'state':'draft',
                       'scrapped': False,
                       'warehouse_id':request.warehouse_id.id,
                       
                   }
                self.env['stock.move'].create(vals)
                self.state = 'approved'
            
    
class RequestMaterialsLine(models.Model):
    _name = "request.materials.line"
    _description = "Request Materials Line"
    
    @api.depends('picking_ids')
    def _basis_qty(self):
        for picking in self:
            basis_qty = 0.0
            for line in picking.picking_ids:
                if line.state != 'done':
                    continue
                basis_qty +=line.total_init_qty 
            picking.basis_qty = basis_qty
            
    product_id = fields.Many2one('product.product', string='Product')
    product_uom = fields.Many2one('product.uom', string='UoM')
    product_qty = fields.Float( string='Product Qty',digits=(12, 0))
    request_id = fields.Many2one('request.materials', string='Request')
    picking_ids = fields.Many2many('stock.picking','picking_request_move_ref','picking_id','request_id','Picking')
    basis_qty = fields.Float(compute='_basis_qty', string='Basis Qty',digits=(12, 0))
    state = fields.Selection([('approved', 'Approved'),('cancel','Canceled')], string='Status',
                             readonly=True, copy=False, index=True, default='approved')
    
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not (self.product_uom and (self.product_id.uom_id.category_id.id == self.product_uom.category_id.id)):
            vals['product_uom'] = self.product_id.uom_id

        product = self.product_id.with_context(
            partner=self.contract_id.partner_id.id,
            quantity=self.product_qty,
            uom=self.product_uom.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name

        self.update(vals)
        return {'domain': domain}
    
    
    

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    request_materials_id = fields.Many2one('request.materials', string='Request Materials')
    
    