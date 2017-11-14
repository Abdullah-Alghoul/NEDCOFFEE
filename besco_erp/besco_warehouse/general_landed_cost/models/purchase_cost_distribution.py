# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################
from openerp import models, fields, exceptions, api, _
import openerp.addons.decimal_precision as dp


# import openerp.exceptions
# from openerp.osv import fields, osv
# from openerp.tools.translate import _
# import openerp.addons.decimal_precision as dp
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class PurchaseCostDistribution(models.Model):
    _name = "purchase.cost.distribution"
    _description = "Purchase landed costs distribution"
    _order = 'name desc'

    @api.one
    @api.depends('total_expense', 'total_purchase')
    def _compute_amount_total(self):
        self.amount_total = self.total_purchase + self.total_expense
        
    @api.one
    @api.depends('cost_lines', 'cost_lines.total_amount')
    def _compute_total_purchase(self):
        self.total_purchase = sum([x.total_amount for x in self.cost_lines])
        
    @api.one
    @api.depends('cost_lines', 'cost_lines.move_id.price_unit')
    def _compute_total_price_unit(self):
        self.total_price_unit = sum([x.move_id.price_unit * (x.move_id.exchange_rate or 1) for x in
                                     self.cost_lines])
    
    @api.one
    @api.depends('cost_lines', 'cost_lines.product_qty')
    def _compute_total_uom_qty(self):
        self.total_uom_qty = sum([x.move_id.product_qty for x in self.cost_lines])
    
    @api.one
    @api.depends('cost_lines', 'cost_lines.total_weight')
    def _compute_total_weight(self):
        self.total_weight = sum([x.total_weight for x in self.cost_lines])
    
#     @api.one
#     @api.depends('cost_lines', 'cost_lines.total_weight_net')
#     def _compute_total_weight_net(self):
#         self.total_weight_net = sum([x.total_weight_net for x in
#                                      self.cost_lines])

    @api.one
    @api.depends('cost_lines', 'cost_lines.total_volume')
    def _compute_total_volume(self):
        self.total_volume = sum([x.total_volume for x in self.cost_lines])
    
    @api.one
    @api.depends('expense_lines', 'expense_lines.expense_amount')
    def _compute_total_expense(self):
        self.total_expense = sum([x.expense_amount for x in
                                  self.expense_lines])
        
    def _expense_lines_default(self):
        expenses = self.env['purchase.expense.type'].search(
            [('default_expense', '=', True)])
        return [{'type': x} for x in expenses]
    
    name = fields.Char(string='Distribution number', required=True,
                       select=True, default='/')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', required=True,
        default=(lambda self: self.env['res.company']._company_default_get(
            'purchase.cost.distribution')))
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency',
        related="company_id.currency_id")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('calculated', 'Calculated'),
         ('done', 'Done'),
         ('error', 'Error'),
         ('cancel', 'Cancel')], string='Status', readonly=True,
        default='draft')
#     cost_update_type = fields.Selection(
#         [('direct', 'Direct Update')], string='Cost Update Type',
#         default='direct', required=True)
    date = fields.Date(
        string='Date', required=True, readonly=True, select=True,
        states={'draft': [('readonly', False)]},
        default=fields.Date.context_today)
    total_uom_qty = fields.Float(
        compute=_compute_total_uom_qty, readonly=True,
        digits_compute=dp.get_precision('Product UoS'),
        string='Total quantity')
    total_weight = fields.Float(
        compute=_compute_total_weight, string='Total gross weight',
        readonly=True,
        digits_compute=dp.get_precision('Stock Weight'))
#     total_weight_net = fields.Float(
#         compute=_compute_total_weight_net,
#         digits_compute=dp.get_precision('Stock Weight'),
#         string='Total net weight', readonly=True)
    
    invoice_id = fields.Many2one(comodel_name='account.invoice',string='Invoice')
    total_volume = fields.Float(
        compute=_compute_total_volume, string='Total volume', readonly=True)
    total_purchase = fields.Float(
        compute=_compute_total_purchase,
        digits_compute=dp.get_precision('Account'), string='Total purchase')
    total_price_unit = fields.Float(
        compute=_compute_total_price_unit, string='Total price unit',
        digits_compute=dp.get_precision('Product Price'))
    amount_total = fields.Float(
        compute=_compute_amount_total,
        digits_compute=dp.get_precision('Account'), string='Total')
    total_expense = fields.Float(
        compute=_compute_total_expense,
        digits_compute=dp.get_precision('Account'), string='Total expenses')
    note = fields.Text(string='Documentation for this order')
    cost_lines = fields.One2many(
        comodel_name='purchase.cost.distribution.line', ondelete="cascade",
        inverse_name='distribution', string='Distribution lines')
    expense_lines = fields.One2many(
        comodel_name='purchase.cost.distribution.expense', ondelete="cascade",
        inverse_name='distribution', string='Expenses',)
        #default=_expense_lines_default)
    
    @api.multi
    def unlink(self):
        for c in self:
            if c.state not in ('draft', 'calculated'):
                raise exceptions.Warning(
                    _("You can't delete a confirmed cost distribution"))
        return super(PurchaseCostDistribution, self).unlink()

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'purchase.cost.distribution')
        return super(PurchaseCostDistribution, self).create(vals)
             
    @api.multi
    def action_calculate(self):
        for distribution in self:
            # Check expense lines for amount 0
            if any([not x.expense_amount for x in distribution.expense_lines]):
                raise exceptions.Warning(
                    _('Please enter an amount for all the expenses'))
            # Check if exist lines in distribution
            if not distribution.cost_lines:
                raise exceptions.Warning(
                    _('There is no picking lines in the distribution'))
            # Calculating expense line
            for line in distribution.cost_lines:
                line.expense_lines.unlink()
                    
                for expense in distribution.expense_lines:
                    if (expense.affected_lines and
                            line.id not in expense.affected_lines.ids):
                        continue
                    if expense.calculation_method == 'amount':
                        multiplier = line.total_amount
                        if expense.affected_lines:
                            divisor = sum([x.total_amount for x in
                                           expense.affected_lines])
                        else:
                            divisor = distribution.total_purchase
                    elif expense.calculation_method == 'price':
                        multiplier = line.product_price_unit
                        if expense.affected_lines:
                            divisor = sum([x.product_price_unit for x in
                                           expense.affected_lines])
                        else:
                            divisor = distribution.total_price_unit
                    elif expense.calculation_method == 'qty':
                        multiplier = line.product_qty
                        if expense.affected_lines:
                            divisor = sum([x.product_qty for x in
                                           expense.affected_lines])
                        else:
                            divisor = distribution.total_uom_qty
                    elif expense.calculation_method == 'weight':
                        multiplier = line.total_weight
                        if expense.affected_lines:
                            divisor = sum([x.total_weight for x in
                                           expense.affected_lines])
                        else:
                            divisor = distribution.total_weight
#                     elif expense.calculation_method == 'weight_net':
#                         multiplier = line.total_weight_net
#                         if expense.affected_lines:
#                             divisor = sum([x.total_weight_net for x in
#                                            expense.affected_lines])
#                         else:
#                             divisor = distribution.total_weight_net
                    elif expense.calculation_method == 'volume':
                        multiplier = line.total_volume
                        if expense.affected_lines:
                            divisor = sum([x.total_volume for x in
                                           expense.affected_lines])
                        else:
                            divisor = distribution.total_volume
                    elif expense.calculation_method == 'equal':
                        multiplier = 1
                        divisor = (len(expense.affected_lines) or
                                   len(distribution.cost_lines))
                    else:
                        raise exceptions.Warning(
                            _('No valid distribution type.'))
                    expense_amount = (expense.expense_amount * multiplier / divisor)
                    expense_line = {
                        'distribution_expense': expense.id,
                        'expense_amount': expense_amount,
                        'cost_ratio': expense_amount / line.product_qty,
                        'distribution_line': line.id,
                    }
                    line.expense_lines = [(0, 0, expense_line)]
            distribution.state = 'calculated'
        return True

    @api.one
    def action_done(self):
        move_obj = self.pool.get('stock.move')
        for line in self.cost_lines:
#             move_obj.write(self.env.cr,self.env.uid,[line.move_id.id],{'costed':False,'price_unit':line.standard_price_new})         
            #THANH: Using SQL instead of write object
            sql='''
                UPDATE stock_move 
                SET costed = false, price_unit= %s
                WHERE id = %s
            '''%(line.standard_price_new, line.move_id.id)
            self.env.cr.execute(sql)
            
            sql='''
                UPDATE stock_picking set is_landed_cost = true
                WHERE id = %s
            '''%(line.move_id.picking_id.id)
            self.env.cr.execute(sql)
        
        for line in self.expense_lines:
            sql='''
                UPDATE account_voucher set is_landed_cost = true
                WHERE id = %s;
            '''%(line.invoice_line.id)
            self.env.cr.execute(sql)
        self.state = 'done'
        
    @api.multi
    def action_draft(self):
        for line in self.cost_lines:
            sql='''
                UPDATE stock_picking set is_landed_cost = false
                WHERE id = %s
            '''%(line.move_id.picking_id.id)
            self.env.cr.execute(sql)
        
        for line in self.expense_lines:
            sql='''
                UPDATE account_voucher set is_landed_cost = false
                WHERE id = %s;
            '''%(line.invoice_line.id)
            self.env.cr.execute(sql)
        self.write({'state': 'draft'})
        return True
    
    @api.one
    def action_cancel(self):
        for line in self.cost_lines:
            sql='''
                UPDATE stock_picking set is_landed_cost = false
                WHERE id = %s
            '''%(line.move_id.picking_id.id)
            self.env.cr.execute(sql)
        
        for line in self.expense_lines:
            sql='''
                UPDATE account_invoice_line set is_landed_cost = false
                WHERE id = %s;
            '''%(line.invoice_line.id)
            self.env.cr.execute(sql)
            sql='''
                UPDATE account_invoice set is_landed_cost = false
                WHERE id = %s;
            '''%(line.invoice_line.invoice_id.id)
            self.env.cr.execute(sql)
        self.state = 'draft'

class PurchaseCostDistributionLine(models.Model):
    _name = "purchase.cost.distribution.line"
    _description = "Purchase cost distribution Line"

    @api.one
    @api.depends('price_unit_include', 'product_qty')
    def _compute_total_amount(self):
        self.total_amount = self.price_unit_include * self.move_id.product_qty
    
#     def _compute_total_purchase(self, cr, uid, ids, name, args, context=None):
#         res = {}
#         cur_obj = self.pool.get('res.currency')
#         for this in self.browse(cr, uid, ids):
#             res[this.id] = 0.0
#             for cost_line in this.cost_lines:
#                 if cost_line.move_id and cost_line.move_id.purchase_line_id:
#                     if cost_line.move_id.company_id.currency_id and cost_line.move_id.purchase_line_id.order_id.currency_id:
#                         if cost_line.move_id.picking_id.date_done:
#                             context['date'] = datetime.strptime(cost_line.move_id.picking_id.date_done, DATETIME_FORMAT) + relativedelta(hours=7)
#                         else:
#                             context['date'] = date = time.strftime(DATE_FORMAT)
#                             
#                     rate = cur_obj._current_rate_computation(cr, uid, [cost_line.move_id.purchase_line_id.order_id.currency_id.id], None, None, True, context=context)
#                     if rate:
#                         res[this.id] += cost_line.move_id.purchase_line_id.price_unit_include * cost_line.move_id.product_qty * rate[cost_line.move_id.purchase_line_id.order_id.currency_id.id]
#                     else:
#                         res[line.id] += cost_line.move_id.purchase_line_id.price_unit_include * cost_line.move_id.product_qty
#         
#         return res
    
    @api.one
    @api.depends('product_id', 'product_qty')
    def _compute_total_weight(self):
        self.total_weight = self.product_weight * self.move_id.product_qty
    
#     @api.one
#     @api.depends('product_id', 'product_qty')
#     def _compute_total_weight_net(self):
#         self.total_weight_net = self.product_weight_net * self.move_id.product_qty
    
    @api.one
    @api.depends('product_id', 'product_qty')
    def _compute_total_volume(self):
        self.total_volume = self.product_volume * self.move_id.product_qty
    
    @api.one
    @api.depends('expense_lines', 'expense_lines.cost_ratio')
    def _compute_cost_ratio(self):
        self.cost_ratio = sum([x.cost_ratio for x in self.expense_lines])
    
    @api.one
    @api.depends('expense_lines', 'expense_lines.expense_amount')
    def _compute_expense_amount(self):
        self.expense_amount = sum([x.expense_amount for x in
                                   self.expense_lines])
    
    @api.one
    @api.depends('cost_ratio')
    def _compute_standard_price_new(self):
        self.standard_price_new = self.price_unit_include + self.cost_ratio
    
    @api.one
    @api.depends('move_id', 'move_id.picking_id', 'move_id.product_id',
                 'move_id.product_qty')
    def _compute_display_name(self):
        self.name = '%s / %s / %s' % (
            self.move_id.picking_id.name, self.move_id.product_id.display_name,
            self.move_id.product_qty)
    
    @api.one
    @api.depends('move_id', 'move_id.product_id')
    def _get_product_id(self):
        # Cannot be done via related field due to strange bug in update chain
        self.product_id = self.move_id.product_id.id
    
    @api.one
    @api.depends('move_id', 'move_id.product_qty')
    def _get_product_qty(self):
        # Cannot be done via related field due to strange bug in update chain
        self.product_qty = self.move_id.product_qty
    
    @api.one
    @api.depends('move_id')
    def _get_standard_price_old(self):
        self.standard_price_old = self.move_id.price_unit
    
    @api.one
    def _price_unit_include(self):
        invoice_line_ids = False
        self.price_unit_include = 0.0
        if self.picking_id:
            sql='''
                SELECT ail.id
                FROM account_invoice ai join stock_invoice_rel sir on ai.id = sir.invoice_id
                    JOIN purchase_cost_distribution_line pcdl on sir.picking_id = pcdl.picking_id
                    JOIN account_invoice_line  ail on ail.invoice_id = ai.id
                WHERE sir.picking_id = %s
                  and ail.product_id = %s
                  and ail.uom_id = %s
            '''%(self.picking_id.id, self.product_id.id, self.product_uom.id)
            self.env.cr.execute(sql)
            invoice_line_ids = [i[0] for i in self.env.cr.fetchall()]
            if invoice_line_ids:
                invoice_line = self.env['account.invoice.line'].browse(invoice_line_ids[0])
                self.price_unit_include = invoice_line.price_unit_include * (invoice_line.invoice_id.currency_rate or 1)
    
    @api.one
    def _product_price_unit(self):
        
        invoice_line_ids = False
        self.product_price_unit = 0.0
        if self.picking_id:
            sql='''
                SELECT ail.id
                FROM account_invoice ai join stock_invoice_rel sir on ai.id = sir.invoice_id
                    JOIN purchase_cost_distribution_line pcdl on sir.picking_id = pcdl.picking_id
                    JOIN account_invoice_line  ail on ail.invoice_id = ai.id
                WHERE sir.picking_id = %s
                  and ail.product_id = %s
                  and ail.uom_id = %s
            '''%(self.picking_id.id, self.product_id.id, self.product_uom.id)
            self.env.cr.execute(sql)
            invoice_line_ids = [i[0] for i in self.env.cr.fetchall()]
            if invoice_line_ids:
                invoice_line = self.env['account.invoice.line'].browse(invoice_line_ids[0])
                self.product_price_unit = invoice_line.price_unit * (invoice_line.invoice_id.currency_rate or 1)
        
        
        
#         context = {}
#         rate =0
#         cur_obj = self.env['res.currency']
#         self.product_price_unit = 0
#         if self.move_id and self.move_id.purchase_line_id:
#             if self.move_id.company_id.currency_id and self.move_id.purchase_line_id.order_id.currency_id:
#                 if self.move_id.picking_id.date_done:
#                     context['date'] = datetime.strptime(self.move_id.picking_id.date_done, DATETIME_FORMAT) + relativedelta(hours=7)
#                 else:
#                     context['date'] = time.strftime(DATE_FORMAT)
#                 rate = cur_obj._current_rate_computation([self.move_id.purchase_line_id.order_id.currency_id.id], None, None, True, context=context)
#             if rate:
#                 self.product_price_unit = self.move_id.purchase_line_id.price_unit * rate[self.move_id.purchase_line_id.order_id.currency_id.id]
#             else:
#                 self.product_price_unit = self.move_id.purchase_line_id.price_unit
    
    name = fields.Char(
        string='Name', compute='_compute_display_name')
    distribution = fields.Many2one(
        comodel_name='purchase.cost.distribution', string='Cost distribution',
        ondelete='cascade')
    move_id = fields.Many2one(
        comodel_name='stock.move', string='Picking line', ondelete="restrict")
#     purchase_line_id = fields.Many2one(
#         comodel_name='purchase.order.line', string='Purchase order line',
#         related='move_id.purchase_line_id')
#     purchase_id = fields.Many2one(
#         comodel_name='purchase.order', string='Purchase order', readonly=True,
#         related='move_id.purchase_line_id.order_id', store=True)
    partner = fields.Many2one(
        comodel_name='res.partner', string='Supplier', readonly=True,
        related='move_id.partner_id')
    picking_id = fields.Many2one(
        'stock.picking', string='Picking', related='move_id.picking_id',
        store=True)
    product_id = fields.Many2one(
        comodel_name='product.product', string='Product', store=True,
        compute='_get_product_id')
    product_qty = fields.Float(
        string='Quantity', compute='_get_product_qty', store=True)
    product_uom = fields.Many2one(
        comodel_name='product.uom', string='Unit of measure',
        related='move_id.product_uom')
#     product_uos_qty = fields.Float(
#         string='Quantity (UoS)', related='move_id.product_uos_qty')
#     product_uos = fields.Many2one(
#         comodel_name='product.uom', string='Product UoS',
#         related='move_id.product_uos')
    
    #KIET: Add these fields to compute value
    price_unit_include = fields.Float(compute='_price_unit_include', string='Price Include', 
                                      readonly=True, digits_compute= dp.get_precision('Product Price'))
    product_price_unit = fields.Float(compute='_product_price_unit', string='Unit price', 
                                      readonly=True, digits_compute= dp.get_precision('Product Price'))
        
    expense_lines = fields.One2many(
        comodel_name='purchase.cost.distribution.line.expense',
        inverse_name='distribution_line', string='Expenses distribution lines',
        ondelete='cascade')
    product_volume = fields.Float(
        string='Volume', help="The volume in m3.",
        related='product_id.product_tmpl_id.volume')
    product_weight = fields.Float(
        string='Gross weight', related='product_id.product_tmpl_id.weight',
        help="The gross weight in Kg.")
#     product_weight_net = fields.Float(
#         string='Net weight', related='product_id.product_tmpl_id.weight_net',
#         help="The net weight in Kg.")
    standard_price_old = fields.Float(
        string='Previous cost', compute="_get_standard_price_old", store=True,
        digits_compute=dp.get_precision('Product Price'))
    expense_amount = fields.Float(
        string='Cost amount', digits_compute=dp.get_precision('Account'),
        compute='_compute_expense_amount')
    cost_ratio = fields.Float(
        string='Unit cost', digits_compute=dp.get_precision('Account'),
        compute='_compute_cost_ratio')
    standard_price_new = fields.Float(
        string='New cost', digits_compute=dp.get_precision('Product Price'),
        compute='_compute_standard_price_new')
    total_amount = fields.Float(
        compute=_compute_total_amount, string='Amount line',
        digits_compute=dp.get_precision('Account'))
    total_weight = fields.Float(
        compute=_compute_total_weight, string="Line weight", store=True,
        digits_compute=dp.get_precision('Stock Weight'),
        help="The line gross weight in Kg.")
#     total_weight_net = fields.Float(
#         compute=_compute_total_weight_net, string='Line net weight',
#         digits_compute=dp.get_precision('Stock Weight'), store=True,
#         help="The line net weight in Kg.")
    total_volume = fields.Float(
        compute=_compute_total_volume, string='Line volume', store=True,
        help="The line volume in m3.")
    
class PurchaseCostDistributionLineExpense(models.Model):
    _name = "purchase.cost.distribution.line.expense"
    _description = "Purchase cost distribution line expense"
    
    distribution_line = fields.Many2one(
        comodel_name='purchase.cost.distribution.line',
        string='Cost distribution line', ondelete="cascade")
    distribution_expense = fields.Many2one(
        comodel_name='purchase.cost.distribution.expense',
        string='Distribution expense', ondelete="cascade")
    type = fields.Many2one(
        'purchase.expense.type', string='Expense type',
        related='distribution_expense.type')
    expense_amount = fields.Float(
        string='Expense amount', default=0.0,
        digits_compute=dp.get_precision('Account'))
    cost_ratio = fields.Float(
        'Unit cost', default=0.0,
        digits_compute=dp.get_precision('Account'))


class PurchaseCostDistributionExpense(models.Model):
    _name = "purchase.cost.distribution.expense"
    _description = "Purchase cost distribution expense"

    @api.one
    @api.depends('distribution', 'distribution.cost_lines')
    def _get_imported_lines(self):
        self.imported_lines = self.env['purchase.cost.distribution.line']
        self.imported_lines |= self.distribution.cost_lines
    
    distribution = fields.Many2one(
        comodel_name='purchase.cost.distribution', string='Cost distribution',
        select=True, ondelete="cascade", required=True)
    ref = fields.Char(string="Reference")
    type = fields.Many2one(
        comodel_name='purchase.expense.type', string='Expense type',
        select=True, ondelete="restrict")
    calculation_method = fields.Selection(
        string='Calculation method', related='type.calculation_method',
        readonly=True)
    imported_lines = fields.Many2many(
        comodel_name='purchase.cost.distribution.line',
        string='Imported lines', compute='_get_imported_lines')
    affected_lines = fields.Many2many(
        comodel_name='purchase.cost.distribution.line', column1="expense_id",
        relation="distribution_expense_aff_rel", column2="line_id",
        string='Affected lines',
        help="Put here specific lines that this expense is going to be "
             "distributed across. Leave it blank to use all imported lines.",
        domain="[('id', 'in', imported_lines[0][2])]")
    expense_amount = fields.Float(
        string='Expense amount', digits_compute=dp.get_precision('Account'),
        required=False)
    invoice_line = fields.Many2one(
        comodel_name='account.voucher.line', string="Supplier Voucher line")