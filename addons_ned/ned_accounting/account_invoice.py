# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class account_period(models.Model):
    _inherit = "account.period"
    
    close_warehouse = fields.Boolean('Closed Warehouse',default=False)
    
class AccountJournal(models.Model):
    _inherit = "account.journal"
    
    unallow_generate_entry = fields.Boolean(string="Unallow generate entry",default=False)
    pre_finance_id = fields.Many2one('account.journal',string="Pre-finance")
    
    
class AccountAccount(models.Model):
    _inherit = 'account.account'

    name_eng = fields.Char(string="Name Eng")
    
class StockPickingType(models.Model):
    _inherit = "stock.picking.type"
    
    @api.multi
    def write(self, vals):
        result = super(StockPickingType, self).write(vals)
        return result
    
    #Thanh: Add some options for code
    code = fields.Selection([('incoming', 'Suppliers'), 
                                  ('outgoing', 'Customers'), 
                                  ('adjust_stock', 'Adjust Stock'), 
                                  ('internal', 'Internal'),
                                  ('transfer_out', 'Transfer Out'),
                                  ('transfer_in', 'Transfer In'),
                                  ('internal', 'Internal'),
                                  ('return_customer', 'Return Customers'), 
                                  ('return_supplier', 'Return Supplier'), 
                                  ('production_out', 'Production Out'),
                                  ('production_in', 'Production In'),
                                  ('phys_adj', 'Physical Adjustment')], 'Type of Operation', required=True)

class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    #THANH: when user change rate manually, this field will be updated to False and these is a cron to update rate to Account Move Line
    stock_update_rate =fields.Boolean(string="Stock Move Update", default = False)
    
    @api.multi
    def write(self, vals):
        vals.update({'stock_update_rate':False})
        return super(ResCurrencyRate, self).write(vals)
    
class ResCurrency(models.Model):
    _inherit = "res.currency"
    
    @api.model
    def cron_update_rate_for_stock_move(self,ids=None):
        company_currency_id = self.env['res.users'].browse(self.env.uid).company_id.currency_id
        second_currency_id = self.env['res.users'].browse(self.env.uid).company_id.second_currency_id
        sql ='''
            SELECT id, name, rate, currency_id
            FROM res_currency_rate
            WHERE stock_update_rate != true
        '''
        self.env.cr.execute(sql)
        for rate in self.env.cr.dictfetchall():
            #Kiet: Trường hợp update lại phân bổ + giá Price _unit khi thay doi Rate currency
            allocation_ids = []
            sql = '''
                SELECT id 
                FROM 
                    stock_move_allocation
                WHERE date(timezone('UTC', in_date::timestamp)) = date(timezone('UTC', '%s'::timestamp))
            '''%(rate['name'])
            self.env.cr.execute(sql)
            for records in self.env.cr.dictfetchall():
                allocation_ids.append(records['id'])
            if allocation_ids:
                for allocation in self.env['stock.move.allocation'].browse(allocation_ids):
                    if allocation.from_move_id.picking_id and allocation.from_move_id.picking_id.purchase_contract_id:
                        price_unit = 0.0
                        purchase_contract_id = allocation.from_move_id.picking_id.purchase_contract_id
                        for line in allocation.from_move_id.picking_id.purchase_contract_id.contract_line:
                            if allocation.product_id == line.product_id:
                                if purchase_contract_id.type == 'purchase':
                                    price_unit = line.price_unit
                                    allocated_value = allocation.allocated_qty * price_unit
                                    allocation.allocated_value = second_currency_id.with_context(date=purchase_contract_id.date_order).compute(allocated_value, 
                                                                                    company_currency_id)
                        if price_unit:
                            allocation.from_move_id.price_unit= second_currency_id.with_context(date=purchase_contract_id.date_order).compute(price_unit, 
                                                                                    company_currency_id)
            sql ='''
                UPDATE res_currency_rate 
                SET stock_update_rate = true 
                WHERE id = %s
            '''%(rate['id'])
            self.env.cr.execute(sql)
    
class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"
    
    notes = fields.Char(string="Notes")
    nvs_nls_id = fields.Many2one('sale.contract', string="NVS-NLS")
    
    @api.model
    def create(self, vals):
        result = super(AccountPayment, self).create(vals)
        return result
    
    @api.model
    def default_get(self, fields): 
        rec = super(AccountPayment, self).default_get(fields)
        active_id = self._context.get('active_id')
        if self._context.get('active_model') and self._context.get('active_model') == 'request.payment':
            request_amount =0.0
            request = self.env['request.payment'].browse(active_id)
            rec['communication'] = request.name
            rec['currency_id'] = request.purchase_contract_id.currency_id.id
            rec['payment_type'] = 'outbound'
            rec['partner_id'] = request.purchase_contract_id.partner_id.id
            rec['purchase_contract_id'] = request.purchase_contract_id.id
            rec['request_payment_id'] =  active_id
            
            for payment in request.request_payment_ids:
                request_amount += payment.amount 
            
            rec['amount'] = request.request_amount - (request_amount or 0.0)
            
            
            if request.purchase_contract_id.type !='purchase':
                rec['extend_payment'] = 'advance'
                rec['communication'] = u'Tạm ứng theo ' + request.purchase_contract_id.name
            else:
                rec['extend_payment'] = 'payment'
                rec['communication'] = u'Thanh toán tiền theo ' + request.purchase_contract_id.name
        
        if self._context.get('active_model') and self._context.get('active_model') == 'purchase.contract':
            contract_id = self.env[self._context.get('active_model')].browse(active_id)
            rec['communication'] = contract_id.name
            rec['currency_id'] = contract_id.currency_id.id
            rec['payment_type'] = 'outbound'
            rec['partner_id'] = contract_id.partner_id.id
            rec['purchase_contract_id'] = contract_id.id
            rec['communication'] = u'Thanh toán tiền theo ' + contract_id.name
            rec['extend_payment'] = 'payment'
            rec['amount'] = contract_id.amount_total
        return rec

class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
    
    
    @api.multi
    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_invoice_tree2')
        result = action.read()[0]

        #override the context to get rid of the default filtering
        result['context'] = {'type': 'in_invoice', 'default_purchase_id': self.id}

        if not self.invoice_ids:
            # Choose a default account journal in the same currency in case a new invoice is created
            journal_domain = [
                ('type', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('currency_id', '=', self.currency_id.id),
            ]
            default_journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            if default_journal_id:
                result['context']['default_journal_id'] = default_journal_id.id
        else:
            # Use the same account journal than a previous invoice
            result['context']['default_journal_id'] = self.invoice_ids[0].journal_id.id

        #choose the view_mode accordingly
        if len(self.invoice_ids) != 1:
            result['domain'] = "[('id', 'in', " + str(self.invoice_ids.ids) + ")]"
        elif len(self.invoice_ids) == 1:
            res = self.env.ref('account.invoice_supplier_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.invoice_ids.id
        return result
    
    @api.multi
    def btt_allocation(self):
        sql ='''
            SELECT id FROM stock_picking 
            WHERE partner_id = %s 
                and picking_type_code = 'incoming'
                and state= 'done'
                and id not in (
                    SELECT picking_id 
                    FROM stock_allocation
                    WHERE contract_id = %s)
        '''%(self.partner_id.id,self.id)
        self.env.cr.execute(sql)
        for contract in self.env.cr.dictfetchall():
            allocation_qty = 0
            picking = self.env['stock.picking'].browse(contract['id'])
            sql ='''
                    SELECT sum(qty_allocation) sum_qty 
                    FROM stock_allocation
                    WHERE picking_id = %s 
                '''%(picking.id)
            self.env.cr.execute(sql)
            for allocation in self.env.cr.dictfetchall():
                allocation_qty = allocation['sum_qty'] or 0.0
            if picking.total_qty <= allocation_qty:
                continue
            self.env['stock.allocation'].create({'contract_id':self.id,'picking_id':picking.id})
        return True
    
    @api.multi
    def btt_load_invoice(self):
        for contract in self:
            sql ='''
                SELECT id invoice_id
                FROM account_invoice 
                WHERE partner_id = %s 
                    and state not in ('draft','cancel')
                    and type = 'in_invoice'
            '''%(contract.partner_id.id)
            self.env.cr.execute(sql)
            for invoiced in self.env.cr.dictfetchall():
                
                allocation_values =0.0
                invoice_obj = self.env['account.invoice'].browse(invoiced['invoice_id'])
                sql ='''
                    SELECT sum(value_allocation) sum_allocation 
                    FROM invoiced_allocation
                    WHERE account_id = %s 
                '''%(invoiced['invoice_id'])
                self.env.cr.execute(sql)
                for allocation in self.env.cr.dictfetchall():
                    allocation_values = allocation['sum_allocation'] or 0.0
                if invoice_obj.amount_total <= allocation_values:
                    continue
                allocation = self.env['invoiced.allocation'].search([('contract_id','=',self.id),('account_id','=',invoiced['invoice_id'])])
                if allocation:
                    continue
                self.env['invoiced.allocation'].create({'contract_id':self.id,'account_id':invoiced['invoice_id']})
        return 1
    
    @api.depends('qty_invoiced_received','invoice_allocation_ids','invoice_allocation_ids.qty_allocation','contract_line.product_qty')
    def _received_invoice_qty(self):
        for contract in self:
            contract.qty_invoiced_unreceived = contract.total_qty - contract.qty_invoiced_received
            
    #Qty Allocation StockPicking
    qty_invoiced_received = fields.Float(string ='Invoiced Received',digits=(12, 0))
    qty_invoiced_unreceived = fields.Float(compute='_received_invoice_qty',string ='Invoiced UnReceived',digits=(12, 0),store = True)
    #Qty NVP
    invoice_allocation_ids = fields.One2many('invoiced.allocation','contract_id',string='Invoice Allocation')
    price_unit = fields.Float(related='contract_line.price_unit',string='Price Unit Contract',digits=(12, 0),readonly=True,store= True)
    stock_allocation_ids = fields.One2many('stock.allocation','contract_id', 'Allocation')
    
    
    @api.depends('contract_line.price_total','contract_line.price_unit','pay_allocation_ids','pay_allocation_ids.allocation_amount',
         'request_payment_ids','request_payment_ids.total_payment','payment_ids','payment_ids.amount','stock_allocation_ids',
         'stock_allocation_ids.qty_allocation',
         'pay_allocation_ids.allocation_line_ids'
         )
    def _amount_all(self):
        for contract in self:
            price_unit = 0.0
            amount_untaxed = amount_tax = 0.0
            for line in contract.contract_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                price_unit = line.price_unit
            
            amount = 0.0
            amount_deposit = 0.0
            sub_rel = 0.0
            if not contract.nvp_ids:
                for stock in contract.stock_allocation_ids:
                    sub_rel += stock.qty_allocation
            else:
                for alls in contract.contract_line:
                    sub_rel += alls.product_qty 
            
            sub_rel = sub_rel * price_unit
                
            for deposit in contract.pay_allocation_ids:
                amount_deposit += deposit.allocation_amount or 0.0
                for interest in deposit.allocation_line_ids:
                    amount += interest.actual_interest_pay
                    
            for deposit in contract.payment_ids:
                amount_deposit += deposit.amount
                
            amount = abs(amount) * (-1)
            amount_deposit = abs(amount_deposit) * (-1)
            
            contract.update({
                'amount_untaxed': contract.currency_id.round(amount_untaxed),
                'amount_tax': contract.currency_id.round(amount_tax),
                'amount_sub_total':amount_untaxed + amount_tax,
                'amount_total': sub_rel + amount + amount_deposit,
                'amount_sub_rel_total':sub_rel,
                'total_interest_pay':abs(amount),
                'amount_deposit':abs(amount_deposit)
            })
        
    total_interest_pay = fields.Monetary(compute='_amount_all', string='Interest', readonly=True, store=True, track_visibility='always')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Payable', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_sub_total = fields.Monetary(string='Sub total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_sub_rel_total = fields.Monetary(string='Sub Real total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_deposit = fields.Monetary(string='Paid', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
   
    @api.depends('invoice_allocation_ids','invoice_allocation_ids.value_allocation','invoice_allocation_ids.qty_allocation')
    def _values_invoiced(self):
        for contract in self:
            amount = 0
            for line in contract.invoice_allocation_ids:
                if line.qty_allocation and line.value_allocation:
                    amount += line.qty_allocation * line.value_allocation
                if not line.qty_allocation and line.value_allocation:
                    amount += 1 * line.value_allocation
            contract.values_invoiced = amount
    values_invoiced = fields.Float(compute='_values_invoiced',string ='Total Invoiced',digits=(12, 0), store = False)
    
    
    @api.depends('contract_line.product_qty','state','nvp_ids','npe_ids','npe_ids.product_qty','nvp_ids.product_qty','stock_allocation_ids','stock_allocation_ids.state','stock_allocation_ids.qty_allocation','stock_allocation_ids.contract_id','stock_allocation_ids.picking_id')
    def _received_qty(self):
        for contract in self:
            if contract.nvp_ids:
                received = 0
                for line in contract.nvp_ids:
                    received += line.product_qty
                contract.qty_unreceived = contract.total_qty - received
                contract.qty_received = received
            else:
                received = 0
                for line in contract.stock_allocation_ids:
                    if line.state == 'approved':
                        received += line.qty_allocation or 0.0
                contract.qty_unreceived = contract.total_qty - received
                contract.qty_received = received
            
            
            
            fix = 0.0
            for line in contract.npe_ids:
                fix += line.product_qty
             
            contract.qty_unfixed = received - fix
            contract.total_qty_fixed = fix
    
    qty_received = fields.Float(compute='_received_qty',string ='Received',digits=(12, 0),store = False)
    qty_unreceived = fields.Float(compute='_received_qty',string ='UnReceived',digits=(12, 0),store = False)
            
    total_qty_fixed = fields.Float(compute='_received_qty',string = 'Fixed',digits=(12, 0),store = False)
    qty_unfixed = fields.Float(compute='_received_qty',string ='UnFixed',digits=(12, 0),store = False)
    
    
    
class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line" 
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_ids', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id', 'invoice_id.company_id')
    def _compute_price(self):
        for line in self:
            try:
                currency = line.invoice_id and line.invoice_id.currency_id or None
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                taxes = False
                quantity = line.quantity or 1
                if line.invoice_line_tax_ids:
                    taxes = line.invoice_line_tax_ids.compute_all(price, currency, quantity, product=line.product_id, partner=line.invoice_id.partner_id)
                line.price_subtotal = price_subtotal_signed = taxes['total_excluded'] if taxes else quantity * price
                if line.invoice_id.currency_id and line.invoice_id.currency_id != line.invoice_id.company_id.currency_id:
                    price_subtotal_signed = self.invoice_id.currency_id.compute(price_subtotal_signed, line.invoice_id.company_id.currency_id)
                sign = line.invoice_id.type in ['in_refund', 'out_refund'] and -1 or 1
                line.price_subtotal_signed = price_subtotal_signed * sign
            except Exception, e:
                continue
            
            
    quantity = fields.Float(string='Quantity', digits=(12, 3),
        required=True, default=1)
    price_unit = fields.Float(string='Unit Price', required=True, digits=(12, 3))
    
        
    price_subtotal = fields.Monetary(string='Amount',
        store=True, readonly=True, compute='_compute_price',digits=(12, 3))
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_price',
        help="Total amount in the currency of the company, negative for credit notes.")
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice" 

    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            if inv.payment_move_line_ids:
                raise UserError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))
            
            if inv.stock_move_id:
                move = inv.stock_move_id
                move.remove_fifo()
                move.action_cancel()
                move.unlink()
        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            moves.line_ids.remove_move_reconcile()
            moves.button_cancel()
            moves.unlink()
        return True
    
    @api.multi
    def confirm_paid(self):
        for inv in self:
            if inv.type == 'in_invoice' and inv.journal_id.type == 'purchase':
                return True
        return self.write({'state': 'paid'})
    
    @api.multi
    def action_move_create(self):
        for inv in self:
            if inv.type == 'out_invoice':
                inv.create_stock_move()
            if inv.journal_id.unallow_generate_entry:
                inv.number = 'Vendor Bill ' + inv.reference
                inv.state = 'open'
                return True
        return super(AccountInvoice, self).action_move_create()
        
    def create_stock_move(self):
        # Thành phẩm
        for inv in self:
            if inv.type == 'out_invoice':
                if inv.sale_contract_id:
                    if inv.stock_move_id:
                        move = inv.stock_move_id
                        move.remove_fifo()
                        move.action_cancel()
                        move.unlink()
                        
                    product_qty =0.0
                    product_id = False
                    price = 0.0
                    for line in inv.invoice_line_ids:
                        product_qty += (line.quantity *1000) or 0.0
                        product_id = line.product_id
                        #price = line.price_unit/1000
                        if inv.sale_contract_id.type == 'export':
                            pick = inv.sale_contract_id.warehouse_id.out_type_id
                            location_id = pick.default_location_dest_id
                            location_dest_id = self.env['stock.location'].search([('usage','=','customer')])
                        else:
                            pick = inv.sale_contract_id.warehouse_id.out_type_local_id
                            location_id = pick.default_location_dest_id
                            location_dest_id = self.env['stock.location'].search([('usage','=','customer')])
                    if product_qty:
                        note = ''
                        if inv.number:
                            note = inv.number +' - '
                        if inv.sale_contract_id:
                            note += inv.sale_contract_id.name
                        data = {
                            'partner_id':inv.partner_id.id,
                            'product_uom_qty':product_qty,
                            'price_unit':price,
                            'location_id':location_id.id or False,
                            'name': product_id.default_code,
                            'date': inv.date_invoice,
                            'product_id': product_id.id,
                            'product_uom': product_id.uom_id.id,
                            'location_dest_id': location_dest_id.id,
                            'company_id': inv.company_id.id,
                            'origin':inv.reference or inv.name,
                            'note':note,
                            'state': 'done'}
                        new_id = self.env['stock.move'].create(data)
                        inv.stock_move_id = new_id.id
                    
                    
                    
        return True
    
    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            result.append((inv.id, "%s %s" % (TYPES[inv.type], inv.reference or '')))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    @api.depends('allocation_ids','allocation_ids.value_allocation')
    def _compute_allocation(self):
        for invoice in self:
            values = 0.0
            for allocation in invoice.allocation_ids:
                values += allocation.value_allocation
            invoice.value_allocation = values
        return 
    
    
    allocation_ids = fields.One2many('invoiced.allocation','account_id', string='Allocation')
    value_allocation = fields.Float(compute='_compute_allocation', string = 'Allocation', digits=(12, 0))
    stock_move_id = fields.Many2one('stock.move', string="Stock Move")
    res_partner_id = fields.Many2one('res.partner', string="End buyer")
    date_pre_finance = fields.Date(string="Date Pre-finance")
    pre_finance_id = fields.Many2one('account.move',string="Pre-finance")
    product_id = fields.Many2one(related='invoice_line_ids.product_id',  string='Product',store = True)
    
    @api.multi
    def btt_clearing_debt(self):
        for inv in self:
            if inv.pre_finance_id:
                continue
            if inv.move_id:
                credit_account_id = inv.account_id.id 
                debit_account_id = inv.partner_id.property_customer_advance_acc_id.id
                if not inv.journal_id.pre_finance_id:
                    return True
                if not self.date_pre_finance:
                    raise UserError(_("Nhập Date Pre-Finance"))
                pre_finance_id = inv.journal_id.pre_finance_id.id
                for line in inv.invoice_line_ids:
                    self._create_account_move_line(line,debit_account_id,credit_account_id,pre_finance_id)
                return True
    
    
    def _create_account_move_line(self, line,debit_account_id, credit_account_id , journal_id):
        move_obj = self.env['account.move']
        move_lines = self._prepare_account_move_line(line, line.quantity, line.price_unit, debit_account_id, credit_account_id)
        date = self.date_pre_finance
        new_move_id = move_obj.create({'journal_id': journal_id,
                                  'line_ids': move_lines,
                                  'date': date,
                                  'ref': line.invoice_id.number,
                                  'narration':line.invoice_id.name})
        self.pre_finance_id = new_move_id
        new_move_id.post()
        return new_move_id
    
    def _prepare_account_move_line(self,line, qty, cost, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        debit = line.price_unit * qty
        #check that all data is correct
        
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        
        partner_id = (self.partner_id and self.pool.get('res.partner')._find_accounting_partner(self.partner_id).id) or False
        debit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': self.name or False,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit':  0.0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'account_id': debit_account_id,
        }
        credit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': self.name or False,
            'partner_id': partner_id,
            'credit': debit, 
            'debit':  0.0,
            'second_ex_rate':self.currency_id.rate or 0.0,
            'account_id': credit_account_id,
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    @api.multi
    def btt_load(self):
        sql ='''
            SELECT id 
            FROM purchase_contract 
            WHERE partner_id = %s 
                and state = 'approved'
                and type = 'purchase'
                and id not in (
                    SELECT contract_id 
                    FROM invoiced_allocation
                    WHERE account_id = %s)
        '''%(self.partner_id.id,self.id)
        self.env.cr.execute(sql)
        for contract in self.env.cr.dictfetchall():
            contract = self.env['purchase.contract'].browse(contract['id'])
            if contract.qty_invoiced_received > contract.total_qty:
                continue
            self.env['invoiced.allocation'].create({'contract_id':contract.id,'account_id':self.id})
        return 1
    
AccountInvoice()

class InvoicedAllocation(models.Model):
    _name = "invoiced.allocation"

#     @api.depends('contract_id','account_id','qty_allocation','value_allocation','state','account_id.state','contract_id.state')
#     def _compute_total_value(self):
#         for order in self:
#             qty_allocation = order.qty_allocation or 1
#             if order.qty_allocation:
#                 order.value_allocation = qty_allocation * order.price_unit
#             else:
#                 order.value_allocation = order.value_allocation
        
                
                    
    contract_id = fields.Many2one('purchase.contract', string='Contract')
    account_id = fields.Many2one('account.invoice', string='Invoiced')
    currency_id = fields.Many2one(related='account_id.currency_id',string='Currency')
    amount_total = fields.Monetary(related='account_id.amount_total',string='Amount Total',digits=(12, 0))
    price_unit = fields.Float(related='account_id.invoice_line_ids.price_unit',string='Price Unit',digits=(12, 0))
    qty_invoiced = fields.Float(related='account_id.total_qty',string='Qty Invoiced',digits=(12, 0))
    qty_contract = fields.Float(related='contract_id.total_qty',string='Qty Contract',digits=(12, 0))
    date_contract = fields.Date(related='contract_id.date_order',string='Date Contract')
    state = fields.Selection([('draft', 'New'), ('approved', 'Approved')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
    qty_allocation = fields.Float(string='Qty Allocation',digits=(12, 0))
    value_allocation = fields.Float(string = 'Values Allocation',digits=(12, 0))
    
#     @api.depends('contract_id','value_allocation','qty_allocation')
#     def _compute_amount_avaliable(self):
#         for order in self:
#             allocation_ids = []
#             if order.contract_id and order.account_id:
#                 try:
#                     sql ='''
#                         SELECT id
#                         FROM invoiced_allocation
#                         WHERE account_id = %s
#                     '''%(order.account_id.id)
#                     self.env.cr.execute(sql)
#                     for line in self.env.cr.dictfetchall():
#                         allocation_ids.append(line['id'])
#                     
#                     value_allocation = 0.0
#                     for line in self.env['invoiced.allocation'].browse(allocation_ids):
#                         if line.qty_allocation and line.value_allocation:
#                             value_allocation += line.qty_allocation * line.value_allocation
#                         if not line.qty_allocation and line.value_allocation:
#                             value_allocation += 1 * line.value_allocation
#                             
#                     order.amount_avaliable = order.account_id.amount_total - value_allocation
#                 except Exception, e:
#                     continue
#     
#     @api.depends('value_allocation','qty_allocation')
#     def _compute_amount_invoice_allocation(self):
#         for order in self:
#             allocation_ids = []
#             if order.contract_id and order.account_id:
#                 try:
#                     sql ='''
#                         SELECT id
#                         FROM invoiced_allocation
#                         WHERE account_id = %s and contract_id = %s
#                     '''%(order.account_id.id,order.contract_id.id)
#                     self.env.cr.execute(sql)
#                     for line in self.env.cr.dictfetchall():
#                         allocation_ids.append(line['id'])
#                     value_allocation = 0.0
#                     for line in self.env['invoiced.allocation'].browse(allocation_ids):
#                         if line.qty_allocation and line.value_allocation:
#                             value_allocation += line.qty_allocation * line.value_allocation
#                         if not line.qty_allocation and line.value_allocation:
#                             value_allocation += 1 * line.value_allocation
#                     order.amount_allocation  = value_allocation
#                 except Exception, e:
#                     continue
    
#     amount_allocation = fields.Float(compute='_compute_amount_invoice_allocation',string = 'Amount Allocation', digits=(12, 0),store =True)
#     amount_avaliable = fields.Float(compute='_compute_amount_avaliable',string = 'Available', digits=(12, 0))
    

    @api.multi
    def button_approved(self):
        self.contract_id.qty_invoiced_received = self.contract_id.qty_invoiced_received + self.qty_allocation
        self.write({'state': 'approved'})
    
    @api.multi
    def cancel_allocation(self):
        self.contract_id.qty_invoiced_received = self.contract_id.qty_invoiced_received - self.qty_allocation
        self.write({'state': 'draft'})
    