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

class VScontractV2(models.Model):
    _name = 'v.scontract.summary.v2'
    _description = 'S-Contract Report'
    _auto =False

    contract_no = fields.Char(string='S No.')
    customer = fields.Char(string='Customer')
    ship_by = fields.Char(string = 'Shipped by')
    s_date = fields.Date(string = 'Date')
    weight_condition = fields.Char(string = 'Weight condition')
    buyer_ref = fields.Char(string = 'Buyer ref.')
    shipment_date = fields.Date(string = 'Shipment date')
    pss = fields.Boolean(string = 'PSS')
    check_by_cont = fields.Boolean(string = 'Check by cont.?')
    product = fields.Char(string='Product')
    specs = fields.Char(string = 'Specs.')
    certificate = fields.Char(string = 'Certificate')
    quantity = fields.Float(string = 'Quantity', digits=(12, 0))
    si_quantity = fields.Float(string = 'SI quantity', digits=(12, 0))


   #  def init(self, cr):
   #  	tools.drop_view_if_exists(cr, 'v_scontract_summary_v2')
   #   	cr.execute("""
			# CREATE or replace view v_scontract_summary_v2 as
			# SELECT ROW_NUMBER() OVER() id, sc.name as contract_no,
			# 	rp.name as customer,
			#     sc.status as ship_by,
			#     sc.date as s_date,
			#     sc.weights as weight_condition,
			#     sc.buyer_ref,
			#     sc.shipment_date,
			#     sc.pss,
			#     sc.check_by_cont,
			#     pp.default_code as product,
			#     scl.name as specs,
			#     cert.name as certificate,
			#     scl.product_qty as quantity,
			#     coalesce(si.si_quantity, 0) as si_quantity
			    
			# from s_contract sc
			# 	join res_partner rp on sc.partner_id = rp.id
			#     join s_contract_line scl on sc.id = scl.contract_id
			#     join product_product pp on scl.product_id = pp.id
			#     left join ned_certificate cert on scl.certificate_id = cert.id
			#     left join ned_packing packing on scl.packing_id = packing.id
			#     left join (select
			#                	si.contract_id,
			#                	sum(sil.product_qty) as si_quantity
			#         	from shipping_instruction si
			#                join shipping_instruction_line sil on si.id = sil.shipping_id
			#             group by contract_id
			#         ) si on sc.id = si.contract_id
			#     ;
			#         """)
