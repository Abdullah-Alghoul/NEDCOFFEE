# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizrad_invoice_purchase(models.TransientModel):
    _name = "wizard.invoice.purchase"
    
    name = fields.Char(string='Invoice Number')
    date = fields.Date(string='Date', default=fields.Datetime.now, required=False)
    journal_id = fields.Many2one("account.journal", 'Journal', required=True)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True)
    wizard_ids = fields.One2many('wizard.purchase.invoice.line', 'wizard_id', 'Wizard Lines')
    description = fields.Char(string='Note')
    
    @api.model
    def default_get(self, fields):
        res = {}    
        vars = []
        active_id = self._context.get('active_id')
        if active_id:
            contract = self.env['purchase.contract'].browse(active_id)
            journal_ids = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            
            res = {'purchase_contract_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
                   'currency_id': contract.currency_id.id or False, 'journal_id': journal_ids.id}
            for line in contract.contract_line:
                vars.append((0, 0, {'product_id':line.product_id.id,'product_qty': line.product_qty or 0.0, 
                                'price_unit': line.price_unit or 0.0}))
                res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def _get_taxes_invoice(self, move_line, type):
        taxes = move_line.product_id.taxes_id
        if move_line.picking_id and move_line.picking_id.partner_id and move_line.picking_id.partner_id.id:
            position = self.env['account.fiscal.position'].browse(move_line.picking_id.partner_id.property_account_position_id.id)
            return position.map_tax(taxes)
        else:
            return map(lambda x: x.id, taxes)
    
    @api.multi
    def _get_account_analytic_invoice(self, picking, move_line):
        return False
    
    @api.multi
    def _prepare_invoice_line(self,  move_line, invoice_id, invoice_vals):
        name = move_line.product_id.name or ''
        origin = move_line.product_id.name or ''
        
#         account_id = False
#         if not account_id:
        account_id = move_line.product_id.categ_id.property_stock_account_input_categ_id.id or False
                    
        if invoice_vals['fiscal_position_id']:
            fp_obj = self.env['account.fiscal.position']
            fiscal_position = fp_obj.browse(invoice_vals['fiscal_position_id'])
            account_id = fiscal_position.map_account(account_id)
      
        uos_id = move_line.product_id and move_line.product_id.uom_id.id or False
        if not uos_id and invoice_vals['type'] == 'out_invoice':
            uos_id = move_line.product_uom.id

        return { 'name': name, 'origin': origin,
            'invoice_id': invoice_id.id, 'uom_id': uos_id, 'product_id': move_line.product_id.id,
            'account_id': account_id, 'price_unit': move_line.price_unit or 0.0, 'quantity': move_line.product_qty,
            #'invoice_line_tax_ids': [(6, 0, self._get_taxes_invoice(move_line, invoice_vals['type']))]
            }
          
    @api.multi
    def create_invoice(self):
        active_id = self._context.get('active_id')
        invoice_pool = self.env['account.invoice']
        invoice_line_pool = self.env['account.invoice.line']
        purchase = self.env['purchase.contract'].browse(active_id)
        partner_id = purchase.partner_id or False
        account_id = partner_id.property_account_payable_id.id or False
        payment_term = partner_id.property_payment_term_id.id or False
        name = '/'
        
        invoice_vals = {'name': self.description or False, 
                        'origin': purchase.name, 
                        'supplier_inv_date': False, 
                        'partner_id': partner_id.id, 
                        'reference': self.name,
                        'type': 'in_invoice', 
                        'account_id':account_id,
                        'date_invoice': self.date or False, 
                        'currency_id': self.currency_id.id or False,
                        'comment': '', 
                        'company_id': 1, 
                        'user_id': self.env.uid, 
                        'journal_id': self.journal_id.id or False,
                        'payment_term_id': payment_term, 
                        'fiscal_position_id': partner_id.property_account_position_id.id or False, 
                        'purchase_contract_id': purchase.id or False}
        
        invoice_id = invoice_pool.create(invoice_vals)
        product_qty = 0
        for line in self.wizard_ids:
            vals = self._prepare_invoice_line( line, invoice_id, invoice_vals)
            invoice_line_pool.create(vals)
            product_qty += line.product_qty
            value_allocation = line.price_unit
        if invoice_id:           
            
            ## tạo phân bổ hóa đơn NPE- NVP 
            vals_invoice = {
                           'contract_id':active_id,
                           'account_id':invoice_id.id,
                           'qty_allocation':product_qty,
                           'value_allocation': value_allocation
            }
            self.env['invoiced.allocation'].create(vals_invoice)
            
                  
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('account.action_invoice_tree1')
            form_view_id = imd.xmlid_to_res_id('account.invoice_supplier_form')
            result = {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[form_view_id, 'form']],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': invoice_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
            
        return result   
                
class wizard_purchase_invoice_line(models.TransientModel):
    _name = "wizard.purchase.invoice.line"
    
    wizard_id = fields.Many2one('wizard.invoice.purchase', string='Wizard invoice', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade',required=True,)
    product_qty = fields.Float(string='product Qty',digits=(12, 0))
    price_unit= fields.Float(string='Price Unit',digits=(12, 0))
    
