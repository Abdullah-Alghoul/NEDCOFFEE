# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

import time
import math

class SaleReturn(models.Model):
    _name = "sale.return"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'create_date desc, id desc'
    
    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
        
    @api.model
    def _default_note(self):
        return self.env.user.company_id.sale_note
    
    @api.onchange('fiscal_position_id')
    def _compute_tax_id(self):
        for order in self:
            order.order_line._compute_tax_id()
            
    @api.depends('order_line.price_total','currency_rate')
    def _currency_amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'currency_amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed) * order.currency_rate,
                'currency_amount_tax': order.pricelist_id.currency_id.round(amount_tax) * order.currency_rate,
                'currency_amount_total': (amount_untaxed + amount_tax)* order.currency_rate,
            })
    
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.order_line:
                total_qty +=line.product_uom_qty
            order.total_qty = total_qty
    
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty')
    
    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'return_customer'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'return_customer'), ('warehouse_id', '=', False)])
        return types[0].id if types else False
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.depends('order_line.move_ids.picking_id')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.order_line:
                moves = line.move_ids.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)
    
    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True, index=True, default='New')
    origin = fields.Char(string='Source Document', help="Reference of the document that generated this sales order request.")
    client_order_ref = fields.Char(string='Customer Reference', copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFR Sent'),
        ('approve', 'Approve'),
        ('return','Returns Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    validity_date = fields.Date(string='Expiration Date', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    create_date = fields.Datetime(string='Creation Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False, default=fields.Date.context_today)

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, change_default=True, index=True, track_visibility='always')

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Pricelist for current sales order.")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    project_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="The analytic account related to a sales order.", copy=False)

    order_line = fields.One2many('sale.return.line', 'order_id', string='Order Lines', states={'cancel': [('readonly', True)], 'done': [('readonly', True)]}, copy=True)

    note = fields.Text('Terms and conditions', default=_default_note)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', oldname='payment_term')
    fiscal_position_id = fields.Many2one('account.fiscal.position', oldname='fiscal_position', string='Fiscal Position')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('sale.return'))
    
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)
    group_id = fields.Many2one('procurement.group', string="Procurement Group")
    
    currency_currency_id = fields.Many2one(related='company_id.currency_id', store=True, string='Currency Company', readonly=True)
    currency_amount_tax = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Tax',store=True)
    currency_amount_untaxed = fields.Float(compute='_currency_amount_all',digits=(16,0) , string = 'Untaxed Amount',store=True)
    currency_amount_total = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Total',store=True)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, copy=False, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},)
    currency_order_line = fields.One2many('sale.return.line', 'order_id', string='Order Lines', readonly=True,copy=False)
    
    order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, index=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', readonly=True, index=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True, default=_default_picking_type)
    create_uid = fields.Many2one('res.users', 'Responsible')
    date_approve = fields.Date('Approval Date', readonly=1, select=True, copy=False)
    user_confirm = fields.Many2one('res.users', string='User Confirm', readonly=True)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)
    claim_id = fields.Many2one('crm.claim', string='Claims', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, required=True)
    
    @api.multi
    def button_loading(self):
        return_obj = self.env['sale.return.line']
        vals = {}
        for this in self:
            if this.order_line:
                self.env.cr.execute("DELETE FROM sale_return_line WHERE id in (SELECT id FROM sale_return_line WHERE order_id = %s)"%(this.id))
            if this.order_id:
                for i in this.order_id.order_line:
                    vals = {'order_id': this.id or False, 'name': i.name or '',
                            'product_id': i.product_id.id or False,'product_uom_qty': i.product_uom_qty or 0.0,
                            'product_uom': i.product_uom.id or False,'price_unit': i.price_unit or 0.0,'tax_id': [(6, 0, i.tax_id.ids)] or False} 
                    new_id = return_obj.create(vals)
        return True
    
    @api.multi
    def button_dummy(self):
        return True
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({
                'payment_term_id': False,
                'fiscal_position_id': False,
            })
            return
        values = {
            'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
            'payment_term_id': self.partner_id.property_payment_term_id and self.partner_id.property_payment_term_id.id or False,
            'note': self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note,
        }
        self.update(values)
        
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('sale.return') or 'New'

        if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)
        result = super(SaleReturn, self).create(vals)
        return result
    
    @api.multi
    def button_draft(self):
        self.write({'state': 'draft'})
        return {}
        
    @api.multi
    def action_cancel(self):
        for order in self:
            for pick in order.picking_ids:
                if pick.state == 'done':
                    raise UserError(_('Unable to cancel purchase order %s as some receptions have already been done.') % (order.name))

            for pick in order.picking_ids.filtered(lambda r: r.state != 'cancel'):
                pick.action_cancel()
        self.write({'state': 'cancel'})
        
    @api.multi
    def action_done(self):
        self.write({'state': 'done'})
        
    @api.multi
    def button_confirm(self):
        self.write({'state': 'approve', 'user_confirm': self.env.uid})
        return {}
    
    @api.multi
    def button_approve(self):
        if self.state in ('draft,sent'):
            self.button_confirm()
        self.write({'state': 'return', 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'user_approve': self.env.uid})
        self._create_picking()
        return {}
    
    @api.multi
    def _get_destination_location(self):
        return self.picking_type_id.default_location_dest_id.id
    
    @api.model
    def _prepare_picking(self):
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id
            })
        return {
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': self.create_date,
            'origin': self.name,
            'location_dest_id': self._get_destination_location,
            'location_id': self.partner_id.property_stock_customer.id, 
        }

    @api.multi
    def _create_picking(self):
        for order in self:
            ptypes = order.order_line.mapped('product_id.type')
            if ('product' in ptypes) or ('consu' in ptypes):
                res = order._prepare_picking()
                picking = self.env['stock.picking'].create(res)
                moves = order.order_line._create_stock_moves(picking)
                moves.action_confirm()
                moves.force_assign()
        return True
    
    @api.multi
    def action_view_picking(self):
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]

        #override the context to get rid of the default filtering on picking type
        result['context'] = {}
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    def action_rfr_send(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        try:
            if self.env.context.get('send_rfr', False):
                template_id = ir_model_data.get_object_reference('general_sale_return', 'email_template_edi_request_return')[1]
            else:
                template_id = ir_model_data.get_object_reference('general_sale_return', 'email_template_edi_returns_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.return',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

class SaleReturnLine(models.Model):
    _name = 'sale.return.line'
    _order = 'order_id desc, sequence, id'
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
            
    @api.depends('price_subtotal', 'product_uom_qty')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_subtotal / line.product_uom_qty if line.product_uom_qty else 0.0
            
    @api.multi
    def _compute_tax_id(self):
        for line in self:
            fpos = line.order_id.fiscal_position_id or line.order_id.partner_id.property_account_position_id
            if fpos:
                if self.env.uid == SUPERUSER_ID and line.order_id.company_id:
                    taxes = fpos.map_tax(line.product_id.taxes_id).filtered(lambda r: r.company_id == line.order_id.company_id)
                else:
                    taxes = fpos.map_tax(line.product_id.taxes_id)
                line.tax_id = taxes
            else:
                line.tax_id = line.product_id.taxes_id if line.product_id.taxes_id else False
    
    def _currency_price_unit(self):
        for line in self:
            line.currency_price_unit = line.order_id.currency_rate and line.price_unit * line.order_id.currency_rate or line.price_unit
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.currency_price_subtotal = line.order_id.currency_rate and taxes['total_included'] * line.order_id.currency_rate or taxes['total_included']
        
    
    def _price_unit_include(self):
        partner_id = False
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
            
        tax_nxk_ids = []
        
        for line in self:
            partner_id = line.order_id.partner_id
            for tax_nxk in line.tax_id:
                if tax_nxk.transaction_type in ('import','export'):
                    tax_nxk_ids.append(tax_nxk.id)
        if tax_nxk_ids:  
            tax_nxk_ids = self.pool.get('account.tax').browse(self.cr,self.uid,tax_nxk_ids)
                
        for line in self:
            price = line.price_unit 
            if tax_nxk_ids:
                taxes = tax_obj.compute_all(self.cr, self.uid, tax_nxk_ids, price, line.product_qty, product=line.product_id, partner=partner_id)
                line.price_unit_include = 0.0
                for tax in taxes['taxes']:
                    line.price_unit_include += tax['amount']
                if line.order_id:
                    cur = line.order_id.currency_id
                    line.price_unit_include = cur_obj.round(self.cr, self.uid, cur, (line.price_unit_include/line.product_qty/line.product_qty) + line.price_unit)
                    line.currency_price_unit_include = line.order_id.currency_rate and line.price_unit_include * line.order_id.currency_rate or line.price_unit_include
            else:
                line.price_unit_include = line.price_unit
                line.currency_price_unit_include = line.order_id.currency_rate and line.price_unit_include * line.order_id.currency_rate or line.price_unit_include
    
            
    order_id = fields.Many2one('sale.return', string='Order Reference', ondelete='cascade', index=True, copy=False)
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'), default=0.0)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Taxes', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    price_reduce = fields.Monetary(compute='_get_price_reduce', string='Price Reduce', readonly=True, store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes')

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_uom_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    product_uom = fields.Many2one('product.uom', string='Unit of Measure', required=True)

    currency_id = fields.Many2one(related='order_id.currency_id', store=True, string='Currency', readonly=True)
    company_id = fields.Many2one(related='order_id.company_id', string='Company', store=True, readonly=True)
    order_partner_id = fields.Many2one(related='order_id.partner_id', store=True, string='Customer')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFR Sent'),
        ('approve', 'Approve'),
        ('return','Returns Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], related='order_id.state', string='Order Status', readonly=True, copy=False, store=True, default='draft')

    
    currency_price_unit = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Price Unit')
    currency_price_subtotal = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Total')
    
    price_unit_include= fields.Monetary(compute='_price_unit_include', string='Price Include')
    currency_price_unit_include = fields.Monetary(compute='_price_unit_include' ,  string='Currency Price Include',)
    
    move_ids = fields.One2many('stock.move', 'sale_return_line_id', string='Reservation', readonly=True, ondelete='set null', copy=False)
    
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
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id.id,
            quantity=self.product_uom_qty,
            date=self.order_id.create_date,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id
        )

        name = product.name_get()[0][1]
        if product.description_sale:
            name += '\n' + product.description_sale
        vals['name'] = name

        self._compute_tax_id()

        if self.order_id.pricelist_id and self.order_id.partner_id:
            vals['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
        self.update(vals)
        return {'domain': domain}
    
    @api.onchange('product_uom')
    def product_uom_change(self):
        if not self.product_uom:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id.id,
                quantity=self.product_uom_qty,
                date_order=self.order_id.create_date,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id
            )
            self.price_unit = self.env['account.tax']._fix_tax_included_price(product.price, product.taxes_id, self.tax_id)
    
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                price_unit = line.taxes_id.compute_all(price_unit, currency=line.order_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)

            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.order_id.create_date,
                'date_expected': line.date_planned,
                'location_id': line.order_id.picking_type_id.default_location_src_id.id or line.order_id.partner_id.property_stock_customer.id,
                'location_dest_id': line.order_id._get_destination_location(),
                'picking_id': picking.id,
                'partner_id': line.order_id.dest_address_id.id or line.order_id.partner_id.id, 
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': line.id,
                'company_id': line.order_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': line.order_id.picking_type_id.id,
                'group_id': line.order_id.group_id.id,
                'procurement_id': False,
                'origin': line.order_id.name,
                'route_ids': line.order_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.order_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':line.order_id.picking_type_id.warehouse_id.id,
            }
        return done
            
class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'sale.return' and self._context.get('default_res_id') and self._context.get('mark_so_as_sent'):
            order = self.env['sale.return'].browse([self._context['default_res_id']])
            if order.state == 'draft':
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)
