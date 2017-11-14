# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.tools.float_utils import float_is_zero, float_compare
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, AccessError

class PurchaseReturn(models.Model):
    _name = "purchase.return"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Returns Order"
    _order = 'date_create desc, id desc'
    
    @api.depends('return_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.return_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
            
    @api.multi
    def _inverse_date_planned(self):
        for order in self:
            order.return_line.write({'date_planned': self.date_planned})
    
    @api.depends('return_line.date_planned')
    def _compute_date_planned(self):
        for order in self:
            min_date = False
            for line in order.return_line:
                if not min_date or line.date_planned < min_date:
                    min_date = line.date_planned
            if min_date:
                order.date_planned = min_date
                
    @api.model
    def _default_picking_type(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'return_supplier'), ('warehouse_id.company_id', '=', company_id)])
        if not types:
            types = type_obj.search([('code', '=', 'return_supplier'), ('warehouse_id', '=', False)])
        return types[0].id if types else False
    
    @api.depends('return_line.move_ids.picking_id')
    def _compute_picking(self):
        for order in self:
            pickings = self.env['stock.picking']
            for line in order.return_line:
                moves = line.move_ids.filtered(lambda r: r.state != 'cancel')
                pickings |= moves.mapped('picking_id')
            order.picking_ids = pickings
            order.picking_count = len(pickings)
    
    @api.depends('return_line.price_total','currency_rate')
    def _currency_amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.return_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'currency_amount_untaxed': order.currency_id.round(amount_untaxed) * order.currency_rate,
                'currency_amount_tax': order.currency_id.round(amount_tax) * order.currency_rate,
                'currency_amount_total': (amount_untaxed + amount_tax)* order.currency_rate,
            })
    
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.return_line:
                total_qty +=line.product_qty
            order.total_qty = total_qty
    
    READONLY_STATES = {
        'approve': [('readonly', True)],
        'return': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }
    
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', states=READONLY_STATES, change_default=True, track_visibility='always')
    name = fields.Char('Return Reference', required=True, select=True, copy=False, default='New')
    origin = fields.Char('Source Document', copy=False)
    partner_ref = fields.Char('Vendor Reference', copy=False)
    date_create = fields.Datetime('Create Date', required=True, states=READONLY_STATES, select=True, copy=False, default=fields.Datetime.now())
    date_approve = fields.Date('Approval Date', readonly=1, select=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, states=READONLY_STATES, change_default=True, track_visibility='always')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,default=lambda self: self.env.user.company_id.currency_id.id)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, copy=False, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},)
    return_line = fields.One2many('purchase.return.line', 'return_id', string='Order Lines', states=READONLY_STATES, copy=True)
    currency_return_line = fields.One2many('purchase.return.line', 'return_id', string='Order Lines', readonly=True, copy=False)
    notes = fields.Text('Terms and Conditions')
    dest_address_id = fields.Many2one('res.partner', string='Drop Ship Address', states=READONLY_STATES)
    
    
    picking_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking', string='Receptions', copy=False)
    group_id = fields.Many2one('procurement.group', string="Procurement Group")
    
    date_planned = fields.Datetime(string='Scheduled Date', compute='_compute_date_planned', inverse='_inverse_date_planned', required=True, select=True, default=fields.Datetime.now(),oldname='minimum_planned_date')
    
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    
    
    picking_type_id = fields.Many2one('stock.picking.type', 'Deliver To', states=READONLY_STATES, required=True, default=_default_picking_type,\
        help="This will determine picking type of incoming shipment")
    
    create_uid = fields.Many2one('res.users', 'Responsible')
    user_confirm = fields.Many2one('res.users', string='User Confirm', readonly=True)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, select=1, states=READONLY_STATES, default=lambda self: self.env.user.company_id.id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFR Sent'),
        ('approve', 'Approve'),
        ('return','Returns Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Status', readonly=True, select=True, copy=False, default='draft', track_visibility='onchange')
    
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position')
    payment_term_id = fields.Many2one('account.payment.term', 'Payment Term')
    
    currency_currency_id = fields.Many2one(related='company_id.currency_id', store=True, string='Currency Company', readonly=True)
    currency_amount_tax = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Tax',store=True)
    currency_amount_untaxed = fields.Float(compute='_currency_amount_all',digits=(16,0) , string = 'Untaxed Amount',store=True)
    currency_amount_total = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Total',store=True)
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty')
    claim = fields.Char('Claim', required=True, states=READONLY_STATES, copy=False)
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('partner_ref', operator, name)]
        pos = self.search(domain + args, limit=limit)
        return pos.name_get()
    
    @api.multi
    @api.depends('name', 'partner_ref')
    def name_get(self):
        result = []
        for po in self:
            name = po.name
            if po.partner_ref:
                name += ' ('+po.partner_ref+')'
            result.append((po.id, name))
        return result
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.return') or '/'
        return super(PurchaseReturn, self).create(vals)
    
    @api.multi
    def unlink(self):
        for order in self:
            if order.state not in ['draft', 'cancel']:
                raise UserError(_('In order to delete a returns by PO, you must cancel it first.'))
        return super(PurchaseReturn, self).unlink()
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.fiscal_position_id = False
            self.payment_term_id = False
            self.currency_id = False
        else:
            self.fiscal_position_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
            self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
            self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
        return {}
    
    @api.multi
    def button_approve(self):
        if self.state in ('draft,sent'):
            self.button_confirm()
        self.write({'state': 'return', 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),  'user_approve': self.env.uid})
        self._create_picking()
        return {}
    
    @api.multi
    def button_draft(self):
        self.write({'state': 'draft'})
        return {}
    
    @api.multi
    def button_confirm(self):
        self.write({'state': 'approve', 'user_confirm': self.env.uid})
        return {}
    
    @api.multi
    def button_cancel(self):
        for order in self:
            for pick in order.picking_ids:
                if pick.state == 'done':
                    raise UserError(_('Unable to cancel purchase order %s as some receptions have already been done.') % (order.name))

            for pick in order.picking_ids.filtered(lambda r: r.state != 'cancel'):
                pick.action_cancel()
        self.write({'state': 'cancel'})
    
    @api.multi
    def button_done(self):
        self.write({'state': 'done'})
    
    @api.multi
    def _get_destination_location(self):
        self.ensure_one()
        if self.partner_id:
            if self.dest_address_id:
                return self.dest_address_id.property_stock_supplier.id
            else:
                return self.partner_id.property_stock_supplier.id
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
            'date': self.date_create,
            'origin': self.name,
            'location_dest_id': self._get_destination_location(),
            'location_id': self.picking_type_id.default_location_src_id.id and self.picking_type_id.warehouse_id.lot_stock_id.id
        }

    @api.multi
    def _create_picking(self):
        for order in self:
            ptypes = order.return_line.mapped('product_id.type')
            if ('product' in ptypes) or ('consu' in ptypes):
                res = order._prepare_picking()
                picking = self.env['stock.picking'].create(res)
                moves = order.return_line._create_stock_moves(picking)
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
                template_id = ir_model_data.get_object_reference('general_purchase_return', 'email_template_edi_request_return')[1]
            else:
                template_id = ir_model_data.get_object_reference('general_purchase_return', 'email_template_edi_returns_done')[1]
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
    
    @api.multi
    def button_loading(self):
        return_obj = self.env['purchase.return.line']
        vals = {}
        for this in self:
            if this.return_line:
                self.env.cr.execute("DELETE FROM purchase_return_line WHERE id in (SELECT id FROM purchase_return_line WHERE return_id = %s)"%(this.id))
            if this.purchase_id:
                for i in this.purchase_id.order_line:
                    vals = {'return_id': this.id or False, 'name': i.name or '',
                            'product_id': i.product_id.id or False,'product_qty': i.product_qty or 0.0,
                            'product_uom': i.product_uom.id or False,'price_unit': i.price_unit or 0.0,'taxes_id': [(6, 0, i.taxes_id.ids)] or False,
                            'date_planned': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)} 
                    new_id = return_obj.create(vals)
        return True
    
class PurchaseReturnLine(models.Model):
    _name = 'purchase.return.line'
    
    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(line.price_unit, line.return_id.currency_id, line.product_qty, product=line.product_id, partner=line.return_id.partner_id)
            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.depends('return_id.state', 'move_ids.state')
    def _compute_qty_received(self):
        for line in self:
            if line.return_id.state not in ['assigned', 'done']:
                line.qty_received = 0.0
                continue
            if line.product_id.type not in ['consu', 'product']:
                line.qty_received = line.product_qty
                continue
            total = 0.0
            for move in line.move_ids:
                if move.state == 'done':
                    total += move.product_qty
            line.qty_received = total
    
    def _currency_price_unit(self):
        for line in self:
            line.currency_price_unit = line.return_id.currency_rate and line.price_unit * line.return_id.currency_rate or line.price_unit
            price = line.price_unit 
            taxes = line.taxes_id.compute_all(price, line.return_id.currency_id, line.product_qty, product=line.product_id, partner=line.return_id.partner_id)
            line.currency_price_subtotal = line.return_id.currency_rate and taxes['total_included'] * line.return_id.currency_rate or taxes['total_included']
        
    def _price_unit_include(self):
        partner_id = False
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
            
        tax_nxk_ids = []
        for line in self:
            partner_id = line.return_id.partner_id
            for tax_nxk in line.taxes_id:
                if tax_nxk.transaction_type in ('import','export'):
                    tax_nxk_ids.append(tax_nxk.id)

        if tax_nxk_ids:    
            for line in self:
                price = self.price_unit 
                taxes = tax_obj.compute_all(self.cr, self.uid, tax_nxk_ids, price, line.product_qty, product=line.product_id, partner=partner_id)
                line.price_unit_include = 0.0
                for tax in taxes['taxes']:
                    line.price_unit_include += tax['amount']
                if self.return_id:
                    cur = line.return_id.currency_id
                    line.price_unit_include = cur_obj.round(self.cr, self.uid, cur, (line.price_unit_include/line.product_qty/line.product_qty) + line.price_unit)
                    line.currency_price_unit_include = line.return_id.currency_rate and line.price_unit_include * line.return_id.currency_rate or line.price_unit_include
        else:
            for line in self:
                line.price_unit_include = line.price_unit
                line.currency_price_unit_include = line.return_id.currency_rate and line.price_unit_include * line.return_id.currency_rate or line.price_unit_include
    
    name = fields.Text(string='Description', required=True)
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    date_planned = fields.Datetime(string='Scheduled Date', required=True, select=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    product_uom = fields.Many2one('product.uom', string='Product Unit of Measure', required=True)
    product_id = fields.Many2one('product.product', string='Product', change_default=True, required=True)
    
    qty_received = fields.Float(compute='_compute_qty_received', string="Received Qty", store=True)
    
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', string='Tax', store=True)
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))

    move_ids = fields.One2many('stock.move', 'purchase_return_line_id', string='Reservation', readonly=True, ondelete='set null', copy=False)
    
    return_id = fields.Many2one('purchase.return', string='Return Reference', select=True, required=True, ondelete='cascade')
    state = fields.Selection(related='return_id.state', stored=True)
    
    partner_id = fields.Many2one('res.partner', related='return_id.partner_id', string='Partner', readonly=True, store=True)
    company_id = fields.Many2one('res.company', related='return_id.company_id', string='Company', store=True, readonly=True)
    currency_id = fields.Many2one(related='return_id.currency_id', store=True, string='Currency', readonly=True)
    date_create = fields.Datetime(related='return_id.date_create', string='Return Date', readonly=True)

    currency_price_unit = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Price Unit')
    currency_price_subtotal = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Total')
    
    price_unit_include= fields.Monetary(compute='_price_unit_include', string='Price Include')
    currency_price_unit_include = fields.Monetary(compute='_price_unit_include' ,  string='Currency Price Include',)
    
    def unlink(self):
        for line in self:
            if line.return_id.state in ['approved', 'return','done']:
                raise UserError(_('Cannot delete a purchase order line which is in state \'%s\'.') %(line.state,))
        return super(PurchaseReturnLine, self).unlink()
    
    @api.model
    def _get_date_planned(self, seller, pr=False):
        date_create = pr.date_create if pr else self.return_id.date_create
        if date_create:
            return datetime.strptime(date_create, DEFAULT_SERVER_DATETIME_FORMAT) + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)
    
    @api.onchange('product_id', 'product_qty', 'product_uom')
    def onchange_product_id(self):
        result = {}
        if not self.product_id:
            return result

        if self.product_id.uom_id.category_id.id != self.product_uom.category_id.id:
            self.product_uom = self.product_id.uom_po_id
        result['domain'] = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        product_lang = self.product_id.with_context({
            'lang': self.partner_id.lang,
            'partner_id': self.partner_id.id,
        })
        self.name = product_lang.display_name
        if product_lang.description_purchase:
            self.name += '\n' + product_lang.description_purchase

        seller = self.product_id._select_seller(
            self.product_id,
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.return_id.date_create and self.return_id.date_create[:10],
            uom_id=self.product_uom)

        if seller or not self.date_planned:
            self.date_planned = self._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if not seller:
            return result

        fpos = self.return_id.fiscal_position_id
        self.taxes_id = fpos.map_tax(self.product_id.supplier_taxes_id)

        price_unit = self.env['account.tax']._fix_tax_included_price(seller.price, self.product_id.supplier_taxes_id, self.taxes_id) if seller else 0.0
        if price_unit and seller and self.return_id.currency_id and seller.currency_id != self.return_id.currency_id:
            price_unit = seller.currency_id.compute(price_unit, self.return_id.currency_id)
        self.price_unit = price_unit
        return result
    
    @api.multi
    def _create_stock_moves(self, picking):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            order = line.return_id
            price_unit = line.price_unit
            if line.taxes_id:
                price_unit = line.taxes_id.compute_all(price_unit, currency=line.return_id.currency_id, quantity=1.0)['total_excluded']
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                price_unit = order.currency_id.compute(price_unit, order.company_id.currency_id, round=False)

            template = {
                'name': line.name or '',
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'date': line.return_id.date_create,
                'date_expected': line.date_planned,
                'location_id': line.return_id.picking_type_id.default_location_src_id.id or line.return_id.picking_type_id.warehouse_id.lot_stock_id.id,
                'location_dest_id': line.return_id._get_destination_location(),
                'picking_id': picking.id,
                'partner_id': line.return_id.dest_address_id.id or line.return_id.partner_id.id, 
                'move_dest_id': False,
                'state': 'draft',
                'purchase_line_id': line.id,
                'company_id': line.return_id.company_id.id,
                'price_unit': price_unit,
                'picking_type_id': line.return_id.picking_type_id.id,
                'group_id': line.return_id.group_id.id,
                'procurement_id': False,
                'origin': line.return_id.name,
                'route_ids': line.return_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in line.return_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id':line.return_id.picking_type_id.warehouse_id.id,
            }
        return done
    
class MailComposeMessage(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'purchase.return' and self._context.get('default_res_id'):
            order = self.env['purchase.return'].browse([self._context['default_res_id']])
            if order.state == 'draft':
                order.state = 'sent'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)
