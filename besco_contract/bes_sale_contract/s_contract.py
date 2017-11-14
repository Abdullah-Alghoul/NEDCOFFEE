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
from openerp import SUPERUSER_ID
import time

class SContract(models.Model):
    _name = "s.contract"
    _order = 'id desc'
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id 
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _default_company_id(self):
        company_ids = self.env['res.users'].browse(self.env.uid).company_id.id
        return company_ids
    
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

    @api.depends('shipping_ids')
    def _compute_shippings(self):
        for contract in self:
            shippings = self.env['shipping.instruction'] 
            for line in contract.shipping_ids:
                lines = line.shipping_ids.filtered(lambda r: r.state != 'cancel')
                shippings |= lines.mapped('shipping_id')
            contract.shipping_ids = shippings
            contract.shipping_count = len(shippings)
            
    @api.depends('contract_ids')
    def _compute_contracts(self):
        for contract in self:
            contracts = self.env['sale.contract'] 
            for line in contract.contract_ids:
                lines = line.contract_line.filtered(lambda r: r.state != 'cancel')
                contracts |= lines.mapped('contract_id')
            contract.contract_ids = contracts
            contract.contract_count = len(contracts)
    
    name = fields.Char(string='Sno', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, readonly=True, default=_default_company_id)
    company_representative = fields.Many2one("res.partner", string="Company Representative", readonly=True, states={'draft': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, readonly=True, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    picking_policy = fields.Selection([('direct', 'Deliver each product when available'), ('one', 'Deliver all products at once')],
        string='Shipping Policy', required=False, readonly=True, default='direct', states={'draft': [('readonly', False)]})

    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')],
             string='Status', readonly=True, copy=False, index=True, default='draft')
    type = fields.Selection([('s-local', 'S-Local'), ('s-export', 'S-Export'), ('local', 'Local'), ('export', 'Export')], string='Type', required=True, readonly=True, index=True, default='local')
      
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')
    customer_representative = fields.Many2one('res.partner', string='Customer Representative', readonly=True, states={'draft': [('readonly', False)]}, index=True, track_visibility='always')
    
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Invoice address for current Purchase order.")
    partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', readonly=True, required=True, states={'draft': [('readonly', False)]})
    
    date = fields.Date(string='Sdate', readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    validity_date = fields.Date(string='Validity Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    expiration_date = fields.Date(string='Expiration Date', readonly=True, states={'draft': [('readonly', False)]})
    
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    exchange_rate = fields.Float(string="Exchange Rate", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=1.0)
    
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    acc_number = fields.Char(string='Account Number', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    
    contract_line = fields.One2many('s.contract.line', 'contract_id', string='Contract Lines', readonly=True, states={'draft': [('readonly', False)]}, copy=True)
  
    note = fields.Text('Terms and conditions')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    date_done = fields.Date('Date Done', readonly=True, select=True, copy=False)
    # S Contract
    trader = fields.Char(string='Trader', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    dispatch_mode = fields.Selection([('air', 'Air'), ('rail', 'Rail'), ('road', 'Road'), ('sea', 'Sea')], string='Dispatch Mode', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    port_of_loading = fields.Many2one('delivery.place', string='Port Of Loading', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    port_of_discharge = fields.Many2one('delivery.place', string='Port of Discharge', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    container_status = fields.Selection([('fcl/fcl', 'FCL/FCL'), ('lcl/fcl', 'LCL/FCL'), ('lcl/lcl', 'LCL/LCL')], string='Container Status', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    weights = fields.Selection([('DW', 'Delivered Weights'), ('NLW', 'Net Landed Weights'),
                                ('NSW', 'Net Shipped Weights'), ('RW', 'Re Weights')], 
                               string='Weigh Condition', readonly=True, states={'draft': [('readonly', False)]}, index=True)
    
    deadline = fields.Date(string='Deadline', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)

    transportation_charges = fields.Selection([('none', 'None'), ('included', 'Included'), ('exclude', 'Exclude')], string='Transportation Charges', readonly=True, states={'draft': [('readonly', False)]}, copy=False, index=True, default='none')
    delivery_tolerance = fields.Float(string="Delivery Tolerance", default=5.0, readonly=True , states={'draft': [('readonly', False)]})
    
    shipping_count = fields.Integer(compute='_compute_shippings', string='Receptions', default=0)
    shipping_ids = fields.One2many('shipping.instruction', 'contract_id', string='Shipping Instruction List', readonly=True)
    
    contract_count = fields.Integer(compute='_compute_contracts', string='Receptions', default=0)
    contract_ids = fields.One2many('sale.contract', 'scontract_id', string='NLS', readonly=True, copy=True)
    
    qty_condition = fields.Selection([('pss','PSS'), ('none', 'PCS')], string="Quality Condition", default='none')
    marking = fields.Text(string="Shipping Marks")
    
    
    
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.contract_line:
                total_qty += line.product_qty
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Total Qty')
    
    product_id = fields.Many2one(related='contract_line.product_id',  string='Product')
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        res = super(SContract, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        if view_type in ['tree', 'form']:
            doc = etree.XML(res['arch'])
            type = context.get('default_type', False)
            if type == 'local':
                for node in doc.xpath("//button[@name='create_si']"):
                    node.set('invisible', "1")
                for node in doc.xpath("//button[@name='action_view_shipping']"):
                    node.set('invisible', "1")
                for node in doc.xpath("//page[@name='shipping']"):
                    node.set('invisible', "1")
            if type == 'export':
                for node in doc.xpath("//button[@name='create_nls']"):
                    node.set('invisible', "1")
                for node in doc.xpath("//button[@name='action_view_contract_nls']"):
                    node.set('invisible', "1")
                for node in doc.xpath("//page[@name='nls']"):
                    node.set('invisible', "1")
                    
            xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
    @api.model
    def create(self, vals):
        if vals.get('name', False):
            name = vals.get('name', False)
            contract_ids = self.search([('name', '=', name)])
            if len(contract_ids) >= 1:
                raise UserError(_("S Contract (%s) was exist.") % (name))
            
        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            addr = partner.address_get(['delivery', 'invoice'])
            vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
            vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
        
        if vals.get('port_of_discharge', False) != False and vals.get('port_of_loading', False) != False:
            if vals.get('port_of_discharge', False) == vals.get('port_of_loading', False):
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        result = super(SContract, self).create(vals)
        return result
    
    @api.multi
    def write(self, values):    
        if values.get('port_of_discharge', False) and values.get('port_of_loading', False):
            if values.get('port_of_discharge', False) == values.get('port_of_loading', False):
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        elif values.get('port_of_discharge', False):
            if values.get('port_of_discharge', False) == self.port_of_loading.id:
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        elif values.get('port_of_loading', False):
            if values.get('port_of_loading', False) == self.port_of_discharge.id:
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        result = super(SContract, self).write(values)
        return result
    
    @api.multi
    def unlink(self):
        for line in self:
            if line.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel contract.'))
        return super(SContract, self).unlink()
    
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
        self.write({'state': 'draft', 'create_date': self.env.uid, 'create_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def button_cancel(self):
        if self.state == 'done':
            raise UserError(_('Unable to cancel S Contract %s') % (self.name))
        if self.state == 'approved':
            if self.type == 'export':
                if self.shipping_ids:
                    for shipping in self.shipping_ids:
                        if shipping.state == 'done':
                            raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related SI.') % (self.name))
                    if shipping.contract_ids:
                        for contract in shipping.contract_ids:
                            if contract.state == 'done':
                                raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related NVS.') % (self.name))
                            if contract.picking_ids:
                                for i in line.picking_ids:
                                    if i.state == 'done':
                                        raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related GDN.') % (self.name))
                            if contract.delivery_ids:
                                for j in line.delivery_ids:
                                    if i.state == 'done':
                                        raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related DO.') % (self.name))
                    self.env.cr.execute('''
                    DELETE FROM stock_pack_operation WHERE picking_id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id
                         join shipping_instruction si on si.id = sc.shipping_id WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM stock_move WHERE picking_id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id
                         join shipping_instruction si on si.id = sc.shipping_id WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM stock_picking WHERE id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id
                         join shipping_instruction si on si.id = sc.shipping_id WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM delivery_order_line WHERE delivery_id in (SELECT de.id FROM delivery_order de join sale_contract sc on sc.id = de.contract_id 
                        join shipping_instruction si on si.id = sc.shipping_id WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM delivery_order WHERE id in (SELECT de.id FROM delivery_order de join sale_contract sc on sc.id = de.contract_id 
                        join shipping_instruction si on si.id = sc.shipping_id  WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM sale_contract_line WHERE contract_id in (SELECT sc.id FROM sale_contract sc join shipping_instruction si on si.id = sc.shipping_id  WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM sale_contract WHERE id in (SELECT sc.id FROM sale_contract sc join shipping_instruction si on si.id = sc.shipping_id  WHERE si.contract_id = %(contract_id)s);
                    DELETE FROM shipping_instruction_line WHERE shipping_id in (SELECT id FROM shipping_instruction WHERE contract_id = %(contract_id)s);
                    DELETE FROM shipping_instruction WHERE id in (SELECT id FROM shipping_instruction WHERE contract_id = %(contract_id)s); ''' % ({'contract_id': self.id}))
            else:
                if self.contract_ids:
                    for line in self.contract_ids:
                        if line.state == 'done':
                            raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related NLS.') % (self.name))
                        if line.state == 'approved':
                            if line.picking_ids:
                                for i in line.picking_ids:
                                    if i.state == 'done':
                                        raise UserError(_('Unable to cancel S Contract %s as some receptions have already been done.\n\t You must first cancel related GDN.') % (self.name))
                    self.env.cr.execute('''
                        DELETE FROM stock_pack_operation WHERE picking_id in (SELECT sp.id FROM sale_contract sc join stock_picking sp on sp.sale_contract_id = sc.id WHERE sc.scontract_id = %(contract_id)s);
                        DELETE FROM stock_move WHERE picking_id in (SELECT sp.id FROM sale_contract sc join stock_picking sp on sp.sale_contract_id = sc.id WHERE sc.scontract_id = %(contract_id)s);
                        DELETE FROM stock_picking WHERE sale_contract_id in (SELECT id FROM sale_contract WHERE scontract_id = %(contract_id)s);
                        DELETE FROM sale_contract_line WHERE contract_id in (SELECT id FROM sale_contract WHERE scontract_id = %(contract_id)s);
                        DELETE FROM sale_contract WHERE id in (SELECT id FROM sale_contract WHERE scontract_id = %(contract_id)s);''' % ({'contract_id': self.id}))
        self.write({'state': 'cancel'})
    
    @api.multi
    def button_approve(self):
        for contract in self:
            if not contract.contract_line:
                raise UserError(_('You cannot approve a S Contract without any S Contract Line.'))
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def button_done(self):
        if self.type == 'export' and not self.shipping_ids:
            raise UserError(_('You cannot done a S Contract without any SI.'))
        elif self.type == 'local' and not self.contract_ids:
            raise UserError(_('You cannot done a S Contract without any NLS.'))
        self.write({'state': 'done', 'date_done': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def check_qty(self):
        product_qty = new_qty = 0.0
        for line in self.contract_line:
            if self.type == 'export':
                for shipping in self.shipping_ids:
                    if shipping.state != 'cancel':
                        if line.product_id == shipping.product_id:
                            product_qty += line.product_qty
                new_qty = shipping.product_qty - product_qty
    
    @api.multi
    def create_si(self):
        if self.type == 'export':
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_view_wizard_si')
            form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizard_si')
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
    def action_view_shipping(self):
        action = self.env.ref('bes_sale_contract.action_shipping_instruction')
        result = action.read()[0]
        result['context'] = {}
        ship_ids = sum([order.shipping_ids.ids for order in self], [])
        if len(ship_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, ship_ids)) + "]), ('state','!=','cancel')]"
        elif len(ship_ids) == 1:
            res = self.env.ref('bes_sale_contract.view_shipping_instruction_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = ship_ids and ship_ids[0] or False
        return result
    
    @api.multi
    def create_nls(self):
        if self.type == 'local':
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_sale_contract.action_view_wizard_nls')
            form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizard_nls')
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'context': action.context,
                'views': [[form_view_id, 'form']],
                'target': action.target,
                'res_model': action.res_model,
                }
        return result
    
    @api.multi
    def action_view_contract_nls(self):
        action = self.env.ref('bes_sale_contract.action_sale_contract_local')
        result = action.read()[0]
        contract_ids = sum([order.contract_ids.ids for order in self], [])
        if len(contract_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, contract_ids)) + "]), ('state','!=','cancel')]"
        elif len(contract_ids) == 1:
            res = self.env.ref('bes_sale_contract.view_sale_contract_form', False)
            result['context'] = action.context
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = contract_ids and contract_ids[0] or False
        return result
    
class SContractLine(models.Model):
    _name = "s.contract.line"
    
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
    
    name = fields.Text(string='Description', required=True)
    contract_id = fields.Many2one('s.contract', string='Contract Reference', ondelete='cascade', index=True, copy=False)
    sequence = fields.Integer(string='Sequence', default=10)

    
    company_id = fields.Many2one(related='contract_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one(related='contract_id.partner_id', store=True, string='Customer')
    
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'),
                                        ('done', 'Done'), ('cancel', 'Cancelled')],
          related='contract_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    currency_id = fields.Many2one(related='contract_id.currency_id', store=True, string='Currency', readonly=True)
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, required=True)
    product_qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='Uom', required=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes',)
    
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

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
    
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    si_id = fields.Many2one('shipping.instruction', string='SI Contract', readonly=True, states={'draft': [('readonly', False)]}, ondelete='cascade')


class ShippingInstruction(models.Model):
    _name = "shipping.instruction"
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
            
    invoice_count = fields.Integer(compute='_compute_invoices', string='Receptions', default=0)
    invoice_ids = fields.One2many('account.invoice', 'si_id', string='Invoiced List', readonly=True, copy=False)
    
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
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _default_shipment_from(self):
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_id.partner_id.id
    
    @api.depends('contract_ids')
    def _compute_contracts(self):
        for ship in self:
            contracts = self.env['sale.contract'] 
            for line in ship.contract_ids:
                lines = line.contract_line.filtered(lambda r: r.state != 'cancel')
                contracts |= lines.mapped('contract_id')
            ship.contract_ids = contracts
            ship.contract_count = len(contracts)
    
    @api.depends('invoice_ids')
    def _compute_invoices(self):
        for contract in self:
            invoices = self.env['account.invoice']
            for line in contract.invoice_ids: 
                invoices = (line.filtered(lambda r: r.state != 'cancel'))
            contract.invoice_ids = invoices
            contract.invoice_count = len(invoices)
            
    @api.depends('shipping_ids')
    def _compute_line_qty(self):
        for ship in self:
            total_qty = 0.0
            for ship_line in ship.shipping_ids:
                total_qty += ship_line.product_qty 
            ship.total_line_qty = total_qty
    
    @api.depends('containers_ids')
    def _compute_cont_qty(self):
        for ship in self:
            total_qty = 0.0
            for containers in ship.containers_ids:
                total_qty += containers.product_qty 
            ship.total_cont_qty = total_qty
    
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    contract_id = fields.Many2one('s.contract', string='S Contract', ondelete='cascade', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    sequence = fields.Integer(string='Sequence', default=10, states={'draft': [('readonly', False)]})
    date = fields.Date(string='Date', readonly=True, index=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now,change_default=True,track_visibility='always')
    deadline = fields.Date(string='Deadline', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now,track_visibility='always')

    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('shipping.instruction'))
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    
    state = fields.Selection([('draft', 'New'),('waiting','Waiting Approve'),('approved', 'Approved'),('done', 'Done'),('cancel', 'Cancelled')],
             string='Status', readonly=True, copy=False, index=True, default='draft')
    
    note = fields.Text('Terms and conditions')
    origin = fields.Char(string='Source Document')

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)]}, required=False, change_default=True, index=True, track_visibility='always')
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_confirm = fields.Date('Date Confirmed', readonly=True, select=True, copy=False)
    user_confirm = fields.Many2one('res.users', string='User Confirm', readonly=True)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    
    shipping_line = fields.Many2one('res.partner', string='Shipping Line', copy=False, readonly=False,
            states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True, domain=[('transfer', '=', True)])
    forwarding_agent = fields.Char(string='Forwarding Agent', copy=False, readonly=True,
            states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True,size=128)
    
    
    port_of_loading = fields.Many2one('delivery.place', string='Port Of Loading', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    port_of_discharge = fields.Many2one('delivery.place', string='Port of Discharge', copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True)
    container_status = fields.Selection([('fcl/fcl', 'FCL/FCL'), ('lcl/fcl', 'LCL/FCL'), ('lcl/lcl', 'LCL/LCL')], string='Container Status', readonly=True, 
                                         states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, copy=False, index=True) 
                                        
    factory_etd = fields.Date('Factory ETD', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    push_off_etd = fields.Date('Push off ETD', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)

    booking_ref_no = fields.Char(string='Booking No.', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    booking_date = fields.Date('Booking date', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    reach_date = fields.Date('Reach Date', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    ico_permit_no = fields.Char(string='ICO No.', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    ico_permit_date = fields.Date('ICO Permit Date', readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    transaction = fields.Char(string='Transaction', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    vessel_flight_no = fields.Char(string='Vessel/Flight No.', copy=False, readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    
    shipping_ids = fields.One2many('shipping.instruction.line', 'shipping_id', string=' Shipping Instruction Lines', readonly=True,
                                                    copy=False, states={'draft': [('readonly', False)]})
    containers_ids = fields.One2many('bes.containers', 'shipping_id', string=' Container Details', readonly=True, copy=False,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]})
    
    incoterms_id = fields.Many2one('stock.incoterms',string='Terms',  readonly=True,  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]}, index=True)
    
    contract_count = fields.Integer(compute='_compute_contracts', string='Receptions', default=0)
    contract_ids = fields.One2many('sale.contract', 'shipping_id', string='Sale Contract', readonly=True, copy=False)
    
    
    type_of_stuffing = fields.Text(string="Type Of Stuffing",  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]})
    marking = fields.Text(string="Marking",  states={'draft': [('readonly', False)], 'waiting': [('readonly', False)]})
    
    total_line_qty = fields.Float(compute='_compute_line_qty', string='Qty', default=0)
    total_cont_qty = fields.Float(compute='_compute_cont_qty', string='Total Qty', default=0)
    product_id = fields.Many2one(related='shipping_ids.product_id',  string='Product')
    
    @api.model
    def create(self, vals):
#         if vals.get('name', 'New'):
#             if vals.get('contract_id', False):
#                 scontract_id = vals.get('contract_id', False)
#                 scontract = self.env['s.contract'].browse(scontract_id)
#                 sql='''
#                     SELECT count(id) number FROM Shipping_Instruction WHERE contract_id = %s
#                 '''%(vals['contract_id'])
#                 self.env.cr.execute(sql)
#                 result = self.env.cr.dictfetchall()
#                 number = result and result[0] and result[0]['number'] or 0
#                 number = number + 1
#                 
#                 name = str('SI-') + str(scontract.name) + '-%%0%sd' % 2 % number 
#                 shipping_ids = self.search([('name', '=', name)])
#                 if len(shipping_ids) >= 1:
#                     raise UserError(_("Shipping Instruction (%s) was exist.") % (name))
#                 vals['name'] = name
            
        if vals.get('port_of_discharge', False) != False and vals.get('port_of_loading', False) != False:
            if vals.get('port_of_discharge', False) == vals.get('port_of_loading', False):
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        
        result = super(ShippingInstruction, self).create(vals)
        return result
    
    @api.multi
    def write(self, values):    
        if values.get('port_of_discharge', False) and values.get('port_of_loading', False):
            if values.get('port_of_discharge', False) == values.get('port_of_loading', False):
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        elif values.get('port_of_discharge', False):
            if values.get('port_of_discharge', False) == self.port_of_loading.id:
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        elif values.get('port_of_loading', False):
            if values.get('port_of_loading', False) == self.port_of_discharge.id:
                raise ValidationError("Port Of Loading and Port of Discharge is not the same.")
        result = super(ShippingInstruction, self).write(values)
        return result
    
#     @api.multi
#     @api.onchange('contract_id')
#     def onchange_contract_id(self):
#         if not self.contract_id:
#             values = { 'final_destination': False, 'port_of_loading': False, 'port_of_discharge': False, 'partner_id': False, 'shipping_ids': False}
#         
#         vars = []        
#         for contract in self.contract_id.contract_line:
#             vars.append((0, 0, {'name': contract.name or False, 'shipping_id': self.id or False,
#                    'tax_id': [(6, 0, [x.id for x in contract.tax_id])] or False, 'price_unit': contract.price_unit or 0.0,
#                    'product_id': contract.product_id.id or False, 'product_qty': contract.product_qty or 0.0,
#                    'partner_id': self.partner_id.id or False, 'company_id': self.company_id.id or False,
#                    'product_uom': contract.product_uom.id or False, 'state': 'draft'}))
#         values = {'final_destination': self.contract_id.partner_shipping_id.id or False, 'port_of_loading': self.contract_id.port_of_loading.id or False,
#                   'port_of_discharge': self.contract_id.port_of_discharge.id or False, 'partner_id': self.contract_id.partner_id.id or False, 'shipping_ids': vars or False}
#         self.update(values)
        
    @api.multi
    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if not self.warehouse_id:
            return {}
        values = {'shipment_from': self.warehouse_id.partner_id.id or False}
        self.update(values)
    
    
    @api.multi
    def button_done(self):
        self.write({'state': 'done'})
        

    
    @api.multi
    def button_waiting(self):
        if not self.shipping_ids:
            raise UserError(_('You cannot approve a Shipping Instruction without any Shipping Instruction Line.'))
        self.write({'state': 'waiting','user_confirm': self.env.uid,'date_confirm': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def button_approve(self):
        if self.total_cont_qty != self.total_line_qty:
            raise UserError(_('Products qty have not packing out.'))
        self.write({'state': 'approved', 'user_approve': self.env.uid, 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def button_done(self):
        if not self.contract_ids:
            raise UserError(_('You cannot done a SI without any NVS.'))
        self.write({'state': 'done'})
    
    @api.multi
    def button_cancel(self):
        if self.state == 'done':
            raise UserError(_('Unable to cancel SI.'))
        
        if self.contract_ids:
            for line in self.contract_ids:
                if line.state == 'done':
                    raise UserError(_('Unable to cancel SI %s as some receptions have already been done.\n\t You must first cancel related NVS.') % (self.name))
                if line.picking_ids:
                    for i in line.picking_ids:
                        if i.state == 'done':
                            raise UserError(_('Unable to cancel SI %s as some receptions have already been done.\n\t You must first cancel related GDN.') % (self.name))
                if line.delivery_ids:
                    for j in line.delivery_ids:
                        if i.state == 'done':
                            raise UserError(_('Unable to cancel SI %s as some receptions have already been done.\n\t You must first cancel related DO.') % (self.name))
                            
            self.env.cr.execute('''DELETE FROM stock_pack_operation WHERE picking_id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id WHERE sc.shipping_id = %(shipping_id)s);
            DELETE FROM stock_move WHERE picking_id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id WHERE sc.shipping_id = %(shipping_id)s);
            DELETE FROM stock_picking WHERE id in (SELECT sp.id FROM stock_picking sp join sale_contract sc on sc.id = sp.sale_contract_id WHERE sc.shipping_id = %(shipping_id)s);
            DELETE FROM delivery_order_line WHERE delivery_id in (SELECT de.id FROM delivery_order de join sale_contract sc on sc.id = de.contract_id WHERE sc.shipping_id = %(shipping_id)s);
            DELETE FROM delivery_order WHERE id in (SELECT de.id FROM delivery_order de join sale_contract sc on sc.id = de.contract_id WHERE sc.shipping_id = %(shipping_id)s);
            DELETE FROM sale_contract_line WHERE contract_id in (SELECT id FROM sale_contract WHERE shipping_id = %(shipping_id)s);
            DELETE FROM sale_contract WHERE id in (SELECT id FROM sale_contract WHERE shipping_id = %(shipping_id)s);''' % ({'shipping_id': self.id}))
        self.write({'state': 'cancel'})
    
    @api.multi
    def button_load_sc(self):
        if self.contract_id:
            self.env.cr.execute('''DELETE FROM shipping_instruction_line WHERE shipping_id = %s''' % (self.id))
            for contract in self.contract_id.contract_line:
                var = {'name': contract.name or False, 'shipping_id': self.id or False, 'partner_id': self.partner_id.id or False,
                       'tax_id': [(6, 0, [x.id for x in contract.tax_id])] or False, 'company_id': self.company_id.id or False,
                       'price_unit': contract.price_unit or 0.0, 'product_id': contract.product_id.id or False, 'product_qty': contract.product_qty or 0.0,
                       'product_uom': contract.product_uom.id or False, 'state': 'draft'}
                self.env['shipping.instruction.line'].create(var)
        return True
    
    @api.multi
    def create_nvs(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('bes_sale_contract.action_view_wizard_nvs')
        form_view_id = imd.xmlid_to_res_id('bes_sale_contract.view_wizard_nvs')
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
    def action_view_contract_nvs(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('bes_sale_contract.action_sale_contract_export')
        result = action.read()[0]
        contract_ids = sum([order.contract_ids.ids for order in self], [])
        if len(contract_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, contract_ids)) + "]), ('state','!=','cancel')]"
        elif len(contract_ids) == 1:
            res = self.env.ref('bes_sale_contract.view_sale_contract_form', False)
            result['context'] = action.context
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = contract_ids and contract_ids[0] or False
        return result
    
    @api.multi
    def action_view_invoices(self):
        for contract in self.contract_ids:
            for invoice in contract.invoice_ids:
                invoice_ids = (invoice.filtered(lambda r: r.state != 'cancel')) or False
                
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
    
class ShippingInstructionLine(models.Model):
    _name = "shipping.instruction.line"
    _order = 'id desc'
    
    name = fields.Text(string='Description', required=True)
    shipping_id = fields.Many2one('shipping.instruction', string='Shipping Instruction', select=True, ondelete='cascade')   
    sequence = fields.Integer(string='Sequence', default=10)

    company_id = fields.Many2one(related='shipping_id.company_id', string='Company', store=True, readonly=True)
    partner_id = fields.Many2one(related='shipping_id.partner_id', store=True, string='Customer')
    
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'), ('cancel', 'Cancelled')],
          related='shipping_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, required=True)
    product_qty = fields.Float(string='Qty', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='Uom', required=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)
    tax_id = fields.Many2many('account.tax', string='Taxes')
    
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
        
class BesContainers(models.Model):
    _name = "bes.containers"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'id asc'
    
    @api.model
    def _default_uom_id(self):
        uom_ids = self.env['product.uom'].search([('name', '=', 'kg')], limit=1)
        return uom_ids
    
    name = fields.Char(string="No Of Containers", required = True)
    seal_no = fields.Char(string='Seal No.', copy=False, index=True)
    shipping_id = fields.Many2one('shipping.instruction', string='No Of Containers', ondelete='cascade', index=True, copy=False)
    product_qty = fields.Float('Qty', default=1)
    product_uom = fields.Many2one('product.uom', 'UoM', default=_default_uom_id)
    
#     @api.model
#     def create(self, vals):
#         if vals.get('name', '/'):
#             if vals.get('shipping_id', False):
#                 shipping_id = vals.get('shipping_id', False)
#                 shipping = self.env['shipping.instruction'].browse(shipping_id) 
#                 number = 0
#                 sql=''' SELECT count(id) number FROM bes_containers WHERE shipping_id = %s
#                 '''%(vals['shipping_id'])
#                 self.env.cr.execute(sql)
#                 result = self.env.cr.dictfetchall()
#                 number = result and result[0] and result[0]['number'] or 0
#                 number = number + 1
#                 
#                 name = str(shipping.name) + '-%%0%sd' % 2 % + number or 'New' 
#                 vals['name'] = name
#         result = super(BesContainers, self).create(vals)
#         return result

class SaleContract(models.Model):
    _inherit = "sale.contract"
    
    shipping_id = fields.Many2one('shipping.instruction', string='SI No.', required=True,ondelete='cascade', readonly=True , states={'draft': [('readonly', False)]})
    scontract_id = fields.Many2one('s.contract', string='SNo.', ondelete='cascade' , readonly=True , states={'draft': [('readonly', False)]})
    
#     @api.multi
#     @api.onchange('scontract_id')
#     def onchange_scontract_id(self):
#         if not self.scontract_id:
#             values = {'weights': False, 'partner_invoice_id': False, 'dispatch_mode': False, 'port_of_loading':  False,
#                 'port_of_discharge': False, 'deadline': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
#                 'transportation_charges': False, 'partner_id': False, 'exchange_rate': 1,
#                 'delivery_tolerance': 0.0, 'container_status': False, 'currency_id': False, 'payment_term_id': False, 'picking_policy': False, 'final_destination': False}
#             self.update(values)
#             
#         values = {'weights': self.scontract_id.weights or False, 'partner_invoice_id': self.scontract_id.partner_invoice_id.id or False,
#                 'dispatch_mode': self.scontract_id.dispatch_mode or False, 'port_of_loading': self.scontract_id.port_of_loading.id or False,
#                 'port_of_discharge': self.scontract_id.port_of_discharge.id or False,
#                 'transportation_charges': self.scontract_id.transportation_charges or False,
#                 'delivery_tolerance': self.scontract_id.delivery_tolerance or 0.0, 'container_status': self.scontract_id.container_status or False,
#                 'partner_id': self.scontract_id.partner_id.id or False, 'exchange_rate': self.scontract_id.exchange_rate or 1,
#                 'currency_id': self.scontract_id.currency_id.id or False, 'payment_term_id': self.scontract_id.payment_term_id.id or False,
#                 'picking_policy': self.scontract_id.picking_policy or False, 'final_destination': self.scontract_id.final_destination.id or False}
#         self.update(values)
#     
#     @api.multi
#     @api.onchange('shipping_id')
#     def onchange_shipping_id(self):
#         if not self.shipping_id:
#             values = {'company_id': False, 'warehouse_id': False, 'port_of_loading':  False, 'port_of_discharge': False,
#               'final_destination': False, 'currency_id': False, 'exchange_rate': 1, 'partner_id': False,
#               'deadline': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
#               'dispatch_mode': False, 'container_status': False, 'weights': False, 'delivery_tolerance': 0.0,
#               'transportation_charges': False, 'picking_policy': False}
#             self.update(values)
#         
#         values = {'company_id': self.shipping_id.company_id.id or False, 'warehouse_id': self.shipping_id.warehouse_id.id or False, 'deadline': self.shipping_id.deadline,
#              'port_of_loading': self.shipping_id.port_of_loading.id or False, 'port_of_discharge': self.shipping_id.port_of_discharge.id or False,
#              'final_destination': self.shipping_id.final_destination.id or False, 'currency_id': self.shipping_id.contract_id.currency_id.id or False,
#              'exchange_rate': self.shipping_id.contract_id.exchange_rate or 1, 'partner_id': self.shipping_id.partner_id.id or False,
#              'dispatch_mode': self.shipping_id.contract_id.dispatch_mode or False, 'container_status': self.shipping_id.contract_id.container_status or False,
#              'weights': self.shipping_id.contract_id.weights or False, 'delivery_tolerance': self.shipping_id.contract_id.delivery_tolerance or 0.0,
#              'transportation_charges': self.shipping_id.contract_id.transportation_charges or False, 'picking_policy': self.shipping_id.contract_id.picking_policy or False}
#         self.update(values)
    
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
                if new_qty > 0.0:
                    var = {'contract_id': self.id or False, 'name': shipping.name or False, 'product_id': shipping.product_id.id or False,
                       'tax_id': [(6, 0, [x.id for x in shipping.tax_id])] or False, 'price_unit': shipping.price_unit or 0.0,
                       'product_qty': new_qty or 0.0, 'product_uom': shipping.product_uom.id or False, 'state': 'draft'}
                    self.env['sale.contract.line'].create(var)
                
        return True

class PostShipMent(models.Model):
    _name = "post.shipment"
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('post.shipment') or 'New'
        result = super(PostShipMent, self).create(vals)
        return result
    
    name = fields.Char(string="Ps No.", required = True, default='/')
    do_id = fields.Many2one('delivery.order', string='DO no.', ondelete='cascade', index=True, copy=False)
    nvs_nls_id = fields.Many2one('sale.contract', string='NVS - NLS', ondelete='cascade', index=True, copy=False)
    truck_plate = fields.Char(string= "Truck No.",size=128)
    post_line = fields.One2many('post.shipment.line', 'post_id', 
                string='Post Shipment Lines')
    delivery_place_id = fields.Many2one('delivery.place', string='Delivery Place', required=False)
    notes = fields.Text(string='Notes')
    
    @api.multi
    def button_load(self):
        if self.do_id:
            self.env.cr.execute('''DELETE FROM post_shipment_line WHERE post_id = %s''' % (self.id))
            
            val ={
                  'nvs_nls_id':self.do_id.contract_id and self.do_id.contract_id.id or False,
                  'delivery_place_id':self.do_id.delivery_place_id and self.do_id.delivery_place_id.id or False,
                  'truck_plate':self.do_id.trucking_no or False,
                  'packing_id':self.do_id.packing_id and self.do_id.packing_id.id or False
                  }
            self.write(val)
        return True
    

class PostShipMentLine(models.Model):
    _name = "post.shipment.line"
    
    cont_no = fields.Char(string ='Cont no.',size =128,required = True)
    loading_date = fields.Date(string='Loading date')
    post_id= fields.Many2one('post.shipment', string='Post no.')
    bags = fields.Float(string ='Bags',digits=(12, 0) )
    shipped_weight = fields.Float(string ='Shipped weight',digits=(12, 0) )
    bl_date = fields.Date(string='B/L date')
    bl_no = fields.Char(string ='B/L no.',size =128,required = False)
    #supervisor_id = fields.Many2one('res.users', string= 'Supervisor')
    supervisor_id = fields.Char(string= 'Supervisor',size =128)
    nvs_nls_id = fields.Many2one(type='sale.contract',related='post_id.nvs_nls_id',  string='NVS - NLS',store=True)
    do_id = fields.Many2one(type='delivery.order',related='post_id.do_id',  string='Do no.',store=True)
    
    
    
    
