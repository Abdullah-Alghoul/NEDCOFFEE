# -*- coding: utf-8 -*-

import json
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models, _
from openerp.tools import float_is_zero
from openerp.tools.misc import formatLang

from openerp.exceptions import UserError, RedirectWarning, ValidationError

import openerp.addons.decimal_precision as dp

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    account_analytic_id =  fields.Many2one('account.analytic.account','Account Analytic')

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
