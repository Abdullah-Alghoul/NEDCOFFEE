# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class WizradInvoice(models.TransientModel):
    _inherit = "wizard.invoice"
    
    res_partner_id = fields.Many2one('res.partner',string='Partner')
    partner_id = fields.Many2one('res.partner',string='Partner')
    
    @api.model
    def default_get(self, fields):
        res = {}
        
        #THANH: set default journal from property
        property_obj = self.env['admin.property'].search([('name','=','wizard_invoice_default_journal')]) or None
        if property_obj:
            res.update({'journal_id':int(property_obj.value)})
             
        vars=[]
        active_id = self._context.get('active_id')
        if active_id:
            
            si = self.env['sale.contract'].browse(active_id)
            
            res_partner_id = si.partner_id
            partner_id = self.env['res.partner'].search([('name','=','NEDCOFFEE BV')])
            account_id = partner_id.property_account_payable_id.id or False
            
            nvs =si.name[4:len(si.name)]
            now = datetime.now()
            current_year = str(now.year)
            current_year = current_year[2:4]
    
            name ='INV-'+ str(current_year) +'-'+ nvs
            
            res.update({'partner_id':partner_id.id,'res_partner_id':res_partner_id.id,'account_id':account_id,
                   'contract_id': active_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
                   'currency_id': si.currency_id.id or False,'name':name})
            
            for line in si.contract_line:
                vars.append((0, 0, {'product_id':line.product_id.id,'product_qty': line.product_qty or 0.0, 
                                'price_unit': line.price_unit or 0.0}))
                res.update({'wizard_ids':vars})
        return res
    
    @api.multi
    def create_invoice(self):
        
        active_id = self._context.get('active_id')
        invoice_pool = self.env['account.invoice']
        invoice_line_pool = self.env['account.invoice.line']
        si = self.env['sale.contract'].browse(active_id)
        partner_id = self.env['res.partner'].search([('name','=','NEDCOFFEE BV')])
        account_id = partner_id.property_account_receivable_id.id or False
        payment_term = partner_id.property_payment_term_id.id or False
            
#         nvs =si.name[4:len(si.name)]
#         now = datetime.now()
#         current_year = now.year
# 
#         name ='INV-'+ str(current_year) +'.'+ nvs
        
        invoice_vals = {'partner_id':partner_id.id,
                        'name': self.name, 
                        'origin': si.name, 
                        'supplier_inv_date': False, 
                        'res_partner_id': si.partner_id.id, 
                        'reference': self.name,
            'type': 'out_invoice', 'account_id': account_id, 'date_invoice': self.date or False, 
            'currency_id': self.currency_id.id or False,
            'comment': '', 
            'company_id': 1, 
            'user_id': self.env.uid, 
            'journal_id': self.journal_id.id or False,
            'payment_term_id': payment_term, 
            'fiscal_position_id': partner_id.property_account_position_id.id or False, 
            'sale_contract_id': si.id or False}
        
        invoice_id = invoice_pool.create(invoice_vals)
        for line in self.wizard_ids:
            vals = self._prepare_invoice_line( line, invoice_id, invoice_vals)
            invoice_line_pool.create(vals)
        invoice_id.compute_taxes()
        
                    
        if invoice_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('account.action_invoice_tree1')
            form_view_id = imd.xmlid_to_res_id('account.invoice_form')
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
                
    
