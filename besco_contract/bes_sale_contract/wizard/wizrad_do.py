# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizrad_do(models.TransientModel):
    _name = "wizard.do"
    
    name = fields.Char(string='Reference', required=True)
    contract_id = fields.Many2one('sale.contract', required=False, readonly=True)
    date = fields.Date(string='Date')
    transportation_cost = fields.Float(string='Transportation Cost', required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    wizard_ids = fields.One2many('wizard.do.line', 'wizard_id', 'Wizard Lines', required=False)
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            contract_obj = self.env['sale.contract'].browse(active_id)
            currency_id = self.env['res.currency'].search([('name', '=', 'VND')], limit=1)
            res = {'name': 'New', 'contract_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'currency_id': currency_id.id}
            product_qty = 0.0
            for line in contract_obj.contract_line:
                for do in contract_obj.delivery_ids:
                    if do.state != 'cancel':
                        for do_line in do.delivery_order_ids:
                            if line.product_id == do_line.product_id:
                                product_qty += do_line.product_qty or 0.0
                product_norm = line.product_qty - product_qty or 0.0
                if product_norm > 0.0:
                    vars.append((0, 0, { 'product_id':line.product_id.id, 'product_uom':line.product_uom.id, 'name':line.name, 'product_norm': product_norm,
                                    'product_qty': line.product_qty - product_qty or 0.0, 'price_unit': line.price_unit or 0.0, 'tax_id': [(6, 0, [x.id for x in line.tax_id])]}))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_convert(self):
        active_id = self._context.get('active_id')
        if not self.wizard_ids:
            raise UserError(_('You cannot create DO vs GDN without any Products.'))
        if not active_id:
            raise UserError(_('You cannot create DO vs GDN.'))
        
        contract = self.env['sale.contract'].browse(active_id)
        company = self.env.user.company_id.id
        partner_id = contract.partner_id.id or False
        warehouse_id = contract.warehouse_id.id or False
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        picking_type_id = warehouse.out_type_id.id or False
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        
                
        var = {'name': self.name, 'contract_id': active_id, 'warehouse_id': warehouse_id, 'picking_type_id': picking_type_id, 'currency_id': self.currency_id.id or False,
           'shipment_from': contract.partner_id.id, 'sale_contract_id': self.contract_id.id, 'transportation_cost': self.transportation_cost or 1 }
        do_id = self.env['delivery.order'].create(var)
        
        for line in self.wizard_ids:
            if line.product_qty > line.product_norm:
                raise UserError(_('Product Qty is not greater than the Product Norm %s at Product Name %s.') % (int(line.product_norm), line.product_id.name))
            self.env['delivery.order.line'].create({'name': line.name, 'delivery_id': do_id.id,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])], 'price_unit': line.price_unit,
                   'product_id': line.product_id.id, 'product_qty': line.product_qty,
                   'product_uom': line.product_uom.id, 'state': 'draft'})
                
        if do_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_delivery_order')
            form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_delivery_order_form')
            result = {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[form_view_id, 'form']],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': do_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
        return True
    
class wizard_do_line(models.TransientModel):
    _name = "wizard.do.line"
    
    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', main=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    product_qty = fields.Float(string='Qty', required=True, default=1.0)
    product_norm = fields.Float(string='Product_norm', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    wizard_id = fields.Many2one('wizard.do', 'Wizard do', required=False)
    
    
    
