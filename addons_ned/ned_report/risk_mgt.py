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

class SupplierRiskManagement(models.Model):
    _name = 'v.supplier.risk.management'
    _description = 'Supplier Risk Management'
    _auto =False
    _order = "district,partner_code"

    partner_code = fields.Char(string = 'Code')
    supplier_name = fields.Char(string = 'Name')
    district = fields.Char(string = 'District')
    goods = fields.Char(string = 'Type')

    projected_to_purchase = fields.Float(string = 'Project to Purchase (Ton)', digits=(12, 0))
    rep_person_1 = fields.Char(string = 'Res. 1', digits=(12, 0))
    rep_person_2 = fields.Char(string = 'Res. 2', digits=(12, 0))
    estimated_annual_volume = fields.Float(string = 'Est. Annual Vlm. (Ton)', digits=(12, 0))
    delivery_at = fields.Char(string = 'Delivery at')
    status = fields.Boolean(string = 'Active')
    total_booked = fields.Float(string = 'Total Booked (Ton)', digits=(12, 0))
    nvp_total_received = fields.Float(string = 'Total Received (Ton)', digits=(12, 0))
    nvp_receivable = fields.Float(string = 'NVP To-Receive (Ton)', digits=(12, 0))
    m2m = fields.Float(string = 'M2M (Mil.)', digits=(12, 0))
    npe_received_unfixed = fields.Float(string = 'NPE Received unfixed (Ton)', digits=(12, 0))
    retained_value = fields.Float(string = 'Retained Value (Mil.)', digits=(12, 0))
    total_m2m = fields.Float(string = 'Ttl. Mark2Market (Mil.)', digits=(12, 0))
    negative_m2m = fields.Float(string = 'Negative M2M (Mil.)', digits=(12, 0))
    purchase_undelivered_limit = fields.Float(string = 'Purchase Undl. Lmt. (Ton)', digits=(12, 0))
    negative_m2m_loss_limit = fields.Float(string = 'Ngt. M2M Loss Lmt. (Mil.)', digits=(12, 0))
    property_evaluation = fields.Float(string = 'Prop. Evaluation (Mil.)', digits=(12, 0))
    purchase_undelivered_limit = fields.Float(string = 'Purchase Undl. Lmt. (Ton)', digits=(12, 0))
    buying_room_qty = fields.Float(string = 'Buying Room - Qty. (Ton)', digits=(12, 0))
    npe_open_advance = fields.Float(string = 'NPE Open Advance (Mil.)', digits=(12, 0))
    buying_room_amount = fields.Float(string = 'Buying Room - Amt. (Mil.)', digits=(12, 0))
    m2m_loss_limit = fields.Float(string = 'Buying Room - Amt. (Mil.)', digits=(12, 0))


  #   def init(self, cr):
  #   	tools.drop_view_if_exists(cr, 'v_supplier_risk_management')
  #    	cr.execute("""
		# 	CREATE OR REPLACE VIEW public.v_supplier_risk_management AS
  #                SELECT 
  #                   row_number() OVER () AS id,
  #                   rp.partner_code,
  #                   COALESCE(rp.shortname, rp.name) AS supplier_name,
  #                   res_dt.name AS district,
  #                   mgt.goods,
  #                   mgt.ppkg/1000 AS projected_to_purchase,
  #                   mgt.repperson1 AS rep_person_1,
  #                   mgt.repperson2 AS rep_person_2,
  #                   mgt.estimated_annual_volume/1000 as estimated_annual_volume,
  #                   mgt.delivery_at,
  #                   coalesce(rp.active, False) AS status,
  #                   COALESCE(nvp.total_booked, 0::numeric)/1000 AS total_booked,
  #                   COALESCE(nvp.total_received, 0)/1000 AS nvp_total_received,
  #                   case when COALESCE(nvp.receivable, 0) < 0 then 0 

  #                       else COALESCE(nvp.receivable, 0)/1000 end AS nvp_receivable,
  #                   COALESCE(nvp.m2m)/1000000 AS m2m,
  #                   COALESCE(npe.received_unfixed, 0)/1000 AS npe_received_unfixed,
  #                   (COALESCE(npe.received_unfixed, 0) * 0.4)::double precision * get_latest_price()/1000000 AS retained_value,
  #                   COALESCE(mgt.deposited, 0::double precision)/1000000 AS deposited,
  #                   (COALESCE(nvp.m2m, 0) + (COALESCE(npe.received_unfixed, 0) * 0.4)::double precision * get_latest_price())/1000000 AS total_m2m,
  #                   case when COALESCE(mgt.deposited, 0::double precision) + COALESCE(nvp.m2m)/100000 > 0 then 0
  #                       else COALESCE(mgt.deposited, 0::double precision) + COALESCE(nvp.m2m)/100000 end AS negative_m2m,
  #                   COALESCE(mgt.purchase_undelivered_limit, 0::double precision)/1000 AS purchase_undelivered_limit,
  #                   COALESCE(mgt.negative_m2m_loss_limit, 0::double precision)/1000000 AS negative_m2m_loss_limit,
  #                   COALESCE(mgt.property_evaluation, 0::double precision)/1000000 AS property_evaluation,
  #                   (COALESCE(mgt.purchase_undelivered_limit, 0::double precision) - 
  #                       case when COALESCE(nvp.receivable, 0) < 0 then 0 else COALESCE(nvp.receivable, 0)/1000 end + 
  #                       COALESCE(npe.received_unfixed, 0)::double precision)/1000 AS buying_room_qty,
  #                   (COALESCE(npe.open_refund, 0::numeric)::double precision)/1000000 as npe_open_advance,
  #                   (COALESCE(mgt.negative_m2m_loss_limit, 0::double precision) + 
  #                       COALESCE(nvp.m2m, 0) + COALESCE(npe.received_unfixed, 0) * 0.4 * get_latest_price())/1000000 AS buying_room_amount
  #                   FROM res_partner rp
  #                       LEFT JOIN ( SELECT supplier_mgt.id,
  #                           supplier_mgt.type_ned,
  #                           supplier_mgt.create_uid,
  #                           supplier_mgt.ppkg,
  #                           supplier_mgt.property_evaluation,
  #                           supplier_mgt.create_date,
  #                           supplier_mgt.purchase_undelivered_limit,
  #                           supplier_mgt.repperson2,
  #                           supplier_mgt.write_uid,
  #                           supplier_mgt.goods,
  #                           supplier_mgt.partnert_id,
  #                           supplier_mgt.write_date,
  #                           supplier_mgt.estimated_annual_volume,
  #                           supplier_mgt.negative_m2m_loss_limit,
  #                           supplier_mgt.repperson1,
  #                           supplier_mgt.m2mlimit,
  #                           supplier_mgt.delivery_at,
  #                           supplier_mgt.date,
  #                           supplier_mgt.deposited
  #                           FROM supplier_mgt
  #                           WHERE (supplier_mgt.id IN ( SELECT max(supplier_mgt_1.id) AS max
  #                                   FROM supplier_mgt supplier_mgt_1
  #                                   GROUP BY supplier_mgt_1.partnert_id))) mgt ON rp.id = mgt.partnert_id
  #                   LEFT JOIN ( SELECT sum(vnvp.contract_qty) AS total_booked,
  #                           vnvp.partner_id,
  #                           sum(vnvp.total_received) AS total_received,
  #                           sum(vnvp.m2m) AS m2m,
  #                           sum(vnvp.receivable_qty) AS receivable
  #                          FROM v_ls_nvp_position vnvp
  #                          WHERE vnvp.date_order >= '2016-10-01'
  #                         GROUP BY vnvp.partner_id) nvp ON rp.id = nvp.partner_id
  #                    LEFT JOIN ( SELECT v_ls_npe_position.partner_id,
  #                           sum(v_ls_npe_position.receivable_qty) AS receivable,
  #                           sum(v_ls_npe_position.received_unfixed) AS received_unfixed,
  #                           sum(v_ls_npe_position.total_paid) AS total_advanced,
  #                           sum(v_ls_npe_position.open_refund) AS open_refund
  #                          FROM v_ls_npe_position
  #                         GROUP BY v_ls_npe_position.partner_id) npe ON rp.id = npe.partner_id
  #                    LEFT JOIN ( SELECT res_district.name,
  #                           res_district.id
  #                          FROM res_district) res_dt ON rp.district_id = res_dt.id
  #                 WHERE rp.company_type::text = 'company'::text AND rp.supplier = true AND rp.customer = false AND rp.employee = false AND rp.partner_code IS NOT NULL;
  #               ;
		# """)