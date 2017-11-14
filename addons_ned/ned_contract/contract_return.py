# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

DATE_FORMAT = "%Y-%m-%d"



class ContractReturn(models.Model):
    _name = "contract.return"
    _order = 'date_return desc, id desc'
    
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env.user.company_id.second_currency_id.id
        return currency_ids
    
    @api.depends('picking_ids')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.picking_ids:
                moves = line.move_lines.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)
            
    @api.depends('contract_return_line.price_total')
    def _amount_all(self):
        for contract in self:
            amount_untaxed = amount_tax = 0.0
            for line in contract.contract_return_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            contract.update({
                'amount_untaxed': contract.currency_id.round(amount_untaxed),
                'amount_tax': contract.currency_id.round(amount_tax),

            })
    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])
        return types[:1]
    
    
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.One2many('stock.picking', 'purchase_contract_id' , 'Picking Line', readonly=True)
            
    name = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('contract.return'))
    company_representative = fields.Many2one("res.partner", string="Company Representative", readonly=True, states={'draft': [('readonly', False)]})
    
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current Purchase order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Delivery address for current Purchase order.")

    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
      
    partner_id = fields.Many2one('res.partner', string='Supplier', readonly=True, states={'draft': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')

    date_return = fields.Date(string='Date Return', readonly=True, copy=False, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=False, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    
    contract_return_line = fields.One2many('contract.return.line', 'contract_id', string='Contract Return Lines', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    note = fields.Text('Terms and conditions')
    origin = fields.Char(string='Source Document')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Receivable', store=True, readonly=True, track_visibility='always')
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    date_done = fields.Date('Date Done', readonly=True, select=True, copy=False)
    
    
    payment_ids = fields.One2many('account.payment','contract_return_id', string='Payment', )
    group_id = fields.Many2one('procurement.group', string="Procurement Group")
    
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.One2many('stock.picking', 'purchase_contract_id' , 'Picking Line', readonly=True)
    
    product_id = fields.Many2one(related='contract_return_line.product_id',  string='Product')
    
    npe_contract = fields.Many2one('purchase.contract', string="NPE Contracts")
    
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=True, default=_default_picking_type,\
        help="This will determine picking type of incoming shipment")
    picking_id = fields.Many2one('stock.picking', string="Stock Picking")

    
    
    
    
    def _total_qty(self): 
        for order in self:
            total_qty = 0
            for line in order.contract_return_line:
                total_qty += line.product_qty
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Quantity')
    
    def _total_price(self):
        for order in self:
            total_price = 0
            for line in order.contract_return_line:
                total_price += line.price_unit
            order.total_price = total_price
            
    total_price = fields.Float(compute='_total_price', digits=(16, 0) , string='Price')
    
    def _total_value(self):
        for order in self:
            total_value = 0
            for line in order.contract_return_line:
                total_value += line.price_subtotal
            order.total_value = total_value
            
    total_value = fields.Float(compute='_total_value', digits=(16, 0) , string='Total Value')
    
    def _total_remain(self):
        for order in self:
            total_remain = 0
            total_payment = 0
            for line in order.payment_ids:
                total_payment += line.amount
            order.total_remain = order.amount_total - total_payment
            
    total_remain = fields.Float(compute='_total_remain', digits=(16, 0) , string='Total Remain')
    
    def _total_payment(self):
        for order in self:
            order.total_payment = order.amount_total - order.total_remain
            
    total_payment = fields.Float(compute='_total_payment', digits=(16, 0) , string='Total Payment')
    
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('contract.return') or 'New'
            
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
        result = super(ContractReturn, self).create(vals)
        return result
    
    @api.multi
    def _get_destination_location(self):
        self.ensure_one()
        return self.picking_type_id.default_location_dest_id.id
    

    
    @api.model
    def _prepare_picking(self):
    
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.date_return,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.partner_id.property_stock_supplier.id,
            'company_id': self.company_id.id,
        }

    @api.multi
    def _create_picking(self):
        for order in self:
            res = order._prepare_picking()
            picking = self.env['stock.picking'].create(res)
            moves = order.contract_return_line._create_stock_moves(picking)
            move_ids = moves.action_confirm()
            moves = self.env['stock.move'].browse(move_ids)
            moves.force_assign()
            order.picking_id = picking.id
        return True
    
    
    @api.multi
    def button_approve(self):
        for contract in self:
            if not contract.contract_return_line:
                raise UserError(_('You cannot approve a contract return without any contract return line.'))
            
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        self._create_picking()
        
    @api.multi
    def print_contract_return(self):
        return {'type': 'ir.actions.report.xml','report_name':'report_contract_return'}
    
    
    
    
class ContractReturnLine(models.Model):
    _name = "contract.return.line"
    
    
    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.contract_id.partner_id.property_account_position_id
            if fpos:
                if self.env.uid == SUPERUSER_ID and line.contract_id.company_id:
                    taxes = fpos.map_tax(line.product_id.taxes_id).filtered(lambda r: r.company_id == line.contract_id.company_id)
                else:
                    taxes = fpos.map_tax(line.product_id.taxes_id)
                line.tax_id = taxes
            else:
                line.tax_id = line.product_id.taxes_id if line.product_id.taxes_id else False
                
    @api.depends('product_qty', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit
            taxes = line.tax_id.compute_all(price, line.contract_id.currency_id, line.product_qty, product=line.product_id, partner=line.contract_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    
    
    
    contract_id = fields.Many2one('contract.return', string='Contract Return Reference', ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    
    company_id = fields.Many2one(related='contract_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', store=True, string='Customer')
    
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')],
         related='contract_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    currency_id = fields.Many2one(related='contract_id.currency_id', store=True, string='Currency', readonly=True)
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_qty = fields.Float(string='Qty', digits=(12, 0), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='UoM', required=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes',)
    
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True,digits=(16, 0))
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    delivery_tolerance = fields.Float(string="Delivery Tolerance", default=0.0)
    
    
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        if not (self.product_uom and (self.product_id.uom_id.category_id.id == self.product_uom.category_id.id)):
            vals['product_uom'] = self.product_id.uom_id

        product = self.product_id.with_context(
            lang=self.contract_id.partner_id.lang,
            partner=self.contract_id.partner_id.id,
            quantity=self.product_qty,
            uom=self.product_uom.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.contract_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
        self.update(vals)
        return {'domain': domain}
    
    
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:

            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.contract_id.date_return,
#                 'date_expected': line.date_planned,
                'location_id': line.contract_id.partner_id.property_stock_supplier.id,
                'location_dest_id': line.contract_id._get_destination_location(),
                'picking_id': picking.id,
                'partner_id': line.contract_id.partner_id.id,
                'product_uom_qty': line.product_qty,
                'move_dest_id': False,
                'state': 'draft',
                'contract_return_line': line.id,
                'company_id': line.contract_id.company_id.id,
                'price_unit': 0,
                'picking_type_id': line.contract_id.picking_type_id.id,
                'group_id': line.contract_id.group_id.id,
                'procurement_id': False,
                'origin': line.contract_id.name,
                'route_ids': line.contract_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.contract_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':line.contract_id.picking_type_id.warehouse_id.id,
            }
            done += moves.create(template)
        return done
    
    
class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
    
    @api.multi
    def button_contract_return(self):
        contract_return = self.env['contract.return']
        for contract in self:
            total_value = 0
            total_payment = 0
            total_rate = 0
            for value in contract.request_payment_ids:
                for rate in value.rate_ids:
                    total_rate = total_rate + rate.provisional_rate
                for payment in value.request_payment_ids:
                    total_payment = total_payment + payment.amount
                total_value = total_rate + total_payment
            vals = {
                'partner_id': contract.partner_id.id,
                'warehouse_id':contract.warehouse_id.id or '',
#                 'contract_return_line': contract.contract_line.id,
                'npe_contract':contract.id or '',
                'amount_total':total_value
                    }
            if contract.npe_ids:
                raise UserError(_("The order has been confirmed."))
            else:
                new_id = contract_return.create(vals)
                for line in contract.contract_line:
                    vals={
                          'product_id':line.product_id.id or '',
                          'name':line.name or '',
                          'product_qty':line.product_qty or '',
                          'product_uom':line.product_uom.id or '',
                          'tax_id':'',
                          'price_subtotal':line.price_subtotal or '',
                          'contract_id':new_id.id,
                          }
                    contract_return = self.env['contract.return.line'].create(vals)
        if new_id:
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('ned_contract.action_contract_return')
            form_view_id = imd.xmlid_to_res_id('ned_contract.view_contract_return_form')
            result = {
                      'name': action.name,
                      'help': action.help,
                      'type': action.type,
                      'views': [[form_view_id, 'form']],
                      'target': action.target,
                      'context': action.context,
                      'res_model': action.res_model,
                      'res_id': new_id.ids[0],
                      'views' : [(form_view_id, 'form')],
                      }
        return result
    
class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"
    
    contract_return_id = fields.Many2one('contract.return',string="Contract Return")

    @api.model
    def default_get(self, fields): 
        rec = super(AccountPayment, self).default_get(fields)
        active_id = self._context.get('active_id')
        if self._context.get('active_model') and self._context.get('active_model') == 'contract.return':
            contract_id = self.env[self._context.get('active_model')].browse(active_id)
            rec['communication'] = contract_id.name
            rec['currency_id'] = contract_id.currency_id.id
            rec['payment_type'] = 'inbound'
            rec['partner_type'] = 'supplier'
            rec['partner_id'] = contract_id.partner_id.id
            rec['contract_return_id'] = contract_id.id
            rec['communication'] = u'Nhận tiền thanh toán theo ' + contract_id.name
            rec['extend_payment'] = 'payment'
            rec['amount'] = contract_id.total_remain
                  
        return rec
    
    
#     @api.constrains('amount')
#     def check_total_amount(self):
#         active_id = self._context.get('active_id')
#         contract_id = self.env[self._context.get('active_model')].browse(active_id)
#         amount_payment = self.amount
# #         if amount_payment > contract_id.total_remain:
# #             raise ValidationError(_('Amount payment bigger than amount remain.'))
#         if amount_payment - contract_id.total_remain == 0:
#             contract_id.write({'state': 'done'})
    
    
    
        