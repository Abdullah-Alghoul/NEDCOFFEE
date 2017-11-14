# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizrad_gdn(models.TransientModel):
    _name = "wizard.gdn"
    
    contract_id = fields.Many2one('sale.contract', readonly=True)
    date = fields.Date(string='Scheduled Date')
    wizard_ids = fields.One2many('wizard.gdn.line', 'wizard_id', 'Wizard Lines')
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            contract_obj = self.env['sale.contract'].browse(active_id)
            res = {'contract_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
            product_qty = product_norm = 0.0
            for line in contract_obj.contract_line:
                for gdn in contract_obj.picking_ids:
                    if gdn.state != 'cancel':
                        for gdn_line in gdn.move_lines:
                            if gdn_line.product_id == line.product_id:
                                product_qty += gdn_line.product_uom_qty or 0.0
                product_norm = line.product_qty - product_qty
                if product_norm > 0.0:
                    vars.append((0, 0, {'product_id':line.product_id.id or False, 'name': line.name or False, 'product_uom':line.product_uom.id or False,
                   'product_qty': product_norm, 'product_norm': product_norm, 'price_unit': line.price_unit or 0.0, 'tax_id': [(6, 0, [x.id for x in line.tax_id])] or False}))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_convert(self):
        active_id = self._context.get('active_id')
        if not self.wizard_ids:
            raise UserError(_('You cannot create a GDN without any Products.'))
        if not active_id:
            raise UserError(_('You cannot create a GDN.'))
        
        contract = self.env['sale.contract'].browse(active_id)
        company = self.env.user.company_id.id or False
        warehouse_id = contract.warehouse_id.id or False
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        picking_type_id = warehouse.out_type_id.id or False
        picking_type = self.env['stock.picking.type'].browse(picking_type_id)
        
        partner_id = contract.partner_id.id or False
        
        var = {'name': '/', 'picking_type_id': picking_type_id, 'min_date': self.date or False, 'partner_id': partner_id, 
           'picking_type_code': picking_type.code or False, 'location_id': picking_type.default_location_src_id.id or False, 'sale_contract_id': active_id,
           'location_dest_id': picking_type.default_location_dest_id.id or False}  
        picking_id = self.env['stock.picking'].create(var)  
        
        for line in self.wizard_ids:
            if line.product_qty > line.product_norm:
                raise UserError(_('Product Qty is not greater than the Product Norm %s at Product Name %s.') % (int(line.product_norm), line.product_id.name))
            self.env['stock.move'].create({'picking_id': picking_id.id or False, 'name': line.name or '', 'product_id': line.product_id.id or False,
                'product_uom': line.product_uom.id or False, 'product_uom_qty': line.product_qty or 0.0, 'price_unit': line.price_unit or 0.0,
                'out_stock_wti': line.product_qty or 0.0, 'picking_type_id': picking_type_id or False,
                'location_id': picking_type.default_location_src_id.id or False, 'date_expected': self.date or False,
                'location_dest_id': picking_type.default_location_dest_id.id or False, 'type': picking_type.code or False,
                'date': self.date or False, 'currency_id': contract.currency_id.id or False, 'partner_id': partner_id,
                'company_id': company, 'state':'draft', 'scrapped': False, 'warehouse_id': contract.warehouse_id.id or False})
          
        if picking_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('stock.action_picking_form')
            form_view_id = imd.xmlid_to_res_id('stock.view_picking_form')
            result = {'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[form_view_id, 'form']],
                    'target': action.target,
                    'context': {'default_picking_type_id': picking_type_id},
                    'res_model': action.res_model,
                    'res_id': picking_id.ids and picking_id.ids[0],
                    'views' : [(form_view_id, 'form')]}
        return result
    
class wizard_gdn_line(models.TransientModel):
    _name = "wizard.gdn.line"
    
    name = fields.Text(string='Description', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', readonly=True)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure', readonly=True)
    product_qty = fields.Float(string='Qty', required=True, default=1.0)
    product_norm = fields.Float(string='Product_norm', readonly=True, default=1.0)
    price_unit = fields.Float('Unit Price', readonly=True, default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes', readonly=True)
    wizard_id = fields.Many2one('wizard.gdn', 'Wizard GDN', required=False, ondelete='cascade')
    
