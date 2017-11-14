# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

DATE_FORMAT = "%Y-%m-%d"

class SaleContractClam(models.Model):
    _name= 'sale.contract.clam'
    _description = 'Sale Contract Clam'
    _order = 'id desc'
    
    
    contract_id= fields.Many2one('sale.contract', string='Clam', required=True,ondelete='cascade')
    name = fields.Char(string="Reason")
    product_qty = fields.Float(string="Product Qty")
    price_unit = fields.Float(string="Price Unit")
    move_id = fields.Many2one('account.move', string='Move', required=False,ondelete='cascade',readonly = True)
    state = fields.Selection([
        ('draft','Draft'),
        ('validate','Validated'),
        ],'Status', select=True, readonly=True,default='draft')
    
    @api.depends('price_unit','product_qty','state')
    def compute_price(self):
        for order in self:
            if order.product_qty and order.price_unit:
                order.amount = order.product_qty * order.price_unit
            else:
                order.amount = 0.0
            
    amount = fields.Float(string="Amount",compute="compute_price")
    
    def _prepare_account_move_line(self, credit_account_id, debit_account_id):
        debit = credit = self.price_unit * self.product_qty or 0.0
        
        debit_line_vals = {
            'name': self.contract_id.name +'-' + self.name,
            'product_id': False,
            'quantity': self.product_qty,
            'ref': self.name,
            'partner_id': self.contract_id.partner_id.id,
            'debit': debit or 0,
            'credit': 0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': self.contract_id.name +'-' + self.name,
            'product_id': False,
            'quantity': self.product_qty,
            'ref': self.name,
            'partner_id': self.contract_id.partner_id.id,
            'credit': debit,
            'debit': 0,
            'account_id': credit_account_id,
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    @api.multi
    def btt_cancel(self):
        if self.move_id:
            self.move_id.button_cancel()
            self.move_id.unlink()
            self.state = 'draft'
        
    @api.multi
    def btt_validate(self):
        if not self.move_id:
            move_obj = self.env['account.move']
            journal_id = self.env['account.journal'].search([('type','=','sale'),('code','=','BHXK')])
            
            if self.contract_id.type =='export':
                debit_account_id = self.contract_id.product_id.categ_id.property_account_cogs_export.id
            else:
                debit_account_id = self.contract_id.product_id.categ_id.property_account_cogs_local.id
            
            credit_account_id = self.contract_id.product_id.categ_id.property_stock_account_output_categ_id.id
            
            move_lines = self._prepare_account_move_line(credit_account_id, debit_account_id)
            date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            new_move_id = move_obj.create({'journal_id': journal_id.id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': self.contract_id.name +'-' + self.name,
                                      'narration':self.contract_id.name +'-' + self.name})
            
            self.move_id = new_move_id.id
            self.state = 'validate'
            new_move_id.post()
            return True
        
    
class SaleContractLine(models.Model):
    _inherit = "sale.contract.line"
    
   
    
    @api.depends('provisional_g2_price','premium','provisional_g2_diff')
    def _provisional_price(self):
        for sale in self:
            if self.provisional_g2_price:
                sale.provisional_price = self.premium + self.provisional_g2_price + self.provisional_g2_diff
            else:
                sale.provisional_price = 0.0
    
    @api.depends('final_g2_price','premium','final_g2_diff')
    def _final_price(self):
        for sale in self:
            sale.price_unit = self.premium + self.final_g2_price + self.final_g2_diff
            
    certificate_id = fields.Many2one('ned.certificate', string='Certificate', ondelete='restrict')
    premium = fields.Float(string="Premium")
    provisional_g2_price = fields.Float(string="Provisional G2 price",digits=(16, 2))
    provisional_g2_diff = fields.Float(string="Provisional G2 diff",digits=(16, 2))
    provisional_price = fields.Float(compute='_provisional_price',digits=(16, 2),store = True)
    
    final_g2_price = fields.Float(String = 'Final G2 price',digits=(16, 2))
    final_g2_diff = fields.Float(String = 'Final G2 diff',digits=(16, 2))
    price_unit = fields.Float(compute='_final_price',digits=(16, 2),store = True,string="Price")
    

class SaleContract(models.Model):
    _inherit = "sale.contract"
    
    
    def get_years(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%Y')
    
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d-%m-%Y')
                             
    @api.depends('date')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.date
            line.day_tz = self.get_date(line.date)
            line.years_tz = self.get_years(line.date)
            
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    years_tz = fields.Char(compute='_compute_date',string = "Years", store=True)
    
    
    def _get_accounting_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        acc_dest = accounts['stock_output'].id
        if line.type =='export':
            acc_src = accounts.get('cogs_export', False)
        else:
            acc_src = accounts.get('cogs_local', False)
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest
    
    def _prepare_account_move_line(self,line, qty,amount ,  credit_account_id, debit_account_id):
        debit = credit = amount
        partner_id = (line.partner_id and self.pool.get('res.partner')._find_accounting_partner(line.partner_id).id) or False
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
    
    
    def create_entries(self,product_qty,amount):
        move_obj = self.env['account.move']
        move_lines =[]
        contract = self
        
        if amount and amount !=0:
            journal_id, acc_src, acc_dest  = self._get_accounting_data(contract)
            move_lines = self._prepare_account_move_line(contract, product_qty ,amount , acc_dest,acc_src)
            if move_lines:
                
                date = time.strftime(DATE_FORMAT)
                ref = u'''Hàng mất mát %s  ''' %(self.name)
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                contract.entries_id = new_move_id.id
        else:
            return False
    
    @api.model
    def cron_create_entries_loss(self,ids=None):
#         sale_ids = self.env['sale.contract'].search([('state','=','done'),('entries_id','=',False)])
#         for move in sale_ids:
#             move.button_action_done()
        return 1
    @api.multi
    def button_action_done(self):
#         if self.entries_id:
#             return
#         if self.loss_qty and  self.loss_qty >0:
#             loss_qty = self.loss_qty
#             amount_loss = qty_out_fifo = amount_do =0.0
#             
#             for do in self.delivery_ids:
#                 if do.picking_id:
#                     for move in do.picking_id.move_lines:
#                         amount_do += move.price_out_fifo
#                         qty_out_fifo += move.qty_out_fifo
#             
#             if qty_out_fifo and self.do_qty == qty_out_fifo:
#                 amount_loss  = loss_qty * (amount_do / qty_out_fifo)
#             if amount_loss and amount_loss !=0.0:
#                 self.create_entries( loss_qty, amount_loss)
        
        self.state = 'done'
        
    @api.model
    def _default_crop_id(self):
        crop_ids = self.env['ned.crop'].search([('state', '=', 'current')], limit=1)
        return crop_ids
    
    crop_id = fields.Many2one('ned.crop', string='Crop', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_crop_id)
    
    product_id = fields.Many2one(related='contract_line.product_id',  string='Product',store=True)
    price_unit = fields.Float(related='contract_line.price_unit',  string='Price Unit')
    entries_id = fields.Many2one('account.move',  string='Entries')
    
    @api.depends('delivery_ids','delivery_ids.total_qty','contract_line','contract_line.product_qty','invoice_ids','invoice_ids.state','invoice_ids.invoice_line_ids','invoice_ids.invoice_line_ids.quantity','invoice_ids.invoice_line_ids.price_unit')
    def _do_qty(self):
        for order in self:
            total_qty = 0
            total_invoice_qty = 0
            invoiced_amount_total = 0
            date_invoice = False
            
            for line in order.delivery_ids:
                total_qty += line.total_qty
                
            for line in order.invoice_ids:
                for i in line.invoice_line_ids:
                    total_invoice_qty += i.quantity
                date_invoice = line.date_invoice
                if line.state =='draft':
                    continue
                invoiced_amount_total += line.amount_total
                
            order.invoiced_qty = total_invoice_qty
            order.invoiced_amount_total = invoiced_amount_total
            
            order.do_qty = total_qty
            order.remain_qty = order.total_qty - order.do_qty
            order.loss_qty = total_qty - (total_invoice_qty * 1000)
            order.date_invoice = date_invoice
            
    do_qty = fields.Float(compute='_do_qty', digits=(12, 0) , string='Do Qty', store=True)
    remain_qty = fields.Float(compute='_do_qty', digits=(12, 0) , string='Remain Do' ,store=True)
    loss_qty = fields.Float(compute='_do_qty', digits=(12, 0) , string='Los Qty',store=True)
    
    invoiced_qty = fields.Float(compute='_do_qty', digits=(12, 2) , string='Invoiced Qty. (Mt)',store=True)
    invoiced_amount_total = fields.Monetary(compute='_do_qty', digits=(12, 3) , string='Invoiced Total',store=True)
    date_invoice = fields.Date(compute='_do_qty', digits=(12, 3) , string='Date Invoice',store=True)
    
    
    @api.depends('invoice_ids','invoice_ids.state','invoice_ids.invoice_line_ids','invoice_ids.invoice_line_ids.quantity','invoice_ids.invoice_line_ids.price_unit')
    def _invoiced_qty(self):
        for order in self:
            total_invoice_qty = 0
            invoiced_amount_total = 0;
            for line in order.invoice_ids:
                if line.state =='draft':
                    continue
                for i in line.invoice_line_ids:
                    total_invoice_qty += i.quantity
                invoiced_amount_total += line.amount_total
            order.invoiced_qty = total_invoice_qty
            order.invoiced_amount_total = invoiced_amount_total
            
    
    
    @api.depends('contract_line','contract_line.product_qty')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.contract_line:
                total_qty += line.product_qty
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Qty',store =True)
    certificate_id = fields.Many2one(related='contract_line.certificate_id',  string='Certificate',)
    p_contract = fields.Char(string="P Contract")
    
    clam_ids = fields.One2many('sale.contract.clam', 'contract_id', 'Clam', readonly=False)
    
    @api.multi
    def print_printout_nvs(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'printout_nvs_report'}
    

    @api.multi
    def button_load(self):
        if self.shipping_id:
            self.env.cr.execute('''DELETE FROM sale_contract_line WHERE contract_id = %s''' % (self.id))
            product_qty = new_qty = 0.0
            val ={
                  'scontract_id':self.shipping_id.contract_id and self.shipping_id.contract_id.id or False,
                  'partner_id':self.shipping_id.partner_id and self.shipping_id.partner_id.id or False,
                  'currency_id':self.shipping_id.contract_id.currency_id and self.shipping_id.contract_id.currency_id.id or False,
                  'port_of_loading': self.shipping_id.port_of_loading and self.shipping_id.port_of_loading.id or False,
                  'port_of_discharge': self.shipping_id.port_of_discharge and self.shipping_id.port_of_discharge.id or False,
                  'weights':self.shipping_id.contract_id and self.shipping_id.contract_id.weights or False,
                }
            self.write(val)
            
            for shipping in self.shipping_id.shipping_ids:
                for nvs in self.shipping_id.contract_ids:
                    if nvs.state != 'cancel':
                        for nvs_line in nvs.contract_line:
                            if nvs_line.product_id == shipping.product_id:
                                product_qty += nvs_line.product_qty
                new_qty = shipping.product_qty - product_qty
                var = {'contract_id': self.id or False, 'name': shipping.name or False, 'product_id': shipping.product_id.id or False,
                       'tax_id': [(6, 0, [x.id for x in shipping.tax_id])] or False, 'price_unit': shipping.price_unit or 0.0,
                       'product_qty': new_qty or 0.0, 'product_uom': shipping.product_uom.id or False,
                       'state': 'draft', 'certificate_id': shipping.certificate_id.id or False}
                self.env['sale.contract.line'].create(var)
                
        return True
    
