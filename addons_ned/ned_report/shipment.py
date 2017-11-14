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

class SalesShipments(models.Model):
    _name = 'v.shipment'
    _description = 'Sales Shipments'
    _auto =False
    # _order = "district,partner_code"

    s_contract = fields.Char(string = 'S Contract')
    customer = fields.Char(string = 'Customer')
    ship_by = fields.Char(string = 'Ship by')
    si_number = fields.Char(string = 'SI No.')

    product = fields.Char(string = 'Product')
    si_quantity = fields.Float(string = 'SI Qty.', digits=(12, 0))
    packing = fields.Char(string = 'Packing')
    shipment_date = fields.Date(string = 'Shipment date')
    fumigation_type = fields.Char(string = 'Fumigation')
    fumigation_date = fields.Date(string = 'Fumi. date')
    pss_condition = fields.Char(string = 'PSS', digits=(12, 0))
    # nvp_total_received = fields.Float(string = 'Total Received (Ton)', digits=(12, 0))
    pss_send_schedule = fields.Date(string = 'PSS sending schedule')
    factory_etd = fields.Date(string = 'Factory ETD')
    materialstatus = fields.Char(string = 'Material status')
    production_status = fields.Char(string = 'Prod. status')
    pss_count = fields.Integer(string = 'PSS Count')
    nvs_allocated = fields.Float(string = 'NVS allocated', digits=(12, 0))
    do_quantity = fields.Float(string = 'DO Qty.', digits=(12, 0))
    gdn_quantity = fields.Float(string = 'GDN Qty', digits=(12, 0))
    priority = fields.Char(string="Priority")
    status = fields.Char(string="Status")
    week_num_year = fields.Float(string="Week num", digits=(12, 0))
    prod_complete_date = fields.Date(string="Est. Prod. complete")
    closing_time = fields.Datetime(string="Closing time")
    production_progress = fields.Float(string='Prod. progress', digits=(12, 0))