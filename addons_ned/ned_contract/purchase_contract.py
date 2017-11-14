# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
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
    
class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    
    @api.multi
    @api.depends('acc_number', 'bank_id')
    def name_get(self):
        result = []
        for bank in self:
            name = bank.acc_number
            if bank.bank_id.bic:
                name = bank.bank_id.bic + ' - ' + bank.acc_number
            result.append((bank.id, name))
        return result
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice" 
    
    contract_id = fields.Many2one('purchase.contract',string="NVP Contract")
    

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    @api.model
    def default_get(self, fields):
        res = super(AccountPayment, self).default_get(fields)
        return res
    
    def _create_payment_entry(self, amount):
        move_id = super(AccountPayment, self)._create_payment_entry(amount)
        if self.purchase_contract_id:
            self.purchase_contract_id.move_ids = [(4, move_id.id)]
    
    def _compute_payment_received(self):
        for line in self:
            pay_alocation = 0.0
            sql='''
                SELECT sum(allocation_amount) amount
                FROM payment_allocation
                WHERE pay_id = %s
            '''%(line.id)
            self.env.cr.execute(sql)
            for pay in self.env.cr.dictfetchall():
                pay_alocation = pay['amount'] or 0.0
            line.payment_refunded = pay_alocation
            line.open_advance = line.amount - pay_alocation
    
        
    payment_refunded = fields.Float(compute='_compute_payment_received', string='Refunded', readonly=True,digits=(12, 0))
    open_advance = fields.Float(compute='_compute_payment_received', string='Open Advance', readonly=True,digits=(12, 0))
    
class NpeNvpInvoice(models.Model):
    _name = "npe.nvp.invoice"
    _order = 'id desc'
    
    contract_id = fields.Many2one('purchase.contract', string="Contract")
    invoice_id = fields.Many2one('account.invoice', string="invoice")
    product_qty = fields.Float(related='invoice_id.total_qty', readonly=True)
    amount_total = fields.Monetary(related='invoice_id.amount_total',string="Amount Total", readonly=True)
    npe_id = fields.Many2one('purchase.contract',string="NPE")
    currency_id =fields.Many2one(related='invoice_id.currency_id', string="Currency")

class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
   
#     @api.model
#     def create(self, vals):
#         result = super(PurchaseContract, self).create(vals)
#         if not self.move_id and vals.get('allocation_amount',False):
#             new_id = self.npe_nvp_entries()
#             self.write({'move_id': new_id})
#             interest_move_id = result.advance_interest_rate_entries()
#         return result
    
    @api.multi
    def write(self, vals):
        result = super(PurchaseContract, self).write(vals)
        if self.interest_move_id and vals.get('pay_allocation_ids',False):
            sql = '''
                DELETE from account_move_line where move_id = %s 
            '''%(self.interest_move_id.id)
            self.env.cr.execute(sql)
            self.interest_move_id.write({'line_ids': self.update_advance_interest_entries()})
            
        if not self.interest_move_id and vals.get('pay_allocation_ids',False):
            interest_move_id = self.advance_interest_rate_entries()
            self.write({'interest_move_id': interest_move_id})
            
        return result
    
    @api.multi
    def button_draft(self):
        for contract in self:
            for move_id in contract.move_ids:
                sql ='''
                    DELETE FROM account_move_line WHERE move_id in (%s);
                    DELETE FROM account_move WHERE id in (%s);
                '''%(move_id.id,move_id.id)
                self.env.cr.execute(sql)
            contract.write({'state': 'draft'})
        
    @api.multi
    def button_cancel(self):
        for contract in self:
            for move_id in contract.move_ids:
                sql ='''
                    DELETE FROM account_move_line WHERE move_id in (%s);
                    DELETE FROM account_move WHERE id in (%s);
                '''%(move_id.id,move_id.id)
                self.env.cr.execute(sql)
            contract.write({'state': 'cancel'})
            
            sql ='''
                SELECT id from stock_picking 
                WHERE purchase_contract_id = %s
            '''%(contract.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                picking_id = self.env['stock.picking'].browse(line['id'])
                picking_id.action_revert_done()
                picking_id.unlink()
        
    def _create_stock_moves(self, line,picking,picking_type, qty):
        moves = self.env['stock.move']
        price_unit = line.price_unit
        if line.tax_id:
            price_unit = line.tax_id.compute_all(price_unit, currency=line.contract_id.currency_id, quantity=1.0)['total_excluded']
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit = price_unit * (line.product_uom.factor / line.product_id.uom_id.factor)
        
        #Quy doi ra USD
        price_unit = self.env.user.company_id.second_currency_id.with_context(date=line.contract_id.date_order).compute(price_unit, 
                                                                                                 self.env.user.company_id.currency_id)
        
        vals = {
                'warehouse_id':picking_type.warehouse_id.id,
                'picking_id': picking.id,
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'init_qty':qty,
                'product_uom_qty': qty or 0.0,
                'price_unit': price_unit,
                # 'tax_id': [(6, 0, [x.id for x in i.tax_id])],
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'date': line.contract_id.date_order,
                # 'exchange_rate':this.purchase_contract_id.exchange_rate or 1,
                'currency_id':line.contract_id.currency_id.id or False,
                'type': picking_type.code,
                'state':'draft',
                'scrapped': False,
                'price_currency':line.price_unit or 0.0,
                }
        
        move_id = moves.create(vals)
        return move_id
    
    @api.multi
    def printf_npe(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'npe_report',
                }
    
    @api.multi
    def printf_nvp(self):
#         payment = self.env['payment.allocation'].search([])
#         for line in payment:
            #line.btt_load_interest()
        if self.nvp_ids:
            return {
                    'type': 'ir.actions.report.xml',
                    'report_name':'npe_nvp_report',
                    }
        else:
            return {
                    'type': 'ir.actions.report.xml',
                    'report_name':'nvp_report',
                    }
    
    @api.multi
    def printf_liquidation(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'nvp_liquidation_report',
                }
    def _get_accounting_data_for_valuation(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        acc_dest = accounts['stock_input'].id
        acc_src = accounts['stock_input'].id

        acc_valuation = accounts.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (line.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (line.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts['stock_journal'].id
        
        return journal_id, acc_src, acc_dest, acc_valuation

    def _create_account_move_line(self, line, credit_account_id, debit_account_id, journal_id):
        #group quants by cost
        move_obj = self.env['account.move']
        move_lines = self._prepare_account_move_line(line, line.product_qty, line.price_unit, credit_account_id, debit_account_id)
        date = line.contract_id.date_order
        new_move_id = move_obj.create({'journal_id': journal_id,
                                  'line_ids': move_lines,
                                  'date': date,
                                  'ref': line.contract_id.name,
                                  'narration':line.contract_id.name})
        self.move_id = new_move_id
        new_move_id.post()
        return new_move_id
    
    def _prepare_account_move_line(self,line, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        valuation_amount = line.price_unit or 0.0
        #valuation_amount = currency_obj.round(line.contract_id.company_id.currency_id, valuation_amount * qty)
        valuation_amount = valuation_amount * qty
        #check that all data is correct
        if self.company_id.currency_id.is_zero(valuation_amount):
            raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.name,))
        
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency,currency_id = aml_obj.with_context(date=self.date_order).compute_amount_fields(valuation_amount, self.currency_id, self.company_id.currency_id)
        
        partner_id = (self.partner_id and self.pool.get('res.partner')._find_accounting_partner(self.partner_id).id) or False
        debit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': line.contract_id and line.contract_id.name or False,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit': credit or 0.0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'amount_currency':amount_currency,
            'account_id': debit_account_id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False
        }
        credit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': line.contract_id and line.contract_id.name or False,
            'partner_id': partner_id,
            'credit': debit or 0.0, 
            'debit': credit or 0.0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'amount_currency': (-1) * amount_currency,
            'account_id': credit_account_id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    # kiet sinh bút toán Chuyển từ NPE sang NVP (1)/ Issuing a transaction converting from NPE to NVP contract.
    def _account_entry_move(self):
        move_obj = self.env['account.move']
        move_lines =[]
        for line in self.contract_line:
#             if line.product_id.valuation != 'real_time':
#                 return False
            if line.product_qty <= 0:
                return False

            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(line)
            move_lines = self._prepare_account_move_line(line, line.product_qty, line.price_unit, acc_src, acc_valuation)
            date = line.contract_id.date_order
            new_move_id = move_obj.create({'journal_id': journal_id,
                                  'line_ids': move_lines,
                                  'date': date,
                                  'ref': line.contract_id.name,
                                  'narration':line.contract_id.name})
            new_move_id.post()
            return new_move_id.id
            
    
    def _prepare_account_move_line_for_general(self, cost, credit_account_id, debit_account_id,description):
        valuation_amount = cost or 0.0
        if self.company_id.currency_id.is_zero(valuation_amount):
            raise UserError(_("The found valuation amount for product %s is zero. Which means there is probably a configuration error. Check the costing method and the standard price") % (self.name,))
        partner_id = (self.partner_id and self.pool.get('res.partner')._find_accounting_partner(self.partner_id).id) or False
        
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency,currency_id = aml_obj.with_context(date=self.date_order).compute_amount_fields(valuation_amount, self.currency_id, self.company_id.currency_id)
        
        debit_line_vals = {
            'name': description,
            'product_id': False,
            'quantity': 1,
            'product_uom_id': False,
            'ref': description,
            'partner_id': partner_id,
            'debit': debit or 0,
            'credit': 0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'amount_currency':amount_currency,
            'account_id': debit_account_id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False
        }
        credit_line_vals = {
            'name': description,
            'product_id': False,
            'quantity': 1,
            'product_uom_id': False,
            'ref': description,
            'partner_id': partner_id,
            'credit': debit,
            'debit': 0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'amount_currency': (-1) * amount_currency,
            'account_id': credit_account_id,
            'currency_id': self.currency_id != self.company_id.currency_id and self.currency_id.id or False
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    def advance_interest_rate_entries(self):
        for contract in self:
            move_obj = self.env['account.move'] 
            credit_account_id = contract.company_id.incomce_from_advance_payment_id.id
            if not contract.company_id.interest_income_shipment_id.id:
                raise UserError(_('You cannot Validate, You must define Account Interest Income Shipment in Company Configuration '))
            debit_account_id = contract.company_id.interest_income_shipment_id.id
            journal_id = False
            interest_pay =0.0
            for pay_allocation in contract.pay_allocation_ids:
                interest_pay += pay_allocation.total_interest_pay or 0.0
            journal_id = journal_id = self.env['account.journal'].search([('code','=','BILL')],limit =1)
            if not interest_pay:
                return False
            
            name = u'''Bút toán lãi suất (Theo ngày hợp đồng): %s'''%(self.name)
            move_lines = contract._prepare_account_move_line_for_general(interest_pay, credit_account_id, debit_account_id,name)
            date = contract.date_order
            
            if not journal_id:
                raise 
            new_move_id = move_obj.create({'journal_id': journal_id.id,
                                      'line_ids': move_lines,
                                      'date': time.strftime(DATE_FORMAT),
                                      'ref': name,
                                      'narration':name})
            new_move_id.post()
        return new_move_id.id
    
    def update_advance_interest_entries(self):
        for contract in self:
            credit_account_id = contract.company_id.incomce_from_advance_payment_id.id
            if not contract.company_id.interest_income_shipment_id.id:
                raise UserError(_('You cannot Validate, You must define Account Interest Income Shipment in Company Configuration '))
            debit_account_id = contract.company_id.interest_income_shipment_id.id
            interest_pay =0.0
            for pay_allocation in contract.pay_allocation_ids:
                interest_pay += pay_allocation.total_interest_pay or 0.0
            if not interest_pay:
                return False
            
            name = u'''lãi ứng tiền cà phê gửi kho: %s'''%(self.name)
            move_lines = contract._prepare_account_move_line_for_general(interest_pay, credit_account_id, debit_account_id,name)
            
        return move_lines
    
    
    def done_interest_rate_entries(self):
        for contract in self:
            move_obj = self.env['account.move'] 
            debit_account_id = contract.partner_id.property_account_payable_id.id
            if not contract.company_id.interest_income_shipment_id.id:
                raise UserError(_('You cannot Validate, You must define Account Interest Income Shipment in Company Configuration '))
            credit_account_id = contract.company_id.interest_income_shipment_id.id 
            journal_id = False
            interest_pay =0.0
            for pay_allocation in contract.pay_allocation_ids:
                interest_pay += pay_allocation.total_interest_pay or 0.0
            journal_id = self.env['account.journal'].search([('code','=','BILL')],limit =1)
                
            if not interest_pay:
                return False
            
            name = u'''lãi ứng tiền cà phê gửi kho: %s'''%(self.name)
            move_lines = contract._prepare_account_move_line_for_general(interest_pay, credit_account_id, debit_account_id,name)
            date = time.strftime(DATE_FORMAT)
            
            if not journal_id:
                raise 
            new_move_id = move_obj.create({'journal_id': journal_id.id,
                                      'line_ids': move_lines,
                                      'date': time.strftime(DATE_FORMAT),
                                      'ref': name,
                                      'narration':name})
            new_move_id.post()
        return new_move_id.id

    @api.multi
    def button_lai(self):
        if self.interest_move_id:
            sql = '''
                DELETE from account_move_line where move_id = %s 
            '''%(self.interest_move_id.id)
            self.env.cr.execute(sql)
            self.interest_move_id.write({'line_ids': self.update_advance_interest_entries()})
                
        if not self.interest_move_id:
            interest_move_id = self.advance_interest_rate_entries()
            self.write({'interest_move_id': interest_move_id})
            
    @api.multi
    def button_done(self):
        # kiet bút toán 
        for contract in self:
            if contract.type != 'purchase':
                contract.write({'state':'done'})
                continue
            
            if self.interest_move_id:
                sql = '''
                    DELETE from account_move_line where move_id = %s 
                '''%(self.interest_move_id.id)
                self.env.cr.execute(sql)
                self.interest_move_id.write({'line_ids': self.update_advance_interest_entries()})
                
            if not self.interest_move_id:
                interest_move_id = self.advance_interest_rate_entries()
                self.write({'interest_move_id': interest_move_id})
                
            new_id = self.done_interest_rate_entries()
            if new_id:
                contract.write({'interest_move_entries_id': new_id})
            contract.write({'state':'done'})
        return 1
    
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
    
    def _get_accounting_faq_data(self,line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_input'].id
        acc_dest = accounts.get('stock_valuation', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_dest.id, acc_src
    
    def get_entries_picking_nvp(self,pick):
        move_obj = self.env['account.move']
        move_lines =[]
        
        for move_line_ids in pick.move_lines:
            amount_vn = amount_usd = 0.0
            for move in move_line_ids:
                amount_vn = move.product_qty * move.price_currency
                amount_usd = move.product_qty * move.price_unit
                
            if amount_vn and amount_vn !=0:
                journal_id, acc_src, acc_dest  = self._get_accounting_faq_data(move_line_ids)
                move_lines = self._prepare_account_move_faq_line(move_line_ids, move_line_ids.product_qty ,amount_usd,amount_vn , acc_src,acc_dest)
                if move_lines:
                    if move_line_ids.entries_id:
                        return False
                    ref = move_line_ids.picking_id.name
                    date = move_line_ids.date
                    new_move_id = move_obj.create({'journal_id': journal_id,
                                          'line_ids': move_lines,
                                          'date': date,
                                          'ref': ref,
                                          'warehouse_id':pick.warehouse_id and pick.warehouse_id.id or False,
                                          'narration':False})
                    new_move_id.post()
                    move_line_ids.entries_id = new_move_id.id
                    return  True
            else:
                return False
            
    @api.multi
    def button_approve(self):
        for contract in self:
            if not contract.contract_line:
                raise UserError(_('You cannot approve a purchase contract without any purchase contract line.'))
                
            #  phat sinh phiếu nhâp kho từ Ký gởi -> NVL
            if contract.nvp_ids and contract.type =='purchase':
                for line in contract.contract_line:
                    if not line.price_unit or line.price_unit == 0.0:
                        raise UserError(_('You cannot Approve, Price Unit !=0 '))
                    
                picking_type = contract.warehouse_id.int_type_id
                if not contract.warehouse_id.int_type_id:
                    raise UserError(_('You cannot Approve, You must define Picking type'))
                
                var = {
                    'warehouse_id':picking_type.warehouse_id.id,
                    'picking_type_id': picking_type.id,
                    'partner_id': contract.partner_id.id,
                    'date': contract.date_order,
                    'date_done': contract.date_order,
                    'origin': contract.name,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                    'location_id': picking_type.default_location_src_id.id,
                    'purchase_contract_id':contract.id
                }
                picking = self.env['stock.picking'].create(var)
                product_qty =0
                product_qty = contract.qty_received
#                 for i in contract.nvp_ids:
#                     product_qty += i.qty_received
                    
                for line in contract.contract_line:
                    moves = self._create_stock_moves(line,picking,picking_type,product_qty)
                    moves.action_confirm()
                    moves.force_assign()
                picking.action_done()
                 #Kiet: cho sinh bút toán luôn
                self.get_entries_picking_nvp(picking)
                
                #Kiet: Phát sinh bút toán Vận chuyển
                move_ids = []
                #move_ids = self.shipping_cost_entry();
                #1: (Dựa theo SL chốt * đơn giá chốt) (Theo ngày hợp đồng) *** Khi User bấm nút Validate hợp đồng NVP
                #move_ids.append(self._account_entry_move())
                #self.write({'move_ids':[(6, 0, move_ids)]})
            
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.depends('contract_line.price_total','contract_line.price_unit','pay_allocation_ids','pay_allocation_ids.allocation_amount',
         'request_payment_ids','request_payment_ids.total_payment','payment_ids','payment_ids.amount'
         )
    def _amount_all(self):
        for contract in self:
            amount_untaxed = amount_tax = 0.0
            for line in contract.contract_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            
            amount = 0.0
            amount_deposit = 0.0
            for deposit in contract.pay_allocation_ids:
                amount_deposit += deposit.allocation_amount or 0.0
                amount += deposit.total_interest_pay
            for deposit in contract.payment_ids:
                amount_deposit += deposit.amount
                
            amount = abs(amount) * (-1)
            amount_deposit = abs(amount_deposit) * (-1)
            
            contract.update({
                'amount_untaxed': contract.currency_id.round(amount_untaxed),
                'amount_tax': contract.currency_id.round(amount_tax),
                'amount_sub_total':amount_untaxed + amount_tax,
                'amount_total': amount_untaxed + amount_tax + amount + amount_deposit,
                'total_interest_pay':amount,
                'amount_deposit':amount_deposit
            })
    
    @api.depends('qty_received','nvp_ids','npe_ids','contract_line.product_qty')
    def _received_qty(self):
        for contract in self:
            received =0.0
            # Trường hợp cho hàng chốt
            if contract.nvp_ids:
                for line in contract.contract_line:
                    received += line.product_qty
                    
            contract.qty_unreceived = contract.total_qty - received
            contract.qty_received = received
    
    
            
    
    @api.depends('invoice_ids','invoice_ids.amount_total')
    def _amount_invoiced(self):
        for contract in self:
            amount_invoiced =0.0
            for invoiced in contract.invoice_ids:
                amount_invoiced +=invoiced.amount_total or 0.0
            contract.amount_invoiced = amount_invoiced or 0.0
            if contract.amount_sub_total !=0 and amount_invoiced == contract.amount_sub_total:
                contract.invoiced = True
            else:
                contract.invoiced = False
    
    npe_nvp_invoice_ids = fields.One2many('npe.nvp.invoice','contract_id', string='Allocation')  
    allocation_ids = fields.One2many('stock.allocation','contract_id', string='Allocation')
    crop_id = fields.Many2one('ned.crop', string='Crop', required=True, readonly=True, states={'draft': [('readonly', False)]})
    from_date_rate = fields.Date('From Rate')
    to_date_rate = fields.Date('To Rate')
    number = fields.Integer('Number')
    state_id = fields.Many2one('res.country.state', 'State', readonly=True, states={'draft': [('readonly', False)]})
    total_interest_pay = fields.Monetary(compute='_amount_all', string='Interest', readonly=True, store=True, track_visibility='always')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Total Payable', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_sub_total = fields.Monetary(string='Sub total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_sub_rel_total = fields.Monetary(string='Sub Rel total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_deposit = fields.Monetary(string='Paid', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    #Qty Allocation StockPicking
    qty_received = fields.Float(string ='Received',digits=(12, 0))
    qty_unreceived = fields.Float(compute='_received_qty',string ='UnReceived',digits=(12, 0),store = False)
    songay = fields.Integer(string="Số ngày")
    
    pay_allocation_ids = fields.One2many('payment.allocation', 'contract_id', string='Payment Allocation')
    delivery_place_id = fields.Many2one('delivery.place', string='Delivery Place',
       readonly=True, states={'draft': [('readonly', False)]}, required=False, domain="[('type', 'in', ['purchase'])]")
    move_ids =fields.Many2many('account.move', 'move_contract_ref', 'move_id', 'contract_id',string= 'Move Entries', readonly=True)
    relation_price_unit = fields.Float(related='contract_line.price_unit', string='Price')
    invoice_ids = fields.One2many('account.invoice', 'contract_id', string='Invoice')
    price_unit = fields.Float(related='contract_line.price_unit',  string='Price unit')
    interest_move_id = fields.Many2one('account.move',string="Interest Entries")
    interest_move_entries_id = fields.Many2one('account.move',string="Interest Entries 2")
    certificate_id = fields.Many2one('ned.certificate', string='Certificate', )
    premium = fields.Integer(string='Premium')
    g2diff = fields.Integer(string='G2Diff')
    packing_terms_id = fields.Many2one('packing.terms',string="Packing terms")
    contract_type = fields.Selection(string='Contract type', selection=[('PTBF', 'PTBF'), ('OR', 'Outright')])
    
    
    @api.depends('payment_ids','payment_ids.amount')
    def _compute_amount(self):
        for contract in self:
            payment_remain = payment_received = amount =0.0
            if contract.type == 'consign':
                for pay in contract.payment_ids:
                    amount += pay.amount or 0.0
                    payment_received += pay.payment_refunded or 0.0
                    payment_remain += pay.open_advance or 0.0
                    
            contract.total_advance = amount or 0.0
            contract.total_payment_remain = payment_remain or 0.0
            contract.total_payment_received = payment_received or 0.0
    
    total_advance = fields.Float(compute='_compute_amount',string ='Total Advance',digits=(12, 0),)
    total_payment_received =fields.Float(compute='_compute_amount',string ='Refunded',digits=(12, 0),)
    total_payment_remain = fields.Float(compute='_compute_amount',string ='Open Advance',digits=(12, 0))
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d-%m-%Y')
    
    def get_years(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%Y')
    
    @api.depends('date_order')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.date_order
            line.day_tz = self.get_vietname_date(line.date_order)
            line.years_tz = self.get_years(line.date_order)
            
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    years_tz = fields.Char(compute='_compute_date',string = "Years", store=True)
    
    @api.multi
    def _nvp_relation_type(self):
        for this in self:
            if not this.nvp_ids:
                this.nvp_relation_type = u'fixed'
            for relation in this.nvp_ids:
                this.nvp_relation_type = relation.type
            
                
    
    nvp_relation_type = fields.Selection(compute='_nvp_relation_type', selection=[('fixed',_('Fixed')),
                                                            ('temporary', _('Temporary'))],method=True,  store=True, string='Relation Type')
    
    @api.depends('state','qty_received','nvp_ids','npe_ids','contract_line.product_qty')
    def _total_qty_fixed(self):
        for order in self:
            fix = 0.0
            for line in order.npe_ids:
                fix += line.product_qty
            
            order.qty_unfixed = order.qty_received - fix
            order.total_qty_fixed = fix
            
    total_qty_fixed = fields.Float(compute='_total_qty_fixed',string = 'Fixed',digits=(12, 0),store = True)
    qty_unfixed = fields.Float(compute='_total_qty_fixed',string ='UnFixed',digits=(12, 0),store = True)
    
    @api.multi
    def btt_load_payment(self):
        sql ='''
            SELECT id 
            FROM account_payment 
            WHERE partner_id = %s 
                and purchase_contract_id is not null
                and extend_payment = 'advance'
                and allocated != true
                and id not in (
                    SELECT pay_id 
                    FROM payment_allocation 
                    WHERE contract_id = %s
                )
        '''%(self.partner_id.id,self.id)
        self.env.cr.execute(sql)
        for contract in self.env.cr.dictfetchall():
            self.env['payment.allocation'].create({'pay_id':contract['id'],'contract_id':self.id})
        return True
    
class PurchaseContractLine(models.Model):
    _inherit = "purchase.contract.line"
    
    @api.model
    def create(self, vals):
        result = super(PurchaseContractLine, self).create(vals)
        return result
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        for line in self:
            order = line.contract_id
            price_unit = line.price_unit
            if line.tax_id:
                price_unit = line.tax_id.compute_all(price_unit, currency=line.contract_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                #price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
                price_unit = self.env.user.company_id.second_currency_id.with_context(date=order.date_order).compute(price_unit, 
                                                                                                 self.env.user.company_id.currency_id)
            
            product_qty =0
            if line.nvp_ids:
                for i in line.nvp_ids:
                    product_qty += i.qty_received
                    
            vals = {
                    'picking_id': picking.id,
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_qty or 0.0,
                    'init_qty':line.product_qty or 0.0,
                    'price_unit': price_unit,
                    'price_currency':line.price_unit or 0.0,
                    # 'tax_id': [(6, 0, [x.id for x in i.tax_id])],
                    'picking_type_id': picking.picking_type_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'date': picking.purchase_contract_id.date_order,
                    # 'exchange_rate':this.purchase_contract_id.exchange_rate or 1,
                    'currency_id':picking.purchase_contract_id.currency_id.id or False,
                    'type': picking.purchase_contract_id.warehouse_id.in_type_id.code,
                    'state':'draft',
                    'scrapped': False,
                    'warehouse_id':picking.purchase_contract_id.warehouse_id.id,
                    }
            
            move_id = moves.create(vals)
            return move_id
    
    
        
class PaymentAllocation(models.Model):
    _name = "payment.allocation"
    _order = 'id desc'
    
    
    def npe_nvp_entries(self):
        for contract in self.contract_id:
            move_obj = self.env['account.move']
            debit_account_id = contract.partner_id.property_account_payable_id.id
            credit_account_id = contract.partner_id.property_vendor_advance_acc_id.id
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            allocation_amount =0.0
            if self.pay_id.extend_payment == 'advance':
                allocation_amount = self.allocation_amount or 0.0
            if not allocation_amount:
                return False
            
            name = u'''Kết chuyển tạm ứng %s - %s'''%(self.pay_id.purchase_contract_id.name,contract.name)
            move_lines = contract._prepare_account_move_line_for_general(allocation_amount, credit_account_id, debit_account_id,name)
            date = contract.date_order
            new_move_id = move_obj.create({'journal_id': journal_id.id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': name,
                                      'narration':name})
            new_move_id.post()
        return new_move_id.id
    
    def update_npe_nvp_entries(self):
        for contract in self.contract_id:
            move_obj = self.env['account.move']
            debit_account_id = contract.partner_id.property_account_payable_id.id
            credit_account_id = contract.partner_id.property_vendor_advance_acc_id.id
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            allocation_amount =0.0
            if self.pay_id.extend_payment == 'advance':
                allocation_amount = self.allocation_amount or 0.0
            if not allocation_amount:
                return False
            
            name = u'''Kết chuyển tạm ứng %s - %s'''%(self.pay_id.purchase_contract_id.name,contract.name)
            move_lines = contract._prepare_account_move_line_for_general(allocation_amount, credit_account_id, debit_account_id,name)
            return move_lines
    
    @api.model
    def create(self, vals):
        result = super(PaymentAllocation, self).create(vals)
        if not self.move_id and vals.get('allocation_amount',False):
            new_id = self.npe_nvp_entries()
            self.write({'move_id': new_id})
        return result
    
    @api.multi
    def write(self, vals):
        result = super(PaymentAllocation, self).write(vals)
        if not self.move_id and vals.get('allocation_amount',False):
            new_id = self.npe_nvp_entries()
            self.write({'move_id': new_id})
            
            
        if self.move_id and vals.get('allocation_amount',False):
            sql = '''
                DELETE from account_move_line where move_id = %s 
            '''%(self.move_id.id)
            self.env.cr.execute(sql)
            self.move_id.write({'line_ids': self.update_npe_nvp_entries()})
        return result
    
    def _compute_payment_received(self):
        for line in self:
            if line.pay_id:
                pay_alocation = 0.0
                sql='''
                    SELECT sum(allocation_amount) amount
                    FROM payment_allocation
                    WHERE pay_id = %s
                '''%(line.pay_id.id)
                self.env.cr.execute(sql)
                for pay in self.env.cr.dictfetchall():
                    pay_alocation = pay['amount'] or 0.0
                line.payment_received = pay_alocation
                line.payment_remain = line.payment_amount - pay_alocation
                if line.payment_remain == 0:
                    line.pay_id.write({'allocated':True})
                else:
                    line.pay_id.write({'allocated':False})
                 
    def _compute_total_interest_pay(self):
        for line in self:
            amount = 0.0
            for payline in line.allocation_line_ids:
                amount += payline.actual_interest_pay
            line.total_interest_pay = amount
    
    pay_id = fields.Many2one('account.payment', string='Payment')
    #notes = fields.Char(related='pay_id.notes', string='notes')
    request_id = fields.Many2one(related='pay_id.request_payment_id', string='Request', readonly=True)
    partner_id = fields.Many2one(related='pay_id.partner_id', string='Supplier', readonly=True,store=True)
    relation_contract_id = fields.Many2one(related='pay_id.purchase_contract_id', string='From NPE', readonly=True)
    payment_date = fields.Date(related='pay_id.payment_date', string='Payment Date', readonly=True)
    payment_amount = fields.Monetary(related='pay_id.amount', string='Original Amount', readonly=True,currency_field='currency_id')
    currency_id = fields.Many2one(related='pay_id.currency_id', string='Currency', readonly=True)
    contract_id = fields.Many2one('purchase.contract', string='To NVP')
    allocation_amount = fields.Float('Allocation Amount',digits=(12, 0))
    allocation_line_ids = fields.One2many('payment.allocation.line', 'pay_allocation_id', string='Allocation Line')
    payment_received = fields.Float(compute='_compute_payment_received', string='Refunded', readonly=True,digits=(12, 0))
    payment_remain = fields.Float(compute='_compute_payment_received', string='Open Advance', readonly=True,digits=(12, 0))
    total_interest_pay = fields.Float(compute='_compute_total_interest_pay', string='Interest', readonly=True,digits=(12, 0))
    
    nvp_date = fields.Date(related='contract_id.date_order', string='NVP Date', readonly=True)
    
    move_id = fields.Many2one('account.move',string="Entries")
    
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d-%m-%Y')
    
    @api.depends('nvp_date')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.nvp_date
            line.day_tz = self.get_vietname_date(line.nvp_date)
            
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    
    @api.multi
    def btt_load_interest(self):
        interest_obj = self.env['payment.allocation.line']
        for allocation_line in self:
            allocation_line.allocation_line_ids.unlink()
            date_start = allocation_line.pay_id.payment_date
            to_date = allocation_line.contract_id.date_order
            month = 1
            while date_start < allocation_line.contract_id.date_order:
                if not date_start:
                    continue
                sql ='''
                    select '%s'::date + 30 as to_date
                '''%(date_start)
                self.env.cr.execute(sql)
                for line in self.env.cr.dictfetchall():
                    to_date = line['to_date']
                if to_date >= allocation_line.contract_id.date_order:
                    to_date = allocation_line.contract_id.date_order
                if month == 5:
                    to_date = allocation_line.contract_id.date_order
                
                rate_id = self.env['interest.rate'].search([('month', '=', month),
                              ('request_id','=',allocation_line.pay_id.request_payment_id.id)], limit=1)
                interest_obj.create({
                        'month':str(month),
                        'pay_allocation_id':allocation_line.id,
                        'from_date':date_start,
                        'to_date':to_date,
                        'rate':rate_id.rate or 0.0
                       })
                try:
                    sql ='''
                        SELECT '%s'::date  as to_date
                    '''%(to_date)
                    self.env.cr.execute(sql)
                    for line in self.env.cr.dictfetchall():
                        date_start = line['to_date']
                except Exception, e:
                    print 'Contract: ' + allocation_line.pay_id.name
                    
                if month == 5:
                    return 
                month +=1
                
            return True
  
class PaymentAllocationLine(models.Model):
    _name = "payment.allocation.line"
    _order = 'id desc'   
    
    
    @api.model
    def create(self, vals):
        result = super(PaymentAllocationLine, self).create(vals)
        return result

    @api.depends('pay_allocation_id.allocation_amount', 'pay_allocation_id','rate', 'from_date', 'to_date')
    def _compute_interest_pay(self):
        for line in self:
            total_date = 0.0
            sql = '''
                SELECT '%s'::date - '%s'::date as date 
            ''' % (line.to_date, line.from_date)
            self.env.cr.execute(sql)
            for rate in self.env.cr.dictfetchall():
                date = total_date = rate['date'] 
             
            interest_pay = line.pay_allocation_id.allocation_amount * (line.rate /100)
            if total_date == 0:
                date = 1
                total_date = 1
                interest_pay_one = (interest_pay / 30) * int(date)
            else:
#                 if date !=30:
#                     date -= 1
#                     total_date -=1
                interest_pay_one = (interest_pay / 30) * int(date)
             
            line.update({
                'total_date': total_date,
                'interest_pay': interest_pay ,
                'actual_interest_pay': interest_pay_one,
            })
     
    pay_allocation_id = fields.Many2one('payment.allocation', string='Pay Allocation Line')
    from_date = fields.Date(string='From Date', readonly=True)
    to_date = fields.Date(string='To Date', readonly=True)
    amount_interest_rate = fields.Monetary(string='Amount Interest', readonly=True)
    currency_id = fields.Many2one(related='pay_allocation_id.contract_id.currency_id', string='Currency', readonly=True)
    total_date = fields.Integer(compute='_compute_interest_pay', string='Date', readonly=True, store=True)
    interest_pay = fields.Float(compute='_compute_interest_pay', string='Interest Pay/Month', readonly=True, store=True,digits=(12, 0))
    actual_interest_pay = fields.Float(compute='_compute_interest_pay', string='Interest pay/Day', readonly=True, store=True,digits=(12, 0))
    month = fields.Selection([('1', 'Tháng 1'), ('2', 'Tháng 2'),  ('3', 'Tháng 3'),
                              ('4', 'Tháng 4'),  ('5', 'Tháng 5')], string='Month',
                             readonly=False, copy=False, index=True,)
    rate = fields.Float(string='Rate %', readonly=False,digits=(12, 6))
    
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    @api.depends('move_lines.product_uom_qty','move_lines','allocation_ids','allocation_ids.qty_allocation','allocation_ids.state')
    def _compute_allocation(self):
        for pick in self:
            qty = 0.0
            for allocation in pick.allocation_ids:
                if allocation.state !='draft':
                    qty += allocation.qty_allocation
            pick.allocated_qty = qty
            pick.qty_available = pick.total_qty - pick.allocated_qty
            if pick.qty_available <= 0.0:
                pick.allocated = True
        return  

    allocation_ids = fields.One2many('stock.allocation','picking_id', 'Allocation')
    allocated_qty = fields.Float(string='Allocated',compute='_compute_allocation',store=True, digits=(16, 0))
    qty_available = fields.Float(string='To Allocated',compute='_compute_allocation',store=True,digits=(16, 0))
    allocation_id = fields.Many2one('stock.allocation', string='Allocation',)
    allocated = fields.Boolean(string = 'Allocated',compute='_compute_allocation',default = False ,store=True)
    
    
    @api.multi
    def btt_allocation(self):
        sql ='''
            SELECT id FROM purchase_contract 
            WHERE partner_id = %s 
                and state= 'approved'
                and id not in (
                    SELECT contract_id 
                    FROM stock_allocation
                    WHERE picking_id = %s)
        '''%(self.partner_id.id,self.id)
        self.env.cr.execute(sql)
        for contract in self.env.cr.dictfetchall():
            contract = self.env['purchase.contract'].browse(contract['id'])
            if contract.nvp_ids:
                continue
            if contract.qty_received >= contract.total_qty:
                continue
            self.env['stock.allocation'].create({'contract_id':contract['id'],'picking_id':self.id})
        return True
    
class StockAllocation(models.Model):
    _name ="stock.allocation"
    _order = 'date_picking desc' 
    
    
    @api.model
    def create(self, vals):
        result = super(StockAllocation, self).create(vals)
        return result
    
    @api.depends('contract_id','picking_id','qty_allocation','state')
    def _compute_qty(self):
        for order in self:
            allocation_qty = 0.0
            if order.picking_id and order.contract_id:
                sql ='''
                    SELECT sum(qty_allocation) sum_qty 
                    FROM stock_allocation
                    WHERE picking_id = %s 
                '''%(order.picking_id.id)
                self.env.cr.execute(sql)
                for allocation in self.env.cr.dictfetchall():
                    allocation_qty = allocation['sum_qty'] or 0.0
                order.qty_received = allocation_qty
                order.qty_unreceived = order.qty_grn -  allocation_qty
                if order.qty_unreceived ==0:
                    order.compare_qty = True
    
    
    contract_id = fields.Many2one('purchase.contract', string='Contract')
    type_contract = fields.Selection([('consign', 'Consignment Agreement'), ('purchase', 'Purchase Contract')], 
                            string="Type", related='contract_id.type',store=True)
    product_id = fields.Many2one('product.product',related='picking_id.product_id', string='Product',store=True)
    picking_id = fields.Many2one('stock.picking', string='GRN',
       readonly=False, states={'draft': [('readonly', False)]}, required=False,)
    date_allocation = fields.Date(string="Date Allocation",default= time.strftime(DATE_FORMAT))
    
    qty_grn = fields.Float(related='picking_id.total_qty',string='GRN Qty')
    date_picking = fields.Datetime(related='picking_id.date_done',string='Date Picking',store=True)
    partner_id = fields.Many2one(related='picking_id.partner_id',string='Partner',store=True)
    qty_contract = fields.Float(related='contract_id.total_qty',string='Contract Qty',store=True)
    price_contract = fields.Float(related='contract_id.price_unit',string='Fix Price',store=True)
    
    date_contract = fields.Date(related='contract_id.date_order',string='Date Contract')
    
    qty_allocation = fields.Float(string='Qty Allocation',digits=(12, 0))
    qty_received = fields.Float(compute='_compute_qty',string = 'Allocated',store=True,digits=(12, 0))
    qty_unreceived = fields.Float(compute='_compute_qty',string = 'UnAllocated',digits=(12, 0))
    compare_qty = fields.Boolean(compute='_compute_qty',string = "Compare",default =True)
    state = fields.Selection([('draft', 'New'), ('approved', 'Approved')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
    
    allocation_picking_id = fields.Many2one('stock.picking',string='GRN Allocate')
    warehouse_id = fields.Many2one(related='allocation_picking_id.picking_type_id.warehouse_id',string='Warehouse',store=True)
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d-%m-%Y')
    
    @api.depends('date_picking')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.date_picking
            line.day_tz = self.get_vietname_date(line.date_picking)
            
    date_tz = fields.Date(compute='_compute_date',string = "Month", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "date", store=True)
    
    #reamin_qty = fields.Float(compute='_reamin_qty', string='Remain Qty', readonly=True,store = True)
    
    @api.multi
    def _create_stock_moves(self, line,picking,picking_type, qty):
        moves = self.env['stock.move']
        price_unit = line.price_unit
        if line.tax_id:
            price_unit = line.tax_id.compute_all(price_unit, currency=line.contract_id.currency_id, quantity=1.0)['total_excluded']
        if line.product_uom.id != line.product_id.uom_id.id:
            price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
        
        #kiet: Quyy doi
        date_contract = picking.date_done
        price_unit = self.env.user.company_id.second_currency_id.with_context(date=date_contract).compute(price_unit, 
                                                                                                 self.env.user.company_id.currency_id,
                                                                                                 round=False)
        
        vals = {
                'picking_id': picking.id,
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': qty or 0.0,
                'init_qty':qty,
                'price_unit': price_unit,
                # 'tax_id': [(6, 0, [x.id for x in i.tax_id])],
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'date': line.contract_id.date_order,
                'price_currency':line.price_unit or 0.0,
                # 'exchange_rate':this.purchase_contract_id.exchange_rate or 1,
                'currency_id':line.contract_id.currency_id.id or False,
                'type': picking_type.code,
                'state':'draft',
                'scrapped': False,
                'warehouse_id':line.contract_id.warehouse_id.id,
                }
        
        move_id = moves.create(vals)
        return move_id
    
    @api.multi
    def cancel_allocation(self):
        for allocation in self:
            sql ='''
                DELETE FROM stock_pack_operation where picking_id in 
                    (SELECT id FROM stock_picking where allocation_id = %s);
                    
                DELETE FROM account_move where id in (
                SELECT entries_id FROM stock_move where picking_id in 
                    (SELECT id FROM stock_picking where allocation_id = %s));
                    
                DELETE FROM stock_move where picking_id in 
                    (SELECT id FROM stock_picking where allocation_id = %s);
                    
                DELETE FROM stock_picking where allocation_id = %s;
                
            '''%(allocation.id,allocation.id,allocation.id,allocation.id)
            self.env.cr.execute(sql)
            allocation.state = 'draft'
            allocation.contract_id.qty_received = allocation.contract_id.qty_received - allocation.qty_allocation
    
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
    
    def _get_accounting_faq_data(self,line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_input'].id
        acc_dest = accounts.get('stock_valuation', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_dest.id, acc_src
    
    def get_entries_picking_nvp(self,pick):
        move_obj = self.env['account.move']
        move_lines =[]
        
        for move_line_ids in pick.move_lines:
            amount_vn = amount_usd = 0.0
            for move in move_line_ids:
                amount_vn = move.product_qty * move.price_currency
                amount_usd = move.product_qty * move.price_unit
                
            if amount_vn and amount_vn !=0:
                journal_id, acc_src, acc_dest  = self._get_accounting_faq_data(move_line_ids)
                move_lines = self._prepare_account_move_faq_line(move_line_ids, move_line_ids.product_qty ,amount_usd,amount_vn , acc_src,acc_dest)
                if move_lines:
                    if move_line_ids.entries_id:
                        return False
                    ref = move_line_ids.picking_id.name
                    date = move_line_ids.date
                    new_move_id = move_obj.create({'journal_id': journal_id,
                                          'line_ids': move_lines,
                                          'date': date,
                                          'ref': ref,
                                          'warehouse_id':pick.warehouse_id and pick.warehouse_id.id or False,
                                          'narration':False})
                    new_move_id.post()
                    move_line_ids.entries_id = new_move_id.id
                    return  True
            else:
                return False
        
        
    @api.multi
    def approve_allocation(self):
        
        for allocation in self:
#             if allocation.picking_id.qty_available < allocation.qty_allocation:
#                 raise UserError(_('You cannot Approve, Qty Allocation < GRN Qty Available '))
#             if allocation.qty_allocation <=0:
#                 raise UserError(_('You cannot Approve, Qty Allocation  = 0 '))
#             if allocation.qty_allocation + allocation.qty_received > allocation.qty_contract:
#                 raise UserError(_('You cannot Approve, Qty Allocation  > Qty Contract'))
#             if allocation.contract_id.type !='purchase':
#                 if not allocation.picking_id.picking_type_id.picking_type_npe_id:
#                     raise UserError(_('You cannot approve, You must define Picking type for NPE'))
#                 picking_type = allocation.picking_id.picking_type_id.picking_type_npe_id
#             else:
#                 if not allocation.picking_id.picking_type_id.picking_type_nvp_id:
#                     raise UserError(_('You cannot approve, You must define Picking type for NVP'))
#                 picking_type = allocation.picking_id.picking_type_id.picking_type_nvp_id
            
            #kiet: Im NVP
            if allocation.contract_id.type =='purchase':
                #kiet: Trường hợp transfer trạm
                if allocation.picking_id.to_picking_type_id:
                    if not allocation.picking_id.to_picking_type_id.picking_type_nvp_id:
                        raise UserError(_('You cannot approve, You must define Picking type for NVP'))
                    picking_type = allocation.picking_id.to_picking_type_id.picking_type_nvp_id
                #kiet: Trương hợp trại kho chính
                else:
                    if not allocation.picking_id.picking_type_id.picking_type_nvp_id:
                        raise UserError(_('You cannot approve, You must define Picking type for NVP'))
                    picking_type = allocation.picking_id.picking_type_id.picking_type_nvp_id
            
            #kiet: Im NPE
            else:
                if allocation.picking_id.to_picking_type_id:
                    if not allocation.picking_id.to_picking_type_id.picking_type_npe_id:
                        raise UserError(_('You cannot approve, You must define Picking type for NPE'))
                    picking_type = allocation.picking_id.to_picking_type_id.picking_type_npe_id
                else:
                    if not allocation.picking_id.picking_type_id.picking_type_npe_id:
                        raise UserError(_('You cannot approve, You must define Picking type for NPE'))
                    picking_type = allocation.picking_id.picking_type_id.picking_type_npe_id
                #kiet: Trương hợp trại kho chính
            
            var = {
                'warehouse_id':picking_type.warehouse_id.id,
                'picking_type_id': picking_type.id,
                'partner_id': allocation.contract_id.partner_id.id,
                'date': allocation.contract_id.date_order,
                'date_done':allocation.picking_id.date_done,
                'origin': allocation.contract_id.name + ';'+ allocation.picking_id.name,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'location_id': picking_type.default_location_src_id.id,
                'allocation_id':allocation.id,
                'purchase_contract_id':allocation.contract_id.id,
            }
            picking = self.env['stock.picking'].create(var)
            for line in allocation.contract_id.contract_line:
                moves = self._create_stock_moves(line,picking,picking_type,allocation.qty_allocation)
                moves.action_confirm()
                moves.force_assign()
            picking.action_done()
            
            #Kiet: cho sinh bút toán luôn
            self.get_entries_picking_nvp(picking)
            
            allocation.allocation_picking_id = picking.id
            #allocation.date_allocation = time.strftime(DATE_FORMAT)
            allocation.state ='approved'
            allocation.contract_id.qty_received = allocation.contract_id.qty_received + allocation.qty_allocation
            
            
        return True


class NpeNvpRelation(models.Model):
    _inherit = "npe.nvp.relation"
    _order = 'date_fixed desc' 
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d-%m-%Y')
    
    @api.depends('date_fixed')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.date_fixed
            line.day_tz = self.get_vietname_date(line.date_fixed)
            
    qty_received = fields.Float(related='npe_contract_id.qty_received',  string='Received')
    total_qty_fixed = fields.Float(related='npe_contract_id.total_qty_fixed',  string='Total Fixed Qty' ,store=True)
    qty_unfixed = fields.Float(related='npe_contract_id.qty_unfixed',  string='UnFixed')
    #date_fixed = fields.Date(related='contract_id.date_order',  string='Date Fixed',store=True)
    original_npe_qty = fields.Float(related='npe_contract_id.total_qty',  string='Original NPE')
    partner_id = fields.Many2one(related='npe_contract_id.partner_id',  string='Supplier',store=True)
    product_id = fields.Many2one(related='npe_contract_id.product_id',  string='Product',store=True)
    qty_unreceived = fields.Float(related='npe_contract_id.qty_unreceived',  string='UnReceived')
    relation_price_unit = fields.Float(related='contract_id.contract_line.price_unit', string='Fixed Price')
    date_fixed = fields.Date(string='Date Fixed',default= time.strftime(DATE_FORMAT))
    
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    
