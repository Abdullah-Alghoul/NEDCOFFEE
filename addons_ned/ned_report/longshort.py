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

class LongShortV2(models.Model):
    _name = 'v.long.short.v2'
    _description = 'Long/Short Position'
    _auto =False

    def add_months(sourcedate, months):
        month = sourcedate.month - 1 + months
        year = int(sourcedate.year + month / 12 )
        month = month % 12 + 1
        day = min(sourcedate.day,calendar.monthrange(year,month)[1])
        return datetime.date(year,month,day)

    def get_month_year(sdate):
        to_date = sdate.strftime('%b %Y')
        return to_date

    a = datetime.datetime.now()


    prod_group = fields.Char(string = 'Prod. Group __________')
    product = fields.Char(string = 'Product Code __________')
    product_id = fields.Integer(string = 'Prod. ID __________')
    sitting_stock = fields.Float(string = 'Sitting Stock __________', digits=(12, 0))

    npe_received_unfixed = fields.Float(string = 'NPE Rec. Unfixed __________', digits=(12, 0))
    gross_ls = fields.Float(string = '  Gross Long/Short ___________', digits=(12, 0))
    nvp_receivable = fields.Float(string = 'Current - NVP Rec. __________', digits=(12, 0))
    unshipped_qty = fields.Float(string = 'Current - S Unsh. __________', digits=(12, 0))
    net_ls = fields.Float(string = 'Current Net L/S __________', digits=(12, 0))
    
    nvp_next1_receivable = fields.Float(string = get_month_year(add_months(a, 1)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next1_unshipped = fields.Float(string = get_month_year(add_months(a, 1)) + ' S Unsh. __________', digits=(12, 0))
    next1_net_ls = fields.Float(string = get_month_year(add_months(a, 1)) + ' L/S __________', digits=(12, 0))

    nvp_next2_receivable = fields.Float(string = get_month_year(add_months(a, 2)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next2_unshipped = fields.Float(string = get_month_year(add_months(a, 2)) + ' S Unsh. __________', digits=(12, 0))
    next2_net_ls = fields.Float(string = get_month_year(add_months(a, 2)) + ' L/S __________', digits=(12, 0))

    nvp_next3_receivable = fields.Float(string = get_month_year(add_months(a, 3)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next3_unshipped = fields.Float(string = get_month_year(add_months(a, 3)) + ' S Unsh. __________', digits=(12, 0))
    next3_net_ls = fields.Float(string = get_month_year(add_months(a, 3)) + ' L/S __________', digits=(12, 0))

    nvp_next4_receivable = fields.Float(string = get_month_year(add_months(a, 4)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next4_unshipped = fields.Float(string = get_month_year(add_months(a, 4)) + ' S Unsh. __________', digits=(12, 0))
    next4_net_ls = fields.Float(string = get_month_year(add_months(a, 4)) + ' L/S __________', digits=(12, 0))

    nvp_next5_receivable = fields.Float(string = get_month_year(add_months(a, 5)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next5_unshipped = fields.Float(string = get_month_year(add_months(a, 5)) + ' S Unsh. __________', digits=(12, 0))
    next5_net_ls = fields.Float(string = get_month_year(add_months(a, 5)) + ' L/S __________', digits=(12, 0))

    nvp_next6_receivable = fields.Float(string = get_month_year(add_months(a, 6)) + ' NVP Rec. __________', digits=(12, 0))
    sale_next6_unshipped = fields.Float(string = get_month_year(add_months(a, 6)) + ' S Unsh. __________', digits=(12, 0))
    next6_net_ls = fields.Float(string = get_month_year(add_months(a, 6)) + ' L/S __________', digits=(12, 0))

    def init(self, cr):
    	tools.drop_view_if_exists(cr, 'v_long_short_v2')
     	cr.execute("""
			CREATE OR REPLACE VIEW public.v_long_short_v2 AS
				SELECT 
				 	ROW_NUMBER() OVER() id,
				 	ctg.name as prod_group,
				    ls.*
				    from product_category ctg
					join product_template pt on ctg.id = pt.categ_id
				    join product_product pp on pt.id = pp.product_tmpl_id
				    join v_long_short ls on pp.id = ls.product_id
				where ctg.code  not in ('NLTH','DV')
				order by ctg.name;
		""")