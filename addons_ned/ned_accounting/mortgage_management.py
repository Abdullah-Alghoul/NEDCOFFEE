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

# class MortgageAllocation(models.Model):
#     _inherit = "mortgage.allocation"
#     
#     
#     mortgage_id = fields.Many2one('mortgage.management.line', string='Mortgage')
#     selling_id = fields.Many2one('mortgage.management.line', string='Mortgage')
#     product_qty = fields.Float(string="Product qty")
    
class MortgageManagement(models.Model):
    _name = "mortgage.management"
    _order = 'id desc'
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    @api.multi
    def button_dummy(self):
        return True
    
    @api.depends('mortgage_line_ids','mortgage_line_ids.price_subtotal','financing_rate','amount')
    def _amount_all(self):
        for mortgage in self:
            amount_total = 0.0
            for line in mortgage.mortgage_line_ids:
                amount_total += line.price_subtotal
            
            amount_total = (amount_total * mortgage.financing_rate) /100
                
            mortgage.update({
                'amount_total': amount_total,
                'amount_remain':amount_total - mortgage.amount
            })
    
    
    @api.multi
    def action_approve(self):
        self.state = 'approved'
        if self.type == 'force_selling':
            return
        return True
    
    name = fields.Char(string='Name', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'), ('done', 'Done'), ('cancel', 'Cancelled')],
             string='Status', readonly= True, copy=False, index=True, default='draft')
    type = fields.Selection([('mortgage', 'mortgage'), ('force_selling', 'Force selling')], string='Type', required=True, readonly=True)
    type_pk = fields.Selection([('product', 'Thế chấp bằng hàng hóa'), 
                            ('debt_collection_rights', 'Quyền thu nợ'),('money','thế chấp bằng USD')], string='Type', required=True, default='product')
    date = fields.Date(string='Date', readonly=True, index= True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    validity_date = fields.Date(string='Validity Date', required=True, readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    bank_id = fields.Many2one('res.bank', string='Bank', readonly=True, copy=False, states={'draft': [('readonly', False)]})
    notes = fields.Text('Mortgage and conditions')
    maturity = fields.Integer(string="Maturity")
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    mortgage_line_ids = fields.One2many('mortgage.management.line','mortgage_id',string="Mortgage Line")
    financing_rate =fields.Float(string="Financing rate %",default = 100)
    debit_limit = fields.Float(string="Debit Limit")
    amount = fields.Monetary(string='Loan Amount', track_visibility='always')
    amount_remain = fields.Monetary(string='Amount Remain', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    
    
    
    
    
    
    
class MortgageManagementLine(models.Model):
    _name = "mortgage.management.line"
    _order = 'id desc'
    
#     
    @api.depends('product_qty', 'price_unit')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * line.product_qty
            line.update({
                'price_subtotal': price,
            })
#     
#     
#     def compute_fifo(self):
#         for order in self:
#             price_out_fifo = fifo_qty_out = fifo_qty = 0.0
#             
#             for fifo in order.fifo_ids:
#                 fifo_qty += fifo.product_qty
#             
#             for fifo in order.fifo_out_ids:
#                 fifo_qty_out += fifo.out_qty
#                 price_out_fifo += fifo.out_qty * fifo.fifo_id.price_unit
#                 
#             if order.product_uom_qty == fifo_qty:
#                 order.fifo = True
#             else:
#                 order.fifo = False
#             
#             if order.product_uom_qty == fifo_qty_out:
#                 order.fifo_out = True
#             else:
#                 order.fifo_out = False
#             
#             order.fifo_qty = fifo_qty
#             order.unfifo_qty = order.product_uom_qty - fifo_qty
            
            
            
#     mortgage_fifo_ids = fields.One2many('mortgage.management.line','mortgage_id', string='FIFO', required=False)
#     selling_fifo_ids = fields.One2many('mortgage.management.line','selling_id', string='FIFO', required=False)
#     fifo = fields.Boolean(string='Allocated',compute="compute_fifo", default=False,store= False)
#     
#     fifo_qty = fields.Float(string='Fifo Qty',compute="compute_fifo", default=False,store= False)
#     unfifo_qty = fields.Float(string='UnFifo Qty',compute="compute_fifo", default=False,store= False)
    
    
            
    name = fields.Char(string='Description', required=True, copy=True)
    product_qty = fields.Float(string="Quantity")
    price_unit = fields.Float(string="Price Unit")
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    mortgage_id = fields.Many2one("mortgage.management", string="Mortgage")
    currency_id = fields.Many2one("res.currency",related='mortgage_id.currency_id', string="Currency")
    date = fields.Date(related='mortgage_id.date', string="Date")
    
    
    
    