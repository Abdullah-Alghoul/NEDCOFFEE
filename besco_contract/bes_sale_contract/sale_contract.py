# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from lxml import etree
import time
from openerp import SUPERUSER_ID

class SaleContract(models.Model):
    _name = "sale.contract"
    _order = 'create_date desc, id desc'
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
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
    def _compute_pickings(self):
        for contract in self:
            pickings = self.env['stock.picking'] 
            for line in contract.picking_ids:
                moves = line.move_lines.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            contract.picking_ids = pickings
            contract.picking_count = len(pickings)
            
    @api.depends('delivery_ids')
    def _compute_deliverys(self):
        for contract in self:
            deliverys = self.env['delivery.order']
            for line in contract.delivery_ids: 
                orders = line.delivery_order_ids.filtered(lambda r: r.state != 'cancel')
                deliverys |= orders.mapped('delivery_id')
            contract.delivery_ids = deliverys
            contract.delivery_count = len(deliverys)
            
    @api.depends('invoice_ids')  
    def _compute_invoices(self):
        for contract in self:
            invoices = self.env['account.invoice']
            for line in contract.invoice_ids: 
                invoices = (line.filtered(lambda r: r.state != 'cancel'))
            contract.invoice_ids = invoices
            contract.invoice_count = len(invoices)
    
    name = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('sale.contract'))
    company_representative = fields.Many2one("res.partner", string="Company Representative", readonly=True, states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    picking_policy = fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
        string='Shipping Policy', required=True, readonly=True, default='direct', states={'draft': [('readonly', False)]})

    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'),('invoice','Invoice'), ('done', 'Done'), ('cancel', 'Cancelled')],
             string='Status', readonly=True, copy=False, index=True, default='draft')
    type = fields.Selection([('local', 'Local'), ('export', 'Export')], string='Type', required=True)
      
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)]}, required=False, change_default=True, index=True, track_visibility='always')
    customer_representative = fields.Many2one('res.partner', string='Customer Representative', readonly=True, states={'draft': [('readonly', False)]}, index=True, track_visibility='always')
    
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current Purchase order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=False, states={'draft': [('readonly', False)]})
    
    date = fields.Date(string='Date', readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    validity_date = fields.Date(string='Validity Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    expiration_date = fields.Date(string='Expiration Date', readonly=True, states={'draft': [('readonly', False)]})
    
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=False, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    exchange_rate = fields.Float(string="Exchange Rate", readonly=True, required=False, states={'draft': [('readonly', False)]}, default=1.0)
    
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    acc_number = fields.Char(string='Account Number', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    
    contract_line = fields.One2many('sale.contract.line', 'contract_id', string='Contract Lines', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
  
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

    dispatch_mode = fields.Selection([('air', 'Air'), ('rail', 'Rail'), ('road', 'Road'), ('sea', 'Sea')], string='Dispatch Mode', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    port_of_loading = fields.Many2one('delivery.place', string='Port Of Loading', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    port_of_discharge = fields.Many2one('delivery.place', string='Port of Destination', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    container_status = fields.Selection([('fcl/fcl', 'FCL/FCL'), ('lcl/fcl', 'LCL/FCL'), ('lcl/lcl', 'LCL/LCL')], string='Container Status', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    weights = fields.Selection([('DW', 'Net Delivered Weights'), ('NLW', 'Net Landed Weights'),
                                ('NSW', 'Net Shipped Weights'), ('RW', 'Re Weights')],  string='Weights', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    
    deadline = fields.Date(string='Deadline', required=False, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    transportation_charges = fields.Selection([('none', 'None'), ('included', 'Included'), ('exclude', 'Exclude')], string='Transportation Charges', readonly=True, states={'draft': [('readonly', False)]}, copy=False, index=True, default='none')
    delivery_tolerance = fields.Float(string="Delivery Tolerance", default=5.0, readonly=True , states={'draft': [('readonly', False)]})
    
#     picking_count = fields.Integer(compute='_compute_pickings', string='Receptions', default=0)
#     picking_ids = fields.One2many('stock.picking', 'sale_contract_id', string='GDN List', readonly=True, copy=False)
    
    delivery_count = fields.Integer(compute='_compute_deliverys', string='Receptions', default=0)
    delivery_ids = fields.One2many('delivery.order', 'contract_id', string='DO List', readonly=True, copy=False)
    
    invoice_count = fields.Integer(compute='_compute_invoices', string='Receptions', default=0)
    invoice_ids = fields.One2many('account.invoice', 'sale_contract_id', string='Invoiced List', readonly=True, copy=False)
    shipping_id = fields.Many2one('shipping.instruction', string='SI No.', ondelete='cascade'),
    scontract_id = fields.Many2one('s.contract', string='SNo.', ondelete='cascade' , readonly=True , states={'draft': [('readonly', False)]})
#     @api.model
#     def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
#         context = self._context
#         res = super(SaleContract, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
#         
#         if view_type in ['tree', 'form']:
#             doc = etree.XML(res['arch'])
#             type = context.get('default_type', False)
#             if type == 'export':
#                 for node in doc.xpath("//field[@name='scontract_id']"):
#                     node.set('invisible', '1')
#                 for node in doc.xpath("//label[@for='scontract_id']"):
#                     node.set('string', 'SI No.')
#                 for node in doc.xpath("//field[@name='shipping_id']"):
#                     node.set('required', '1')
#             if type == 'local':
#                 for node in doc.xpath("//field[@name='shipping_id']"):
#                     node.set('invisible', '1')
#                 for node in doc.xpath("//field[@name='scontract_id']"):
#                     node.set('required', '1')
#                     
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res
    @api.model
    def create(self, vals): 
        if vals.get('name', False):
            if vals.get('name', False) == 'New':
                if vals.get('type', False) and vals.get('type', False) == 'local':
                    vals['name'] = self.env['ir.sequence'].next_by_code('sale.nls')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('sale.nvs')
            else:
                name = vals.get('name', False)
                contract_ids = self.search([('name', '=', name)])
                if len(contract_ids) >= 1:
                    raise UserError(_("Contract (%s) was exist.") % (name))
            
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
            
        if vals.get('port_of_discharge', False) != False and vals.get('port_of_loading', False) != False:
            if vals.get('port_of_discharge', False) == vals.get('port_of_loading', False):
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        result = super(SaleContract, self).create(vals)
        return result
    
#     @api.multi
#     def write(self, values):    
#         if values.get('port_of_discharge', False) and values.get('port_of_loading', False):
#             if values.get('port_of_discharge', False) == values.get('port_of_loading', False):
#                 raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
#         elif values.get('port_of_discharge', False):
#             if values.get('port_of_discharge', False) == self.port_of_loading.id:
#                 raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
#         elif values.get('port_of_loading', False):
#             if values.get('port_of_loading', False) == self.port_of_discharge.id:
#                 raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
#         result = super(SaleContract, self).write(values)
#         return result
    
    @api.multi
    def unlink(self):
        if self.state not in ('draft', 'cancel'):
            raise UserError(_('You can only delete draft or cancel Contract.'))
        return super(SaleContract, self).unlink()
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'payment_term_id': False,
                'partner_invoice_id': False,
                'partner_shipping_id': False,
                'currency_id': False,
            })
            return
        addr = self.partner_id.address_get(['delivery', 'invoice'])
        values = {
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
            'currency_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id or False,
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
        if self.state == 'done':
            raise UserError(_('Unable to cancel Contract %s as some receptions have already been done.\n\t You must first cancel related receptions.') % (self.name))
        
#         if self.invoice_ids:
#             raise UserError(_('Unable to cancel Contract %s as some receptions have already been done.\n\t You must first delete related invoices.') % (self.name))
#         
#         if self.picking_ids:
#             for picking in self.picking_ids:
#                 if picking.state == 'done':
#                     raise UserError(_('Unable to cancel Contract %s as some receptions have already been done.\n\t You must first cancel related receptions.') % (self.name))
        
#         if self.delivery_ids:
#             for delivery in self.delivery_ids:
#                 if delivery.state == 'done':
#                     raise UserError(_('Unable to cancel Contract %s as some receptions have already been done.\n\t You must first cancel related receptions.') % (self.name))

#         self.env.cr.execute('''DELETE FROM stock_pack_operation WHERE picking_id in (SELECT id FROM stock_picking WHERE sale_contract_id = %(contract_id)s);
#             DELETE FROM stock_move WHERE picking_id in (SELECT id FROM stock_picking WHERE sale_contract_id = %(contract_id)s);
#             DELETE FROM stock_picking WHERE sale_contract_id = %(contract_id)s;
#             DELETE FROM delivery_order_line WHERE delivery_id in (SELECT id FROM delivery_order WHERE contract_id = %(contract_id)s);
#             DELETE FROM delivery_order WHERE contract_id = %(contract_id)s;''' % ({'contract_id': self.id}))
            
        self.write({'state': 'draft'})
    
    @api.multi
    def button_approve(self):
        for contract in self:
            if not contract.contract_line:
                raise UserError(_('You cannot approve a Contract without any Contract Line.'))
#             if not self.port_of_discharge: 
#                 raise ValidationError("Port Of Loading missing information.")
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def contract_total_qty(self):
        total_qty = 0.0
        for line in self.contract_line:
            total_qty += line.product_qty
        return total_qty
    
    @api.multi
    def button_done(self):
        self.write({'state': 'done', 'date_done': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['context'] = {}
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    def create_do(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('bes_sale_contract.action_view_wizard_do')
        form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizard_do')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
            }
        return result
    
    @api.multi
    def action_view_do(self):
        action = self.env.ref('bes_sale_contract.action_delivery_order')
        result = action.read()[0]
        pick_ids = sum([order.delivery_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('bes_sale_contract.view_delivery_order_form', False)
            result['context'] = {}
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    def action_view_invoice(self):
        invoice_ids = self.mapped('invoice_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree1')
        list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.invoice_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
        elif len(invoice_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    @api.multi
    def create_invoice(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('bes_sale_contract.action_wizard_invoice')
        form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizard_invoice')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
            }
        return result
    
class SaleContractLine(models.Model):
    _name = "sale.contract.line"
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
            conversion = line.conversion or 1
            price = line.price_unit / conversion
            taxes = line.tax_id.compute_all(price, line.contract_id.currency_id, line.product_qty, product=line.product_id, partner=line.contract_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
    
    contract_id = fields.Many2one('sale.contract', string='Contract Reference', ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    company_id = fields.Many2one(related='contract_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', store=True, string='Customer')
    
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')],
         related='contract_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    currency_id = fields.Many2one(related='contract_id.currency_id', store=True, string='Currency', readonly=True)
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, required=True)
    product_qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='UoM', required=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)
    conversion = fields.Float('Conversion', required=False,  default=1000,digits=(12, 0))

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
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    sale_contract_id = fields.Many2one('sale.contract', string='Sale Contract',  ondelete='cascade')
    delivery_id = fields.Many2one('delivery.order', string='Delivery Order')

    
#     @api.multi
#     def action_cancel(self):
#         self.ensure_one()
#         if self.delivery_id:
#             raise UserError(_('DO %s need to cancel before.')%(self.delivery_id.name))
#         return super(StockPicking, self).action_cancel()
    
    @api.multi  
    def action_wizrad_out_stock_wti(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('bes_sale_contract.action_wizrad_out_stock_wti')
        form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizrad_out_stock_wti')
        
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
            }
        return result
    
    @api.multi
    def do_new_transfer(self):
        self.ensure_one()
        if self.delivery_id:
            self.delivery_id.button_done()
        return super(StockPicking, self).do_new_transfer()
    
class StockMove(models.Model):
    _inherit = "stock.move"

    out_stock_wti = fields.Float(string="Out stock WTI", default=1.0)
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    sale_contract_id = fields.Many2one('sale.contract', string='Sale Contract', readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')
