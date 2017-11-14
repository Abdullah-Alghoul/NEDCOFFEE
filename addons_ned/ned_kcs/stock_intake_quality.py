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

class StockIntakeQuality(models.Model):
    _name = 'v.qc.details'
    _description = 'Stock Intake Quality'
    _auto =False

    zone = fields.Char(string = 'Zone')
    stack = fields.Char(string = 'Stack')
    balance_basis = fields.Float(string = 'Balance', digits=(12, 0))
    receipt_note = fields.Char(string = 'Receipt Note')

    receiving_date = fields.Date(string = 'Date')
    packing = fields.Char(string = 'Packing')
    mc = fields.Float(string = 'MC', digits=(12, 2))
    fm = fields.Float(string = 'FM', digits=(12, 2))
    black = fields.Float(string = 'Bl.', digits=(12, 2))
    broken = fields.Float(string = 'Brk.', digits=(12, 2))
    brown = fields.Float(string = 'Brw.', digits=(12, 2))
    mold = fields.Float(string = 'Mol.', digits=(12, 2))
    cherry = fields.Float(string = 'Chr.', digits=(12, 2))
    excelsa = fields.Float(string = 'Ex.', digits=(12, 2))
    screen18 = fields.Float(string = 'Scr18', digits=(12, 2))
    screen16 = fields.Float(string = 'Scr16', digits=(12, 2))
    screen13 = fields.Float(string = 'Scr13', digits=(12, 2))
    belowsc12 = fields.Float(string = 'Bl-12', digits=(12, 2))
    burned = fields.Float(string = 'Burned', digits=(12, 2))
    eaten = fields.Float(string = 'Eaten', digits=(12, 2))
    immature = fields.Float(string = 'Imt.', digits=(12, 2))
    product = fields.Char(string='Product')
    receipt_qty = fields.Float(string="Receipt Qty.", digits=(12, 2))

  