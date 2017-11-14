# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time
import math

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.depends('order_line.price_total', 'commission_type', 'commission_percentage','commission_fix_amount')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        super(SaleOrder, self)._amount_all()
        for order in self:
            #Thanh: Compute with commission
            commission_amount = 0.0
            order.commission_amount = commission_amount
            if order.commission_type == 'percentage':
                commission_amount = round(order.commission_percentage * order.amount_total / 100, 0)
                order.commission_amount = commission_amount
                
#             if order.commission_type:
#                 if order.commission_type == 'percentage':
#                     order.amount_total = order.amount_total - commission_amount
#                 else:
#                     order.amount_total = order.amount_total - order.commission_fix_amount
                    
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
    
    total_qty = fields.Float(compute='_total_qty', digits=(16,2) , string = 'Total Qty')
    currency_currency_id = fields.Many2one(related='company_id.currency_id', store=True, string='Currency Company', readonly=True)
    currency_amount_tax = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Tax',store=True)
    currency_amount_untaxed = fields.Float(compute='_currency_amount_all',digits=(16,0) , string = 'Untaxed Amount',store=True)
    currency_amount_total = fields.Float(compute='_currency_amount_all',digits=(16,0) , string='Amount Total',store=True)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, copy=False, required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},)
    currency_order_line = fields.One2many('sale.order.line', 'order_id', string='Order Lines', readonly=True,copy=False)
    
    commission_type = fields.Selection([
        ('fix','Fixed Amount'),
        ('percentage','Percentage')], string='Commission Type', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    commission_fix_amount = fields.Monetary(string='Commission Amount', digits=(16,2), required=False, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    commission_percentage = fields.Float(string='Commission Percentage (%)', digits=(16,2), required=False, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    commission_amount = fields.Monetary(string='Commission Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
                
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
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
        

    currency_price_unit = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Price Unit')
    currency_price_subtotal = fields.Monetary(compute='_currency_price_unit',digits=(16,0),string='Total')
    
    price_unit_include= fields.Monetary(compute='_price_unit_include', string='Price Include')
    currency_price_unit_include = fields.Monetary(compute='_price_unit_include' ,  string='Currency Price Include',)
    
    
    