# -*- coding: utf-8 -*-
import time
from datetime import date, datetime

from openerp.osv import expression
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    @api.multi
    @api.depends('line_ids.second_amount')
    def _second_amount_compute(self):
        for move in self:
            total = 0.0
            for line in move.line_ids:
                total += line.second_amount > 0 and line.second_amount or 0.0
            move.second_amount = total
            
    second_amount = fields.Monetary(compute='_second_amount_compute', store=True, currency_field='second_currency_id')
    second_currency_id = fields.Many2one(related='company_id.second_currency_id', store=True, string='2nd Currency', readonly=True, copy=False)
