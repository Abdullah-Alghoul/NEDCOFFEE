
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

class ReportMrpGrp(models.Model):
    _name = "report.mrp.grp"
    _auto = False
    _description = "Report Mrp Grp"
    
    product_id = fields.Many2one('product.product',string="Product")
    categ_id = fields.Many2one('product.category',string="Category")
    quantity = fields.Integer(compute='_compute_date',string = "date", store=True)
    years_tz = fields.Char(compute='_compute_date',string = "Years", store=True)
    
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_mrp_grp')
        cr.execute("""
            CREATE OR REPLACE VIEW report_mrp_grp AS (
            SELECT sp.id,
                pt.categ_id ,
                product_id,sum(total_qty) quantity,
                years_tz
            FROM  stock_picking sp
                    join product_product pp on sp.product_id = pp.id
                    join product_template pt on pt.id = pp.product_tmpl_id
            WHERE picking_type_id = 6 
            and date_done is not null
                and sp.state ='done'
            group by sp.id,pt.categ_id,product_id,years_tz
            )""")
