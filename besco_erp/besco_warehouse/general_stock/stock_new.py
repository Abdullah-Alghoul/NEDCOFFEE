# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

import time
import math
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    @api.depends('move_lines.product_uom_qty','move_lines','move_lines.product_qty')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.move_lines:
                total_qty +=line.product_qty
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty',store=True)
    
    categ_id = fields.Many2one(related='move_lines.product_id.categ_id',  string='Product Category',store = True)
    
    def get_datetime(self, date):
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y-%m-%d')
    
    def get_years(self, date):
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y')
    
    @api.depends('date_done')
    def _compute_date(self):
        for line in self:
            if line.date_done:
                line.day_tz = self.get_datetime(line.date_done)
                line.years_tz = self.get_years(line.date_done)
            else:
                line.day_tz = False
                line.years_tz =False
    
    day_tz = fields.Date(compute='_compute_date',string = "Day tz", store=True)
    years_tz = fields.Char(compute='_compute_date',string = "Years tz", store=True)

class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'
    @api.one
    def _get_moves(self):
        self.move_ids = self.quant_ids.mapped('history_ids')

    move_ids = fields.One2many('stock.move', compute='_get_moves')

