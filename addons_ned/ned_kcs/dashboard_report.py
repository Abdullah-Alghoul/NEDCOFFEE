
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

DATE_FORMAT = "%Y-%m-%d"

class ReportKcsGrn(models.Model):
    _name = "report.kcs.grn"
    _auto = False
    _description = "Report Kcs Grn"
    
    product_id = fields.Many2one('product.product',string="Product")
    mc = fields.Float(string="Mc",group_operator="avg",)
    fm = fields.Float(string="Fm",group_operator="avg",)
    black = fields.Float(string="Black",group_operator="avg",)
    broken = fields.Float(string="Broken",group_operator="avg",)
    brown = fields.Float(string="Brown",group_operator="avg",)
    years_tz = fields.Char(string="Years")
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_kcs_grn')
        cr.execute("""
            CREATE OR REPLACE VIEW report_kcs_grn AS (
             SELECT sp.id,
                sp.product_id,
                sum(total_qty) quantity,
                kcs.mc,
                fm,
                black,
                broken,
                brown,
                years_tz
            FROM  stock_picking sp                    
                    join request_kcs_line kcs on sp.id =kcs.picking_id
            WHERE date_done is not null
                and sp.state ='done'
            group by sp.id,sp.product_id,years_tz, kcs.mc,
                fm,
                black,
                Broken,
                brown,
                years_tz
            )""")
