# -*- coding: utf-8 -*-
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    
    #THANH: will be removed
    invoice_lines = fields.One2many('account.payment.invoice', 'asset_id', 
                                    string='Invoices', readonly=True)
