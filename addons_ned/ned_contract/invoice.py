
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountInvoice(models.Model):
    _inherit = "account.invoice" 

    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.invoice_line_ids:
                total_qty +=line.quantity
            order.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty', string = 'Total Qty', digits=(12, 2))