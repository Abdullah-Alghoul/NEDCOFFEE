# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    @api.one
    @api.depends('price_unit', 'purchase_price', 'product_uom_qty')
    def _product_margin(self):
        for line in self:
            line.margin = 0
            sale_amount = line.price_subtotal#(line.price_unit*line.product_uos_qty*(100.0-line.discount)/100.0)
            cost_amount = line.purchase_price * line.product_uom_qty
            if not line.purchase_price and line.product_id:
                cost_amount = line.product_id.standard_price * line.product_uom_qty
            margin = 0.0
            if not cost_amount:
                margin = 100.0
            else:
                margin = round((sale_amount - cost_amount) * 100/cost_amount, 3)
            line.margin = margin
    
    margin = fields.Float(compute='_product_margin', string='Margin (%)')
    purchase_price = fields.Float(string='Cost Price', digits=(16,2))
    mark_up = fields.Float(string='Mark-up (%)', digits=(16,2), readonly=True, default=0.0)
    
    @api.multi
    def _check_mark_up(self):
        for data in self:
            if data.mark_up < 0:
                return False
        return True
     
    _constraints = [
        (_check_mark_up, 'Mark-up must be greater than 0', []),
    ]
    
#     @api.multi
#     @api.onchange('product_id')
#     def product_id_change(self):
#         res = super(SaleOrderLine, self).product_id_change()
#         vals = {'value': {}}
# 
#         #THANH: Get standard price
#         product = self.product_id
#         from_cur = self.env.user.company_id.currency_id
#         purchase_price = product.standard_price
#         to_uom = self.product_uom.id
#         if to_uom != product.uom_id.id:
#             purchase_price = self.env['product.uom']._compute_price(self.env.cr, self.env.user, product.uom_id.id, purchase_price, to_uom)
# #         self._context.update({'date': self.order_id.date_order})
#         purchase_price = self.order_id.pricelist_id.currency_id.round(from_cur.compute(purchase_price, self.order_id.pricelist_id.currency_id))
#         vals['value'].update({'purchase_price': purchase_price})
#         #THANH: Get standard price
#         
#         self.update(vals)
#         return res
    
    @api.multi
    @api.onchange('price_unit')
    def onchange_price_unit(self):
        vals = {}
        if (100 + self.mark_up):
            purchase_price = round(self.price_unit * 100 / (100 + self.mark_up),3)
            vals.update({'purchase_price': purchase_price})
        self.update(vals)
        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.one
    @api.depends('enterprise_tax', 'order_line.price_unit', 'order_line.purchase_price', 'order_line.product_uom_qty')
    def _product_margin(self):
        for sale in self:
            sale.margin = 0.0
            sale.gross_profit = 0.0
                
            sale_amount = 0.0
            cost_amount = 0.0
            for line in sale.order_line:
                sale_amount += line.price_subtotal#(line.price_unit * line.product_uom_qty * (100.0-line.discount) /100.0)
                line_cost_amount = (line.purchase_price * line.product_uom_qty)
                if not line.purchase_price and line.product_id:
                    line_cost_amount = (line.product_id.standard_price * line.product_uom_qty)
                cost_amount += line_cost_amount
                
            if sale_amount:
                amount_enterprise_tax = 0.0
                amount_commission = 0.0
                if sale.commission_type == 'fix':
                    amount_commission = sale.commission_fix_amount
                    amount_enterprise_tax = sale.commission_fix_amount * sale.enterprise_tax /100
                if sale.commission_type == 'percentage':
                    amount_commission = sale.commission_amount
                    amount_enterprise_tax = sale.commission_amount * sale.enterprise_tax /100
                    
#                 real_sale_amount = (sale_amount - sale.amount_commission - amount_enterprise_tax)
                gross_profit = (sale_amount - cost_amount - amount_commission - amount_enterprise_tax)
                sale.gross_profit = gross_profit
                margin = 0.0
                if not cost_amount:
                    margin = 100.0
                else:
                    margin = round(gross_profit * 100/cost_amount, 3)
                sale.margin = margin
    
    @api.one
    @api.depends('minimum_margin', 'margin')
    def _can_be_sold(self):
        for sale in self:
            sale.can_be_sold = (sale.margin > sale.minimum_margin) and True or False
    
    @api.one
    @api.depends('minimum_margin', 'order_line.purchase_price', 'order_line.product_uom_qty')
    def _get_minimum_amount(self):
        for sale in self:
            cost_amount = 0.0
            for line in sale.order_line:
                line_cost_amount = line.purchase_price * line.product_uom_qty
                if not line.purchase_price and line.product_id:
                    line_cost_amount = line.product_id.standard_price * line.product_uom_qty
                cost_amount += line_cost_amount
            self.minimum_total_amount = (1-sale.minimum_margin/100) and round(cost_amount/(1-sale.minimum_margin/100),3)
    
    def _get_minimum_margin(self, cr, uid, *args):
        user_pool = self.pool.get('res.users')
        sale_team_pool = self.pool.get('crm.case.section')
        minimum_margin = user_pool.browse(cr, uid, uid).minimum_margin or 0.0
        cr.execute('SELECT section_id FROM sale_member_rel WHERE member_id=%s',(uid,))
        res = cr.fetchall()
        if res:
            sale_team_id = res[0][0]
            minimum_margin = sale_team_pool.browse(cr, uid, sale_team_id).minimum_margin or 0.0
        return minimum_margin
    
    minimum_margin = fields.Float(string='Min Margin (%)', digits=(16,2), readonly=True, states={'draft': [('readonly', False)]})
    minimum_total_amount = fields.Float(compute='_get_minimum_amount', string='Cost Amount', digits=(16,2), readonly=True)
    can_be_sold = fields.Boolean(compute='_can_be_sold', string='Can be sold', readonly=True)
    margin = fields.Float(compute='_product_margin', string='Margin (%)')
    gross_profit = fields.Float(compute='_product_margin', string='Gross Profit')
    
#        'net_profit': fields.function(_product_margin, string='Net Profit', 
##                                      store={
##                'sale.order.line': (_get_order, ['mark_up','margin'], 20),
##                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line','order_line_detail','amount_commission','enterprise_tax'], 20),
##                }, store=False, multi='profit'),

    order_line_detail = fields.One2many('sale.order.line', 'order_id', string='Order Line Detail', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})

    #Thanh: Add Amount Commission and Modify Store field
    enterprise_tax = fields.Float(string='Enterprise tax (%)', digits=(16,2), readonly=True, states={'draft': [('readonly', False)]}, default=25)
    
#     _defaults = {
#         'minimum_margin': _get_minimum_margin,
#     }
    
    @api.multi
    def _check_enterprise_tax(self):
        for data in self:
            if data.enterprise_tax > 100 or data.enterprise_tax < 0:
                return False
        return True
    
    _constraints = [
        (_check_enterprise_tax, 'Enterprise Tax must be greater than 0 and smaller than 100 !!!', []),

    ]
    
    @api.multi
    def action_confirm(self):
        for order in self:
            if not order.can_be_sold or order.can_be_sold == False:
                raise UserError(_('You cannot confirm a sale order which Margin is under Minimum Margin.'))
        super(SaleOrder, self).action_confirm()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
