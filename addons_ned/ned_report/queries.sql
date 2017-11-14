-- View: public.v_shipment

-- DROP VIEW public.v_shipment;

CREATE OR REPLACE VIEW public.v_shipment AS
 SELECT row_number() OVER () AS id,
    sc.name AS s_contract,
    rp.name AS customer,
    sc.status AS ship_by,
    si.name AS si_number,
    pp.default_code AS product,
    sil.product_qty AS si_quantity,
    np.name AS packing,
    si.shipment_date,
    nf.name AS fumigation_type,
    si.fumigation_date,
    si.pss_condition,
    si.pss_send_schedule,
    si.factory_etd,
    si.materialstatus,
    si.production_status,
    pm.pss_count,
    COALESCE(sum(nvsl.product_qty), 0::numeric) AS nvs_allocated,
    COALESCE(sum(deli.do_quantity), 0::numeric) AS do_quantity,
    COALESCE(sum(deli.gdn_quantity), 0::numeric) AS gdn_quantity,
    si.priority_by_month AS priority,
        CASE
            WHEN COALESCE(sum(deli.gdn_quantity), 0::numeric) = COALESCE(sil.product_qty, 0::numeric) OR (sil.product_qty - sum(deli.gdn_quantity)) < 60::numeric THEN 'Done'::text
            WHEN COALESCE(sum(nvsl.product_qty), 0::numeric) = 0::numeric THEN 'Unallocated'::text
            WHEN COALESCE(sum(deli.do_quantity), 0::numeric) > COALESCE(sum(deli.gdn_quantity), 0::numeric) THEN 'Waiting GDN'::text
            ELSE NULL::text
        END AS status,
    week_num_year(si.factory_etd) AS week_num_year,
    si.prodcompleted as prod_complete_date
   FROM s_contract sc
     JOIN res_partner rp ON rp.id = sc.partner_id
     LEFT JOIN shipping_instruction si ON sc.id = si.contract_id
     LEFT JOIN shipping_instruction_line sil ON si.id = sil.shipping_id
     JOIN product_product pp ON pp.id = sil.product_id
     LEFT JOIN ned_packing np ON np.id = sil.packing_id
     LEFT JOIN ned_fumigation nf ON si.fumigation_id = nf.id
     LEFT JOIN ( SELECT pm_1.shipping_id,
            count(pm_1.shipping_id) AS pss_count
           FROM pss_management pm_1
          GROUP BY pm_1.shipping_id) pm ON si.id = pm.shipping_id
     LEFT JOIN sale_contract nvs ON si.id = nvs.shipping_id
     LEFT JOIN sale_contract_line nvsl ON nvs.id = nvsl.contract_id
     LEFT JOIN ( SELECT dor.contract_id,
            sum(dol.product_qty) AS do_quantity,
            sum(sm.gdn_quantity) AS gdn_quantity
           FROM delivery_order dor
             JOIN delivery_order_line dol ON dor.id = dol.delivery_id
             LEFT JOIN stock_picking sp ON dor.picking_id = sp.id
             LEFT JOIN ( SELECT stock_move.picking_id,
                    sum(stock_move.product_uom_qty) AS gdn_quantity
                   FROM stock_move
                  GROUP BY stock_move.picking_id) sm ON dor.picking_id = sm.picking_id
          GROUP BY dor.contract_id) deli ON nvs.id = deli.contract_id
  GROUP BY sc.name, rp.name, sc.status, si.name, pp.default_code, sil.product_qty, np.name, si.shipment_date, nf.name, si.fumigation_date, si.pss_condition, si.pss_send_schedule, si.factory_etd, si.materialstatus, si.production_status, pm.shipping_id, pm.pss_count, si.priority_by_month,si.prodcompleted;

