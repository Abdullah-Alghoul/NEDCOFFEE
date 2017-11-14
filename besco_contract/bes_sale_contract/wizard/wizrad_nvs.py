# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizrad_nvs(models.TransientModel):
    _name = "wizard.nvs"
    
    name = fields.Char(string='Reference', required=True)
    shipping_id = fields.Many2one('shipping.instruction', 'Shipping', ondelete='cascade')
    date = fields.Date(string='Transfer Of Date')
    wizard_ids = fields.One2many('wizard.nvs.line', 'wizard_id', 'Wizard Lines')
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            shipping_obj = self.env['shipping.instruction'].browse(active_id)
            res = {'name': 'New', 'shipping_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'delivery_from': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
            product_qty = 0.0
            for line in shipping_obj.shipping_ids:
                for contract in shipping_obj.contract_ids:
                    if contract.state != 'cancel':
                        for contract_line in contract.contract_line:
                            if line.product_id == contract_line.product_id:
                                product_qty += contract_line.product_qty or 0.0
                product_norm = line.product_qty - product_qty or 0.0
                if product_norm > 0.0:
                    vars.append((0, 0, { 'product_id':line.product_id.id or False, 'product_uom':line.product_uom.id, 'name':line.name or False,
                   'product_qty': line.product_qty - product_qty or 0.0, 'product_norm': product_norm, 'price_unit': line.price_unit or 0.0, 'tax_id': [(6, 0, [x.id for x in line.tax_id])]} or False))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_convert(self):
        active_id = self._context.get('active_id')
        if not self.wizard_ids:
            raise UserError(_('You cannot create a NVS without any Products.'))
        if not active_id:
            raise UserError(_('You cannot create a NVS.'))
        
        shipping_obj = self.env['shipping.instruction'].browse(active_id)
        warehouse_id = shipping_obj.warehouse_id.id or False
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        partner_id = shipping_obj.partner_id.id or False
        scontract_id = shipping_obj.contract_id.id or False
        scontract = self.env['s.contract'].browse(scontract_id)
        
        var = {'name': self.name, 'warehosue_id': warehouse.id or False, 'shipment_from': warehouse.partner_id.id or False,
            'partner_invoice_id': scontract.partner_invoice_id.id or False, 'dispatch_mode': scontract.dispatch_mode or False,
            'port_of_loading': scontract.port_of_loading.id or False, 'deadline': scontract.deadline or False,
            'port_of_discharge': scontract.port_of_discharge.id or False, 'transportation_charges': scontract.transportation_charges or False,
            'container_status': scontract.container_status or False,
            'delivery_tolerance': scontract.delivery_tolerance or 0.0, 'shipping_id': active_id, 'type': 'export',
            'partner_id': scontract.partner_id.id or False, 'currency_id': scontract.currency_id.id or False,
            'weights': scontract.weights or False, 'payment_term_id': scontract.payment_term_id.id or False,
            'exchange_rate': scontract.exchange_rate or 1, 'final_destination': scontract.final_destination.id or False,
            'picking_policy': scontract.picking_policy or False}
        nvs_id = self.env['sale.contract'].create(var)
        
        for line in self.wizard_ids:
            if line.product_qty > line.product_norm:   
                raise UserError(_('Product Qty is not greater than the Product Norm %s at Product Name %s.') % (int(line.product_norm), line.product_id.name))
            self.env['sale.contract.line'].create({'name': line.product_id.name, 'contract_id': nvs_id.id,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])], 'price_unit': line.price_unit,
                   'product_id': line.product_id.id, 'product_qty': line.product_qty, 'partner_id': partner_id, 'company_id': company,
                   'product_uom': line.product_uom.id, 'state': 'draft'})
          
        if nvs_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_sale_contract_export')
            form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_sale_contract_form')
            list_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_sale_contract_tree')
            result = {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': nvs_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
        return result
    
class wizrad_nvs_line(models.TransientModel):
    _name = "wizard.nvs.line"
    
    name = fields.Text(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    product_qty = fields.Float(string='Qty', required=True, default=1.0)
    product_norm = fields.Float(string='Product_norm', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    wizard_id = fields.Many2one('wizard.nvs', 'Wizard nvs', required=False, ondelete='cascade')
       
