# -*- coding: utf-8 -*-
from openerp import api, fields, models

class AccountAccountType(models.Model):
    _name = "account.account.type"
    _inherit = "account.account.type"
    
    #THANH: add type income and expenses
    type = fields.Selection([
        ('other', 'Regular'),
        ('receivable', 'Receivable'),
        ('payable', 'Payable'),
        ('liquidity', 'Liquidity'),
        ('income', 'Income'),
        ('expenses', 'Expenses'),
    ], required=True, default='other',
        help="The 'Internal Type' is used for features available on "\
        "different types of accounts: liquidity type is for cash or bank accounts"\
        ", payable/receivable is for vendor/customer accounts.")
