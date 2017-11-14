# -*- coding:utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import api, tools
from calendar import monthrange
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class hr_contract(osv.osv):
    _inherit = 'hr.contract'
    
    _columns = {    
        'contract_rule_input_ids': fields.one2many('rule.input.line', 'contract_id', string='Input Rules'),
        }
    
hr_contract()

