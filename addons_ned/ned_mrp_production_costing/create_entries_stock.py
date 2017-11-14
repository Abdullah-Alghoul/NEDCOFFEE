# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class StockMove(models.Model):
    _inherit = "stock.move"
    
    def _get_accounting_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_dest = accounts['stock_output'].id
        acc_src = accounts.get('stock_valuation', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src.id, acc_dest
    
    def _prepare_account_move_line(self,line, qty,amount ,  credit_account_id, debit_account_id):
        debit = credit = amount
        
        
        ##PARTNER Nedbv
        res_company_id = self.env['res.partner'].search([('name','=','NEDCOFFEE BV')])
        
        if res_company_id:
            partner_id = res_company_id.id
        else:
            partner_id = line.picking_id and line.picking_id.partner_id and line.picking_id.partner_id.id or False
        #name =''
#         if line.picking_id:
#             name = line.picking_id.origin + ' - ' +line.product_id.default_code
#         else:

        name = line.product_id.default_code
        if line.picking_id:
            name += '-' + line.picking_id.name
            
        debit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit':  0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            #'amount_currency':amount_currency,
            'account_id': debit_account_id,
            #'currency_id': line.second_currency_id.id
        }
        credit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': 0.0,  
            'credit': credit or 0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            #'amount_currency': (-1) * amount_currency,
            'account_id': credit_account_id,
            #'currency_id': line.second_currency_id.id
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    #Kiet: Nghiep vu nhập kho NVL khi đã FIFO
    
    
    def _get_accounting_hcm_cus_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_output'].id
        acc_dest = accounts.get('cogs_export', False) 
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest
    
    
    def _get_accounting_buonme_hcm_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_output'].id
        acc_dest = accounts.get('stock_valuation', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest.id
    
    def _get_accounting_faq_data(self,line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_input'].id
        acc_dest = accounts.get('stock_valuation', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_dest.id, acc_src
    
    def get_entries_buonme_hcm(self,move_line_ids):
        move_obj = self.env['account.move']
        move_lines =[]
        
        amount = 0.0
        for fifo in move_line_ids.fifo_out_ids:
            amount += fifo.out_qty * fifo.fifo_id.price_unit
        if not amount and amount ==0:
            amount = move_line_ids.product_qty * move_line_ids.price_unit
        if amount and amount !=0:
            journal_id, acc_src, acc_dest  = self._get_accounting_buonme_hcm_data(move_line_ids)
            move_lines = self._prepare_account_move_line(move_line_ids, move_line_ids.product_qty ,amount , acc_dest,acc_src)
            if move_lines:
                ref = move_line_ids.picking_id.name
                if move_line_ids.picking_id.origin:
                    ref += '- ' + move_line_ids.picking_id.origin
                date = move_line_ids.date
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line_ids.entries_id = new_move_id.id
                return amount
        else:
            return False
    
    @api.model
    def entries_buonme_hcm_fifo(self):
        location_id = self.env['stock.location'].search([('code','=','NVP - BMT')])
        location_dest_id = self.env['stock.location'].search([('code','=','HCM')])
        stock_move_ids = self.env['stock.move'].search([('state','=','done'),('product_qty','!=',0),('product_id','=',1207),
                              ('date','>=','2017-02-01 00:00:00'),('entries_id','=',False),('price_unit','!=',0),
                              ('location_id','=',location_id.id),('location_dest_id','=',location_dest_id.id)])
        for move in stock_move_ids:
#             if move.entries_id:
#                 move.entries_id.button_cancel()
#                 move.entries_id.unlink()
            if move.qty_out_fifo  == move.product_uom_qty:
                self.get_entries_buonme_hcm(move)
    
    def get_entries_hcm_customer(self,move_line_ids):
        move_obj = self.env['account.move']
        move_lines =[]
        
        amount = 0.0
        for fifo in move_line_ids.fifo_out_ids:
            amount += fifo.out_qty * fifo.fifo_id.price_unit
            
        if amount and amount !=0:
            journal_id, acc_src, acc_dest  = self._get_accounting_hcm_cus_data(move_line_ids)
            move_lines = self._prepare_account_move_line(move_line_ids, move_line_ids.product_qty ,move_line_ids.product_qty * move_line_ids.price_unit , acc_src,acc_dest)
            if move_lines:
                if move_line_ids.entries_id:
                    return False
                ref = move_line_ids.picking_id.name
                date = move_line_ids.date
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line_ids.entries_id = new_move_id.id
                return  True
        else:
            return False
    
    @api.model
    def entries_hcm_customer_fifo(self):
        location_id = self.env['stock.location'].search([('code','=','HCM')]) 
        location_dest_id = self.env['stock.location'].search([('usage','=','customer')]) 
        stock_move_ids = self.env['stock.move'].search([('state','=','done'),('product_qty','!=',0),
                              ('entries_id','=',False),('date','>=','2017-01-01 00:00:00'),
                              ('product_id','=',1207),
                              ('location_id','=',location_id.id),('location_dest_id','=',location_dest_id.id)])
        for move in stock_move_ids:
#             if move.entries_id:
#                 move.entries_id.button_cancel()
#                 move.entries_id.unlink()
            if move.qty_out_fifo  == move.product_uom_qty:
                self.get_entries_hcm_customer(move) 
    
    def _prepare_account_move_faq_line(self,line, qty,amount_usd,amount_vn , debit_account_id, credit_account_id):
        debit = credit = amount_usd
        partner_id = (line.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(line.picking_id.partner_id).id) or False
        #name =''
#         if line.picking_id:
#             name = line.picking_id.origin + ' - ' +line.product_id.default_code
#         else:
        name = line.product_id.default_code
        debit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit':  0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency':amount_vn,
            'account_id': debit_account_id,
            'currency_id': line.second_currency_id.id
        }
        credit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': 0.0,  
            'credit': credit or 0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency': (-1) * amount_vn,
            'account_id': credit_account_id,
            'currency_id': line.second_currency_id.id
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    def get_entries_faq_nvp(self,move_line_ids):
        move_obj = self.env['account.move']
        move_lines =[]
        
        amount_vn = amount_usd = 0.0
        for move in move_line_ids:
            amount_vn = move.product_qty * move.price_currency
            amount_usd = move.product_qty * move.price_unit
            
        if amount_vn and amount_vn !=0:
            journal_id, acc_src, acc_dest = self._get_accounting_faq_data(move_line_ids)
            move_lines = self._prepare_account_move_faq_line(move_line_ids, move_line_ids.product_qty ,amount_usd,amount_vn , acc_src,acc_dest)
            if move_lines:
                if move_line_ids.entries_id:
                    return False
                ref = move_line_ids.picking_id.name
                date = move_line_ids.date
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'warehouse_id':move_line_ids.picking_id.picking_type_id.warehouse_id.id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line_ids.entries_id = new_move_id.id
                return  True
        else:
            return False
        
    
                
                
    @api.model
    def entries_faq_nvp_fifo(self):
        location_npe_id = self.env['stock.location'].search([('code','=','NPE - BMT')])
        location_nvp_id = self.env['stock.location'].search([('code','=','Kho chưa phân bổ - BMT')])  
        location_dest_id = self.env['stock.location'].search([('code','=','NVP - BMT')]) 
        stock_move_ids = self.env['stock.move'].search([('state','=','done'),('price_unit','!=',0),
                              ('entries_id','=',False),('date','>=','2017-01-01 00:00:00'),
                              ('location_id','in',(location_npe_id.id,location_nvp_id.id)),('location_dest_id','=',location_dest_id.id)])
        for move in stock_move_ids:
            self.get_entries_faq_nvp(move)
#         
        
#         sql ='''
#             Update ir_cron set active = true where name = 'Update entries faq'
#         '''
#         self.env.cr.execute(sql)
            
                            
#             
        
        # Bút toán kho hàng Vật tư
#         location_dest_vt_id = self.env['stock.location'].search([('code','=','VT')]) 
#         stock_move_ids = self.env['stock.move'].search([('state','=','done'),('price_unit','!=',0),
#                               ('entries_id','=',False),
#                               ('location_dest_id','=',location_dest_vt_id.id)])
#         for move in stock_move_ids:
#             self.get_entries_faq_nvp(move)
        return True
        
    @api.model
    def cron_create_entries_fifo(self,ids=None):
#         self.entries_buonme_hcm_fifo()
        #self.env.cr.commit()
#         self.entries_hcm_customer_fifo()
        #self.env.cr.commit()
        self.entries_faq_nvp_fifo()
        return 1