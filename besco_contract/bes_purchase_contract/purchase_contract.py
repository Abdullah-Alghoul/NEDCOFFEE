# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"
    
    
    @api.model
    def default_get(self, fields): 
        rec = super(AccountPayment, self).default_get(fields)
        active_id = self._context.get('active_id')
        if self._context.get('active_model') and self._context.get('active_model') == 'request.payment':
            request = self.env['request.payment'].browse(active_id)
            rec['communication'] = request.name
            rec['currency_id'] = request.purchase_contract_id.currency_id.id
            rec['payment_type'] = 'outbound'
            rec['partner_id'] = request.purchase_contract_id.partner_id.id
            rec['purchase_contract_id'] = request.purchase_contract_id.id
            rec['request_payment_id'] =  active_id
            if request.purchase_contract_id.type !='purchase':
                rec['extend_payment'] = 'advance'
                rec['communication'] = 'Advance - ' + request.purchase_contract_id.name
            else:
                rec['extend_payment'] = 'payment'
                rec['communication'] = 'Payment - ' + request.purchase_contract_id.name
        
        if self._context.get('active_model') and self._context.get('active_model') == 'purchase.contract':
            contract_id = self.env[self._context.get('active_model')].browse(active_id)
            rec['communication'] = contract_id.name
            rec['currency_id'] = contract_id.currency_id.id
            rec['payment_type'] = 'outbound'
            rec['partner_id'] = contract_id.partner_id.id
            rec['purchase_contract_id'] = contract_id.id
            rec['communication'] = 'Payment - ' + contract_id.name
            rec['extend_payment'] = 'payment'
        return rec
    
    purchase_contract_id = fields.Many2one('purchase.contract', string='Purchase Contract',
       readonly=True, states={'draft': [('readonly', False)]}, required=False,)
    
    allocated = fields.Boolean(string = 'Allocated',default=False)

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    purchase_contract_id = fields.Many2one('purchase.contract', string='Purchase Contract',
       readonly=True, states={'draft': [('readonly', False)]}, required=False,)

class NpeNvpRelation(models.Model):
    _name = "npe.nvp.relation"
    
    @api.depends('npe_contract_id','contract_id')
    def _total_deposit_amount(self):
        for relation in self:
            deposit_amount = 0.0
            if relation.npe_contract_id:
                for line in relation.npe_contract_id.request_payment_ids:
                    deposit_amount += line.total_payment
                relation.deposit_amount = deposit_amount
    
    @api.depends('npe_contract_id','contract_id')
    def _origin_qty(self):
        for relation in self:
            origin_qty = 0.0
            if relation.npe_contract_id:
                for line in relation.npe_contract_id.contract_line:
                    origin_qty +=line.product_qty
                relation.origin_qty = origin_qty
    
    deposit_amount = fields.Float(compute='_total_deposit_amount',string = 'Deposit Amount')
    npe_contract_id = fields.Many2one('purchase.contract', string='NPE')
    contract_id = fields.Many2one('purchase.contract', string='NVP')
    product_qty = fields.Float('Fixed Qty',digits=(16, 0))
    origin_qty = fields.Float(compute='_origin_qty',string = 'Original Qty',digits=(16, 0))
    type = fields.Selection([('fixed', 'Fixed'), ('temporary', 'Temporary')], string='Type',
                     readonly=True,store= True)
    
    
class PurchaseContract(models.Model):
    _name = "purchase.contract"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date_order desc, id desc'
    
    @api.multi
    @api.onchange('date_order')
    def onchange_date_order(self):
        deal_line = False
        if not self.date_order:
            return True
        crop_ids = self.env['ned.crop'].search([('start_date', '<=', self.date_order),('to_date', '>=', self.date_order)], limit=1)
        sql ='''
            SELECT '%s'::Date +5 as deal_line
        '''%(self.date_order)
        self.env.cr.execute(sql)
        for line in self.env.cr.dictfetchall():
            deal_line = line['deal_line']
        self.update({
            'crop_id': crop_ids,
            'deadline_date':deal_line
        })
    
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env.user.company_id.second_currency_id.id
        return currency_ids
    
    @api.multi
    def button_dummy(self):
        return True
    
    @api.depends('contract_line.price_total')
    def _amount_all(self):
        for contract in self:
            amount_untaxed = amount_tax = 0.0
            for line in contract.contract_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            contract.update({
                'amount_untaxed': contract.currency_id.round(amount_untaxed),
                'amount_tax': contract.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
            
    @api.depends('picking_ids')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.picking_ids:
                moves = line.move_lines.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)
            
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.One2many('stock.picking', 'purchase_contract_id' , 'Picking Line', readonly=True)
            
    name = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('purchase.contract'))
    company_representative = fields.Many2one("res.partner", string="Company Representative", readonly=True, states={'draft': [('readonly', False)]})
    
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current Purchase order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Delivery address for current Purchase order.")

    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
      
    partner_id = fields.Many2one('res.partner', string='Supplier', readonly=True, states={'draft': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')
    supplier_representative = fields.Many2one('res.partner', string='Supplier Representative', readonly=True, states={'draft': [('readonly', False)]}, index=True, track_visibility='always')

    validity_date = fields.Date(string='Validate Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    expiration_date = fields.Date(string='Expiration Date', readonly=True, states={'draft': [('readonly', False)]})
    date_order = fields.Date(string='Date Contract', readonly=True, copy=False, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    deadline_date = fields.Date(string='Deadline Date', readonly=False, copy=False )
    price_estimation_date = fields.Date(string='Price Estimation Date', readonly=True, states={'draft': [('readonly', False)]})
    
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    exchange_rate = fields.Float(string="Exchange Rate", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=1.0)
    
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    acc_number = fields.Char(string='Account Number', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    payment_description = fields.Text('Payment Term Description', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=False, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    transportation_charges = fields.Selection([('none', 'None'), ('included', 'Included'), ('exclude', 'Exclude')], string='Transportation Charges', readonly=True, states={'draft': [('readonly', False)]}, copy=False, index=True, default='none')
    delivery_from = fields.Date(string='From Date', readonly=True, copy=False, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    delivery_to = fields.Date(string='To Date', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    
    contract_line = fields.One2many('purchase.contract.line', 'contract_id', string='Contract Lines', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    type = fields.Selection([('consign', 'Consignment Agreement'), ('purchase', 'Purchase Contract')], string="Type", required=True, default="consign")
    note = fields.Text('Terms and conditions')
    origin = fields.Char(string='Source Document')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    date_done = fields.Date('Date Done', readonly=True, select=True, copy=False)
    
    check_qty = fields.Boolean(string='Check Qty', readonly=True, states={'draft': [('readonly', False)]})
    check_price_unit = fields.Boolean(string='Check Unit Price', readonly=True, states={'draft': [('readonly', False)]})
    
    npe_contract_id = fields.Many2one('purchase.contract', string='NPE', readonly=True, states={'draft': [('readonly', False)]})
    nvp_ids = fields.One2many('npe.nvp.relation','contract_id', string='Nvp', readonly=True, states={'draft': [('readonly', False)]})
    npe_ids = fields.One2many('npe.nvp.relation','npe_contract_id', string='Npe', readonly=True, states={'draft': [('readonly', False)]})
    
    payment_ids = fields.One2many('account.payment','purchase_contract_id', string='Payment', )
    group_id = fields.Many2one('procurement.group', string="Procurement Group")
    
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.One2many('stock.picking', 'purchase_contract_id' , 'Picking Line', readonly=True)
    
    product_id = fields.Many2one(related='contract_line.product_id',  string='Product',store =True)
    
    
    
    
    
    @api.depends('contract_line.product_qty', 'contract_line')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.contract_line:
                total_qty += line.product_qty                
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Total Qty',store = True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            if vals.get('type', 'purchase') == 'purchase':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.contract') or 'New'
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('npe.contract') or 'New'
        
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
        result = super(PurchaseContract, self).create(vals)
        return result
    
    @api.multi
    def unlink(self):
        for contract in self:
            if contract.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel contract.'))
            picking_ids = self.env['stock.picking'].search([('purchase_contract_id', '=', contract.id), ('state', 'not in', ('draft', 'cancel'))])
            if picking_ids:
                raise UserError(_('You can only delete draft contract!'))
        return super(PurchaseContract, self).unlink()
    
    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]
        result['context'] = {}
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'payment_term_id': False,
                'partner_invoice_id': False,
                'partner_shipping_id': False,
            })
            return
        
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }
        
        self.update(values)
    
    @api.multi
    @api.onchange('company_id')
    def company_id_domain(self):
        if not self.company_id:
            return {'domain': {'company_representative': []}}
        domain = {'company_representative': [('parent_id', '=', self.company_id.partner_id.id)]}
        return {'domain':domain}
    
    @api.multi
    def button_draft(self):
        self.write({'state': 'draft'})
    
    @api.multi
    def _get_destination_location(self):
        return self.picking_type_id.default_location_dest_id.id
 
    @api.multi
    def button_approve(self):
        for contract in self:
            self._account_entry_move()
            if not contract.contract_line:
                raise UserError(_('You cannot approve a purchase contract without any purchase contract line.'))
            
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def button_done(self):
        self.write({'state': 'done', 'date_done': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def button_cancel(self):
        picking = self.env['stock.picking']
        
        if self.picking_ids:
            for picking in self.picking_ids:
                if picking.state in ('assigned', 'done'):
                    raise UserError(_('Unable to cancel contract %s as some receptions have already been done.\n\t You must first cancel related receptions.') % (self.name))
                    
        self.env.cr.execute('''
            DELETE FROM stock_move WHERE picking_id in (SELECT id FROM stock_picking WHERE purchase_contract_id = %(contract_id)s);
            DELETE FROM stock_picking WHERE purchase_contract_id = %(contract_id)s;''' % ({'contract_id': self.id}))
        self.write({'state': 'cancel'})
    
class PurchaseContractLine(models.Model):
    _name = "purchase.contract.line"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
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
    
    contract_id = fields.Many2one('purchase.contract', string='Contract Reference', ondelete='cascade', index=True, copy=False)
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
        for line in self:
            order = line.contract_id
            price_unit = line.price_unit
            if line.tax_id:
                price_unit = line.tax_id.compute_all(price_unit, currency=line.contract_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)
            
            vals = {
                    'picking_id': picking.id,
                    'name': line.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'product_uom_qty': line.product_qty or 0.0,
                    'price_unit': price_unit,
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
        

    
    
    
    
    
    
