# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizrad_nls_line(models.TransientModel):
    _inherit = "wizard.nls.line"
    
    certificate_id = fields.Many2one('ned.certificate', string='Certificate')

class wizrad_nls(models.TransientModel):
    _inherit = "wizard.nls"
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            contract_obj = self.env['s.contract'].browse(active_id)
            res = {'name': 'New', 's_contract_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
            product_qty = 0.0
            for line in contract_obj.contract_line:
                for contract in contract_obj.contract_ids:
                    if contract.state != 'cancel':
                        for contract_line in contract.contract_line:
                            if line.product_id == contract_line.product_id:
                                product_qty += contract_line.product_qty or 0.0
                product_norm = line.product_qty - product_qty or 0.0
                if product_norm > 0.0:
                    vars.append((0, 0, {'product_id':line.product_id.id or False, 'product_uom':line.product_uom.id or False, 'name':line.name or False,
                   'product_qty': line.product_qty - product_qty or 0.0, 'product_norm': product_norm, 'price_unit': line.price_unit or 0.0,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])] or False, 'certificate_id': line.certificate_id.id or False}))
            res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def button_convert(self):
        active_id = self._context.get('active_id')
        if not self.wizard_ids:
            raise UserError(_('You cannot create a NLS without any Products.'))
        if not active_id:
            raise UserError(_('You cannot create a NLS.'))
        
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        scontract = self.env['s.contract'].browse(active_id)
        partner_id = scontract.partner_id.id or False
        
        var = {'name': self.name or False, 'warehosue_id': warehouse_id.id or False, 'shipment_from': warehouse_id.partner_id.id or False,
            'partner_invoice_id': scontract.partner_invoice_id.id or False, 'dispatch_mode': scontract.dispatch_mode or False,
            'port_of_loading': scontract.port_of_loading.id or False, 'port_of_discharge': scontract.port_of_discharge.id or False,
            'deadline': scontract.deadline or False, 'transportation_charges': scontract.transportation_charges or False,
            'container_status': scontract.container_status or False,
            'delivery_tolerance': scontract.delivery_tolerance or 0.0, 'partner_id': scontract.partner_id.id or False,
            'scontract_id': active_id, 'type': 'local', 'crop_id': scontract.crop_id.id or False,
            'weights': scontract.weights or False, 'currency_id': scontract.currency_id.id or False,
            'exchange_rate': scontract.exchange_rate or 1, 'payment_term_id': scontract.payment_term_id.id or False,
            'picking_policy': scontract.picking_policy or False, 'final_destination': scontract.final_destination.id or False}
        nls_id = self.env['sale.contract'].create(var)
        
        for line in self.wizard_ids:
            if line.product_qty > line.product_norm:
                raise UserError(_('Product Qty is not greater than the Product Norm %s at Product Name %s.') % (int(line.product_norm), line.product_id.name))
            self.env['sale.contract.line'].create({'name': line.name or False, 'contract_id': nls_id.id or False,
                   'tax_id': [(6, 0, [x.id for x in line.tax_id])] or False, 'price_unit': line.price_unit or 0.0,
                   'product_id': line.product_id.id or False, 'product_qty': line.product_qty or 0.0,
                   'partner_id': partner_id or False, 'company_id': company or False, 'certificate_id': line.certificate_id.id or False or False,
                   'product_uom': line.product_uom.id or False, 'state': 'draft'})
          
        if nls_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_sale_contract_local')
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
                    'res_id': nls_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
        return result
