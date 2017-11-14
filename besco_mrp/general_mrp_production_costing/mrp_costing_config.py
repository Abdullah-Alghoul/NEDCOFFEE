# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from datetime import datetime
import time

DATE_FORMAT = "%Y-%m-%d"

class MrpAccountConfig(models.Model):
    _name= 'mrp.account.config'
    _description = 'MRP Account Configuration'
    
    company_id = fields.Many2one('res.company', 'Company', required=True)
    active = fields.Boolean('Active', required=True,default=True)
    
    #Thanh: Group Direct Control
    direct_material_account_ids = fields.Many2many('account.account', 'direct_material_account_rel', 'config_id', 'account_id',string= 'Direct Material Accounts')
    direct_labour_account_ids = fields.Many2many('account.account', 'direct_labour_account_rel', 'config_id', 'account_id', string='Direct Labour Accounts')
    
    #Thanh: Group Factory Overhead Control
    indirect_material_account_ids = fields.Many2many('account.account', 'indirect_material_account_rel', 'config_id', 'account_id',string= 'Indirect Material Accounts')
    indirect_labour_account_ids = fields.Many2many('account.account', 'indirect_labour_account_rel', 'config_id', 'account_id',string= 'Indirect Labour Accounts')
    factory_utilities_account_ids = fields.Many2many('account.account', 'factory_utilities_account_rel', 'config_id', 'account_id',string= 'Factory Utilities Accounts')
    factory_depreciation_account_ids = fields.Many2many('account.account', 'factory_depreciation_account_rel', 'config_id', 'account_id',string= 'Factory Depreciation Accounts')
    other_indirect_account_ids = fields.Many2many('account.account', 'other_indirect_account_rel', 'config_id', 'account_id',string= 'Other Indirect Accounts')
    
