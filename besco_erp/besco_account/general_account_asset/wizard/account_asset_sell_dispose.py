# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _

import time
from datetime import datetime
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
DATETIME_FORMAT = "%Y-%m-%d"
DATE_FORMAT = "%Y-%m-%d"

class SellorDispose(models.TransientModel):
    _name = 'sell.or.dispose'
    
    def _prepare_invoice_line(self, asset, invoice_id, amount):
        name = asset.name or ''
        origin = asset.name or ''

        account_id =  asset.category_id.account_income_recognition_id
      

        return { 'name': name, 'origin': origin,
            'invoice_id': invoice_id.id,
            'account_id': account_id.id, 'price_unit': amount or 0.0, 'quantity': 1,
            #'invoice_line_tax_ids': [(6, 0, self._get_taxes_invoice(move_line, invoice_vals['type']))]
            }
    
    def create_invoice(self, asset,amount):
        invoice_pool = self.env['account.invoice']
        invoice_line_pool = self.env['account.invoice.line']
        partner_id =  self.partner_id
        account_id = partner_id.property_account_receivable_id.id,
        payment_term = partner_id and partner_id.property_payment_term_id.id or False
        
        invoice_vals = {'name': asset.name or False, 
                        'origin': asset.name, 
                        'supplier_inv_date': False, 
                        'partner_id': partner_id.id, 
                        'reference': asset.name,
                        'type': 'out_invoice', 
                        'account_id':account_id,
                        'date_invoice': self.date or False, 
                        'currency_id': asset.currency_id.id or False,
                        'comment': '', 
                        'company_id': 1, 
                        'user_id': self.env.uid, 
                        'journal_id': asset.category_id.journal_id.id or False,
                        'payment_term_id': payment_term, 
                        'fiscal_position_id': partner_id and partner_id.property_account_position_id.id or False, 
                        }
        
        invoice_id = invoice_pool.create(invoice_vals)
        vals = self._prepare_invoice_line(asset,invoice_id, amount)
        invoice_line_pool.create(vals)
#                     
#             
        return invoice_id   
    
    partner_id = fields.Many2one('res.partner', string='Customer')
    date = fields.Date(string="Date")
    
    def create_move(self, asset, post_move=True):
        depreciation_date =  fields.Date.context_today(self)
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        debit_amount2 = current_currency.compute(asset.value_residual, company_currency)
        credit_amount = current_currency.compute(asset.value, company_currency)
        debit_amount1 = credit_amount - debit_amount2
#             sign = (line.asset_id.category_id.journal_id.type == 'purchase' or line.asset_id.category_id.journal_id.type == 'sale' and 1) or -1
        #asset_name = asset.name + ' (%s/%s)' % (asset.sequence, asset.method_number)
        asset_name = asset.name 
        reference = asset.code
        journal_id = asset.category_id.journal_id.id
        partner_id = asset.partner_id.id
        categ_type = asset.category_id.type
        
        sign = (categ_type == 'purchase' or categ_type == 'sale' and 1) or -1
        debit_account1 = asset.category_id.account_depreciation_id.id
        debit_account2 = asset.category_id.recognition_expense_account_id.id  
        credit_account = asset.category_id.account_asset_id.id
        
        account_analytic_id = asset.account_analytic_id or asset.category_id.account_analytic_id
        
        move_line_1 = {
            'name': asset_name,
            'account_id': debit_account1,
            'debit':  debit_amount1,
            'credit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and  (asset.value - asset.value_residual) or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'sale' else False,
            'date': depreciation_date,
        }
        move_line_2 = {
            'name': asset_name,
            'account_id': debit_account2,
            'debit': debit_amount2, 
            'credit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and asset.value_residual or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'purchase' else False,
            'date': depreciation_date,
        }
        move_line_3 = {
            'name': asset_name,
            'account_id': credit_account,
            'credit': credit_amount,
            'debit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and (- 1) * asset.value or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'purchase' else False,
            'date': depreciation_date,
        }
        move_vals = {
            'ref': reference,
            'date': depreciation_date or False,
            'journal_id': asset.category_id.journal_id.id,
            'line_ids': [(0, 0, move_line_2), (0, 0, move_line_1),(0, 0, move_line_3)],
            'asset_id': asset.id,
            }
        move = self.env['account.move'].create(move_vals)
        #THANH: auto post entries
        move.post()
        return move.id
            
    @api.multi
    def sell_or_dispose(self):
        asset_id = self.env.context.get('active_ids')
        asset = self.env['account.asset.asset'].browse(asset_id)
        amount = asset.value_residual
        if amount<=0:
            return
        invoice_id = self.create_invoice(asset,amount)
        unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check)
        if unposted_depreciation_line_ids:
            old_values = {
                'method_end': asset.method_end,
                'method_number': asset.method_number,
            }
            
            
            move_id = self.create_move(asset,post_move=False)
            # Remove all unposted depr. lines
            commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]
            
            # Create a new depr. line with the residual amount and post it
            sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1
            today = datetime.today().strftime(DF)
            vals = {
                'amount': amount,
                'asset_id': asset.id,
                'sequence': sequence,
                'name': (asset.code or '') + '/' + str(sequence),
                'remaining_value': 0,
                'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                'depreciation_date': today,
                'move_check':True,
                'move_id':move_id
            }
            commands.append((0, False, vals))
            
            asset.write({'depreciation_line_ids': commands, 'method_end': today, 'method_number': sequence})
            tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_end'])
            changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
            if changes:
                asset.message_post(subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
            
            #kiệt: Xuất bán tài sản 
            #move_ids += asset.depreciation_line_ids[-1].create_move(post_move=False)
            
            
        if invoice_id:   
            asset.sale_invoice_id = invoice_id.id
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