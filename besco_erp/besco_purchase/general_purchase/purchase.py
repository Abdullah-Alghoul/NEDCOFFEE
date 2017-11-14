# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time
import math

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"
    
    
   
    
    
    @api.depends('order_line.price_total','currency_rate')
    def _currency_amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
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
            for line in order.order_line:
                total_qty +=line.product_qty
            order.total_qty = total_qty
            
    currency_order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines', readonly=True, copy=False)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, copy=False, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},)
    currency_currency_id = fields.Many2one(related='company_id.currency_id', store=True, string='Currency Company', readonly=True)
    currency_amount_tax = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Tax',store=True)
    currency_amount_untaxed = fields.Float(compute='_currency_amount_all',digits=(16,0) , string = 'Untaxed Amount',store=True)
    currency_amount_total = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Total',store=True)
    
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty')


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    
    def _currency_price_unit(self):
        for line in self:
            line.currency_price_unit = line.order_id.currency_rate and line.price_unit * line.order_id.currency_rate or line.price_unit
            price = line.price_unit 
            taxes = line.taxes_id.compute_all(price, line.order_id.currency_id, line.product_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.currency_price_subtotal = line.order_id.currency_rate and taxes['total_included'] * line.order_id.currency_rate or taxes['total_included']
        
    def _price_unit_include(self):
        partner_id = False
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
            
        tax_nxk_ids = []
        for line in self:
            partner_id = line.order_id.partner_id
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
                if self.order_id:
                    cur = line.order_id.currency_id
                    line.price_unit_include = cur_obj.round(self.cr, self.uid, cur, (line.price_unit_include/line.product_qty/line.product_qty) + line.price_unit)
                    line.currency_price_unit_include = line.order_id.currency_rate and line.price_unit_include * line.order_id.currency_rate or line.price_unit_include
        else:
            for line in self:
                line.price_unit_include = line.price_unit
                line.currency_price_unit_include = line.order_id.currency_rate and line.price_unit_include * line.order_id.currency_rate or line.price_unit_include

    
    
    currency_price_unit = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Price Unit')
    currency_price_subtotal = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Total')
    
    price_unit_include= fields.Monetary(compute='_price_unit_include', string='Price Include')
    currency_price_unit_include = fields.Monetary(compute='_price_unit_include' ,  string='Currency Price Include',)