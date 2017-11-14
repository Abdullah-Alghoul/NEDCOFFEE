# -*- coding: utf-8 -*-
from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp import fields, models
from openerp.tools.translate import _
from openerp.exceptions import UserError
from datetime import datetime, timedelta, date
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from docutils.nodes import document
import calendar
import datetime
from time import gmtime, strftime
DATE_FORMAT = "%Y-%m-%d"

class ProductionReport(models.Model):
    _name = 'v.grn.matching'
    _description = 'GRN Matching Report'
    _auto = False

    branch_id = fields.Char(sring = 'ID')
    grn_branch = fields.Char(sring = 'GRN Branch')
    branch_date_received = fields.Date(string = 'Branch Received Date')
    grn_factory = fields.Char(sring = 'GRN Factory')
    factory_date_received = fields.Date(string = 'Factory Received Date')
    deduction_branch = fields.Float(string = 'Deduction at Branch', digits=(12, 2), group_operator="avg")
    deduction_factory = fields.Float(string = 'Deduction at Factory', digits=(12, 2), group_operator="avg")
    brn_fac = fields.Float(string = 'Deduction Difference', digits=(12, 2), group_operator="avg")
    deficit = fields.Char(sring = 'Deficit')

    net_weight_branch = fields.Float(string = 'Net Weight Branch', digits=(12, 0))
    net_weight_factory = fields.Float(string = 'Net Weight Factory', digits=(12, 0))
    basis_weight_branch = fields.Float(string = 'Basis Weight Branch', digits=(12, 0))
    basis_weight_factory = fields.Float(string = 'Basis Weight Factory', digits=(12, 0))

    mc_branch = fields.Float(string = 'MC_%', digits=(12, 2))
    mc_factory = fields.Float(string = 'MC_%', digits=(12, 2))
    fm_branch = fields.Float(string = 'FM_%', digits=(12, 2))
    fm_factory = fields.Float(string = 'FM_%', digits=(12, 2))
    black_branch = fields.Float(string = 'Black_%', digits=(12, 2))
    black_factory = fields.Float(string = 'Black_%', digits=(12, 2))
    broken_branch = fields.Float(string = 'Broken_%', digits=(12, 2))
    broken_factory = fields.Float(string = 'Broken_%', digits=(12, 2))

    brown_branch = fields.Float(string = 'Brown_%', digits=(12, 2))
    brown_factory = fields.Float(string = 'Brown_%', digits=(12, 2))
    cherry_branch = fields.Float(string = 'Cherry_%', digits=(12, 2))
    cherry_factory = fields.Float(string = 'Cherry_%', digits=(12, 2))
    screen18_branch = fields.Float(string = 'Screen18_%', digits=(12, 2))
    screen18_factory = fields.Float(string = 'Screen18_%', digits=(12, 2))
    screen16_branch = fields.Float(string = 'Screen16_%', digits=(12, 2))
    screen16_factory = fields.Float(string = 'Screen16_%', digits=(12, 2))
    screen13_branch = fields.Float(string = 'Screen13_%', digits=(12, 2))
    screen13_factory = fields.Float(string = 'Screen13_%', digits=(12, 2))
    belowsc12_branch = fields.Float(string = 'Belowsc12_%', digits=(12, 2))
    belowsc12_factory = fields.Float(string = 'Belowsc12_%', digits=(12, 2))

    # mc_branch = fields.Float(string = 'MC Branch', digits=(12, 2))
    # mc_factory = fields.Float(string = 'MC Factory', digits=(12, 2))
    # fm_branch = fields.Float(string = 'FM Branch', digits=(12, 2))
    # fm_factory = fields.Float(string = 'FM Factory', digits=(12, 2))
    # black_branch = fields.Float(string = 'Black Branch', digits=(12, 2))
    # black_factory = fields.Float(string = 'Black Factory', digits=(12, 2))
    # broken_branch = fields.Float(string = 'Broken Branch', digits=(12, 2))
    # broken_factory = fields.Float(string = 'Broken Factory', digits=(12, 2))

    # brown_branch = fields.Float(string = 'Brown Branch', digits=(12, 2))
    # brown_factory = fields.Float(string = 'Brown Factory', digits=(12, 2))
    # cherry_branch = fields.Float(string = 'Cherry Branch', digits=(12, 2))
    # cherry_factory = fields.Float(string = 'Cherry Factory', digits=(12, 2))
    # screen18_branch = fields.Float(string = 'Screen18 Branch', digits=(12, 2))
    # screen18_factory = fields.Float(string = 'Screen18 Factory', digits=(12, 2))
    # screen16_branch = fields.Float(string = 'Screen16 Branch', digits=(12, 2))
    # screen16_factory = fields.Float(string = 'Screen16 Factory', digits=(12, 2))
    # screen13_branch = fields.Float(string = 'Screen13 Branch', digits=(12, 2))
    # screen13_factory = fields.Float(string = 'Screen13 Factory', digits=(12, 2))
    # belowsc12_branch = fields.Float(string = 'Belowsc12 Branch', digits=(12, 2))
    # belowsc12_factory = fields.Float(string = 'Belowsc12 Factory', digits=(12, 2))


