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
    _name = 'v.production.report'
    _description = 'Production Report'
    _auto = False


    batch_no = fields.Char(string = 'Batch no.')
    bom_type = fields.Char(string = 'BOM')
    start_date = fields.Date(string = 'Start')
    stock_note = fields.Char(string = 'Picking')

    operation_type = fields.Char(string = 'Type')
    picking_date = fields.Date(string = 'Picking date')
    stack = fields.Char(string = 'Stack')
    product = fields.Char(string = 'Product')

    net_quantity = fields.Float(string = 'Net qty.', digits=(12, 0))
    basis_qty = fields.Float(string = 'Basis qty.', digits=(12, 0))

    mc = fields.Float(string = 'MC', digits=(12, 2), group_operator="avg")
    fm = fields.Float(string = 'FM', digits=(12, 2), group_operator="avg")
    black = fields.Float(string = 'Black', digits=(12, 2), group_operator="avg")
    broken = fields.Float(string = 'Broken', digits=(12, 2), group_operator="avg")
    brown = fields.Float(string = 'Brown', digits=(12, 2), group_operator="avg")
    mold = fields.Float(string = 'Moldy', digits=(12, 2), group_operator="avg")
    cherry = fields.Float(string = 'Cherry', digits=(12, 2), group_operator="avg")
    excelsa = fields.Float(string = 'Excelsa', digits=(12, 2), group_operator="avg")
    screen18 = fields.Float(string = 'Scr18', digits=(12, 2), group_operator="avg")
    screen16 = fields.Float(string = 'Scr16', digits=(12, 2), group_operator="avg")
    screen13 = fields.Float(string = 'Scr13', digits=(12, 2), group_operator="avg")
    screen12 = fields.Float(string = 'Scr12', digits=(12, 2), group_operator="avg")
    eaten = fields.Float(string = 'Eaten', digits=(12, 2), group_operator="avg")
    burn = fields.Float(string = 'Burned', digits=(12, 2), group_operator="avg")
    immature = fields.Float(string = 'Immature', digits=(12, 2), group_operator="avg")
    state = fields.Char(string = 'State')
    remarks = fields.Char(string = 'Remarks')

    # def init(self, cr):
    #     tools.drop_view_if_exists(cr, 'v_production_report')
    #     cr.execute("""
    #         CREATE or replace view v_production_report as
    #         SELECT row_number() OVER () AS id,
    #             mrp.name AS batch_no,
    #             bom.code AS bom_type,
    #             mrp.date_planned AS start_date,
    #             sp.name AS stock_note,
    #             case when spt.code = 'production_out' then 'IN' else 'OUT' end as operation_type,
    #             sp.date_done as picking_date,
    #             ss.name AS stack,
    #             pp.default_code AS product,
    #             (case when spt.code = 'production_out' then 1 else -1 end) * sm.product_uom_qty AS net_quantity,
    #             (case when spt.code = 'production_out' then 1 else -1 end) * sm.init_qty AS basis_qty,
    #             ss.mc,
    #             ss.fm,
    #             ss.black,
    #             ss.broken,
    #             ss.brown,
    #             ss.mold,
    #             ss.cherry,
    #             ss.excelsa,
    #             ss.screen18,
    #             ss.screen16,
    #             ss.screen13,
    #             ss.eaten,
    #             ss.burn,
    #             ss.immature,
    #             ss.screen12,
    #             sm.state
                
    #            FROM mrp_production mrp
    #              JOIN stock_picking sp ON mrp.id = sp.production_id
    #              JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
    #              JOIN stock_stack ss ON sp.stack_id = ss.id
    #              JOIN stock_move sm ON sp.id = sm.picking_id
    #              JOIN product_product pp ON sm.product_id = pp.id
    #              JOIN mrp_bom bom ON mrp.bom_id = bom.id
    #           WHERE spt.code::text in ('production_out'::text, 'production_in') AND sm.state::text in ('done'::text, 'cancelled')
              
    #           order by mrp.name, operation_type;
    #     """)