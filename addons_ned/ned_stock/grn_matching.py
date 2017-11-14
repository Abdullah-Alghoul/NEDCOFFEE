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

class GRNMatching(models.Model):
	_name = "grn.matching"
	name = fields.Char(string='GRN Matching')
	grn_branch = fields.Many2one('stock.picking', string = 'GRN Branch')
	grn_factory = fields.Many2one('stock.picking', string = 'GRN Factory')
	matching_date = fields.Date()
