create or replace view v_production_report as
SELECT row_number() OVER () AS id,
	mrp.name AS batch_no,
	bom.code AS bom_type,
    mrp.date_planned AS start_date,
    sp.name AS stock_note,
    case when spt.code = 'production_out' then 'IN' else 'OUT' end as operation_type,
    sp.date_done as picking_date,
    ss.name AS stack,
    pp.default_code AS product,
    (case when spt.code = 'production_out' then 1 else -1 end) * sm.product_uom_qty AS net_quantity,
    (case when spt.code = 'production_out' then 1 else -1 end) * sm.init_qty AS basis_qty,
    ss.mc,
    ss.fm,
    ss.black,
    ss.broken,
    ss.brown,
    ss.mold,
    ss.cherry,
    ss.excelsa,
    ss.screen18,
    ss.screen16,
    ss.screen13,
    ss.eaten,
    ss.burn,
    ss.immature,
    ss.screen12
    
   FROM mrp_production mrp
     JOIN stock_picking sp ON mrp.id = sp.production_id
     JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
     JOIN stock_stack ss ON sp.stack_id = ss.id
     JOIN stock_move sm ON sp.id = sm.picking_id
     JOIN product_product pp ON sm.product_id = pp.id
     JOIN mrp_bom bom ON mrp.bom_id = bom.id
  WHERE spt.code::text in ('production_out'::text, 'production_in') AND sm.state::text in ('done'::text, 'cancelled')
  
  order by mrp.name, operation_type;