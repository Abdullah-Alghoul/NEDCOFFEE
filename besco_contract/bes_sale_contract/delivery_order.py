# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from lxml import etree
import time
from openerp import SUPERUSER_ID

class DeliveryOrder(models.Model):
    _name = "delivery.order"
    _order = 'id desc'
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id 
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')],
             string='Status', readonly=True, copy=False, index=True, default='draft')
    
    date = fields.Date(string='Date', readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    trucking_id = fields.Many2one('res.partner', string='Trucking Co', readonly=True, required=False, states={'draft': [('readonly', False)]})
    transrate = fields.Float(string='Trans Rate', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, readonly=True, states={'draft': [('readonly', False)]})
    picking_type_id = fields.Many2one("stock.picking.type", string="Reason", readonly=True, required=False, states={'draft': [('readonly', False)]})
    
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True, states={'draft': [('readonly', False)]})
    vehicle_manufacture = fields.Char(string="Vehicle Manufacture", readonly=True, states={'draft': [('readonly', False)]})
    trucking_no = fields.Char(string="Trucking No.", readonly=True, states={'draft': [('readonly', False)]})
    driver_name = fields.Char(string="Driver's Name", readonly=True, states={'draft': [('readonly', False)]})
    registration_certificate = fields.Char(string="Registration Certificate", readonly=True, states={'draft': [('readonly', False)]})
    company_ref_guide = fields.Char(string="Company Ref. Guide", readonly=True, states={'draft': [('readonly', False)]})
    transporter_ref_guide = fields.Char(string="Transporter Ref. Guide", readonly=True, states={'draft': [('readonly', False)]})
    
    contract_id = fields.Many2one("sale.contract", string="Contract No.", required=False, readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')
    markings = fields.Text(string="Markings", readonly=True, states={'draft': [('readonly', False)]})
    reason = fields.Text(string="Reason", readonly=True, states={'draft': [('readonly', False)]})
    picking_id = fields.Many2one("stock.picking", string="GDN No.")
#     invoice_state = fields.Selection(selection=[("invoiced", "Invoiced"), ("2binvoiced", "To Be Invoiced"), ("none", "Not Applicable")],
#                          related="picking_id.invoice_state", string="Invoice Control", readonly=True, copy=False, store=True, default="2binvoiced")          
    
    delivery_order_ids = fields.One2many('delivery.order.line', 'delivery_id', string="DO Lines", readonly=True, states={'draft': [('readonly', False)]})
    post_shippemnt_ids = fields.One2many('post.shipment', 'do_id', string="Post Shippment", readonly=True, states={'draft': [('readonly', False)]})
    date_out = fields.Date(string='Date out', readonly=False, index=True,copy = False)
    received_date = fields.Date(string='Received date', readonly=False, index=True,copy = False)
    
    type= fields.Selection([('Sale', 'Sale'), ('Transfer', 'Transfer')],
             string='Type')
    
    @api.depends('delivery_order_ids','delivery_order_ids.product_qty')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.delivery_order_ids:
                total_qty += line.product_qty
            order.total_qty = total_qty
    
    
    
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Qty',store=True)
    product_id = fields.Many2one(related='delivery_order_ids.product_id',  string='Product',store=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', False):
            if vals.get('type',False) == 'Sale':
                vals['name'] = self.env['ir.sequence'].next_by_code('delivery.order')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('delivery.order.transfer')
        else:
            name = vals.get('name', False)
            do_ids = self.search([('name', '=', name)])
            if len(do_ids) >= 1:
                raise UserError(_("Delivery Orders (%s) was exist.") % (name))
        result = super(DeliveryOrder, self).create(vals)
        return result
    
    @api.multi
    def unlink(self):
        if self.state not in ('draft', 'approved', 'cancel'):
            raise UserError(_('You cannot delete a Delivery Order approved.'))
        
        picking_pool = self.env['stock.picking']
        picking_id = picking_pool.search([('delivery_id', '=', self.id)])
        if picking_id:
#             if picking_id.invoice_state == 'invoiced':
#                 raise UserError(_('You cannot delete a Delivery Order has an invoice.'))
        
            self.env.cr.execute('''DELETE FROM stock_pack_operation WHERE picking_id = %(picking_id)s;
                DELETE FROM stock_move WHERE picking_id = %(picking_id)s;
                DELETE FROM stock_picking WHERE id = %(picking_id)s; ''' % ({'picking_id': picking_id.id}))
        return super(DeliveryOrder, self).unlink()
    
    
    @api.multi
    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if not self.warehouse_id:
            return
        domain = {'picking_type_id': [('id', '=', self.warehouse_id.out_type_id.id)]}
        values = {'picking_type_id': self.warehouse_id.out_type_id.id or False}
        self.update(values)
        return {'domain': domain}
    
    @api.multi
    def button_load_do(self):
        if self.contract_id: 
            self.env.cr.execute('''DELETE FROM delivery_order_line WHERE delivery_id = %s''' % (self.id))
            product_qty = new_qty = 0.0
            for contract in self.contract_id.contract_line:
                for do in self.contract_id.delivery_ids:
                    if do.state != 'cancel':
                        for do_line in do.delivery_order_ids:
                            if do_line.product_id == contract.product_id:
                                product_qty += do_line.product_qty
                new_qty = contract.product_qty - product_qty 
                var = {'delivery_id': self.id, 'name': contract.name, 'product_id': contract.product_id.id,
                       'product_qty': new_qty, 'product_uom': contract.product_uom.id, 'state': 'draft'}
                self.env['delivery.order.line'].create(var)
        return True
    
    @api.multi
    def button_draft(self):
        if self.state == 'approved':
            picking_id = self.picking_id
#             if picking_id and picking_id.invoice_state == 'invoiced':
#                 raise UserError(_('Unable to cancel Delivery Order %s.') % (self.name))
            if picking_id.state not in ('confirmed','assigned','done'):
                picking_id.unlink()
            else:
                raise UserError(_('Unable to cancel Delivery Order %s.') % (self.name))
        self.write({'state': 'draft'})
        
        
    @api.multi
    def button_approve(self):
        if not self.delivery_order_ids:
            raise UserError(_('You cannot approve a Delivery Order without any Delivery Order Lines.'))
        
        var = {'name': '/', 'picking_type_id': self.picking_type_id.id or False, 'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
           'partner_id': self.partner_id.id or False, 
#            'invoice_state': self.picking_type_id.invoice_state or False, 
           'picking_type_code': self.picking_type_id.code or False,
           'location_id': self.picking_type_id.default_location_src_id.id or False, 
           'sale_contract_id': self.contract_id.id or False,
           'location_dest_id': self.picking_type_id.default_location_dest_id.id or False, 
           'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
        picking_id = self.env['stock.picking'].create(var)  
        self.picking_id = picking_id
        for line in self.delivery_order_ids:
            self.env['stock.move'].create({'picking_id': picking_id.id or False, 'name': line.name or '', 'product_id': line.product_id.id or False,
                'product_uom': line.product_uom.id or False, 'product_uom_qty': line.product_qty or 0.0, 'price_unit': line.price_unit or 0.0,
                'out_stock_wti': line.product_qty or 0.0, 'picking_type_id': self.picking_type_id.id or False, 'currency_id': self.currency_id.id or False,
                'location_id': self.picking_type_id.default_location_src_id.id or False, 'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'location_dest_id': self.picking_type_id.default_location_dest_id.id or False, 'type': self.picking_type_id.code or False,
                'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'partner_id': self.partner_id.id or False,
                'company_id': self.contract_id.company_id.id, 'state':'draft', 'scrapped': False, 'warehouse_id': self.warehouse_id.id or False})
        
        received_date = False
        sql ='''
            SELECT '%s'::date +1 as date
        '''%(datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT))
             
        self.env.cr.execute(sql)
        for date in self.env.cr.dictfetchall():
            received_date = date['date'] or 0.0
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_out':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'received_date':received_date,
                     'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                    
    @api.multi
    def button_done(self):
        picking_pool = self.env['stock.picking']
        picking_id = picking_pool.search([('delivery_id', '=', self.id)])
        if not picking_id:
            raise UserError(_('You cannot done a Delivery Order without a GDN.'))
        self.write({'state': 'done'})
        
        
class DeliveryOrderLine(models.Model):
    _name = "delivery.order.line"
        
    name = fields.Text(string='Description', required=True)
    delivery_id = fields.Many2one('delivery.order', string='Delivery Order', ondelete='cascade', index=True, copy=False)
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'), ('cancel', 'Cancelled')],
          related='delivery_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, required=True)
    product_qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='Uom', required=True)  
    price_unit = fields.Float('Unit Price', default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')  
    
