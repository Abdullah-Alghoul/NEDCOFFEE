# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang



class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    
    acc_dr_id= fields.Many2one('account.account',string="Account Debit", domain=[('type','<>','view')])
    acc_cr_id= fields.Many2one('account.account',string="Account Credit", domain=[('type','<>','view')])
    
    