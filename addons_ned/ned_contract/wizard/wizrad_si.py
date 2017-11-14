# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizard_si_line(models.TransientModel):
    _inherit = "wizard.si.line"
    
    certificate_id = fields.Many2one('ned.certificate', string='Certificate')


class wizrad_si(models.TransientModel):
    _inherit = "wizard.si"
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            contract_obj = self.env['s.contract'].browse(active_id)
            res = {'name': 'New', 's_contract_id': active_id, 'date':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
            product_qty = 0.0
            for line in contract_obj.contract_line:
                for si in contract_obj.shipping_ids:
                    if si.state != 'cancel':
                        for si_line in si.shipping_ids:
                            if line.product_id == si_line.product_id:
                                product_qty += si_line.product_qty or 0.0
                product_norm = line.product_qty - product_qty or 0.0
                if product_norm > 0.0:
                    vars.append((0, 0, { 'product_id':line.product_id.id, 'product_uom':line.product_uom.id, 'name':line.name,
                   'product_qty': line.product_qty - product_qty or 0.0, 'product_norm': product_norm, 'price_unit': line.price_unit or 0.0,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])], 'certificate_id': line.certificate_id.id or False}))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_convert(self):
        var = []
        active_id = self._context.get('active_id')
        if not self.wizard_ids:
            raise UserError(_('You cannot create a SI without any Products.'))
        if not active_id:
            raise UserError(_('You cannot create a SI.'))
        
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        scontract = self.env['s.contract'].browse(active_id)
        partner_id = scontract.partner_id.id or False
        
        vars = {'name': self.name, 'final_destination': scontract.partner_shipping_id.id or False, 'partner_id': scontract.partner_id.id or False,
             'port_of_loading': scontract.port_of_loading.id or False, 'deadline': scontract.deadline or False,
             'port_of_discharge': scontract.port_of_discharge.id or False, 'shipment_from': warehouse_id.partner_id.id or False,
             'contract_id': scontract.id or False, 'default_type': 'export', 'warehouse_id': warehouse_id.id or False,
             'company_id': company or False, 'type': 'export'}
        shipping_id = self.env['shipping.instruction'].create(vars)
        
        for line in self.wizard_ids:
            if line.product_qty > line.product_norm:
                raise UserError(_('Product Qty is not greater than the Product Norm %s at Product Name %s.') % (int(line.product_norm), line.product_id.name))
            self.env['shipping.instruction.line'].create({'name': line.name, 'shipping_id': shipping_id.id,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])], 'price_unit': line.price_unit, 'company_id': company,
                   'product_id': line.product_id.id, 'product_qty': line.product_qty, 'partner_id': partner_id,
                   'product_uom': line.product_uom.id, 'state': 'draft', 'certificate_id': line.certificate_id.id or False})
      
        if shipping_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_shipping_instruction')
            form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_shipping_instruction_form')
            list_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_shipping_instruction_tree')
            result = {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': shipping_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
        return result
