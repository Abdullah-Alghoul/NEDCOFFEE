DELETE FROM trobz_partner_company_rel;
INSERT INTO trobz_partner_company_rel(partner_id, company_id)
	SELECT 	rp.id, (SELECT max(id) FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hochiminh City') 
	FROM	res_partner rp
	WHERE (rp.name NOT ILIKE '%Europ Continents%') AND NOT EXISTS (
		SELECT 1
		FROM trobz_partner_company_rel
		WHERE partner_id = rp.id AND company_id IN (SELECT id FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hochiminh City') 
	);

INSERT INTO trobz_partner_company_rel(partner_id, company_id)
	SELECT 	rp.id, (SELECT max(id) FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hochiminh City') 
	FROM	res_partner rp
	WHERE (rp.name = 'Europ Continents Vietnam Co., Ltd - Hochiminh City') AND NOT EXISTS (
		SELECT 1
		FROM trobz_partner_company_rel
		WHERE partner_id = rp.id AND company_id IN (SELECT id FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hochiminh City') 
	);

INSERT INTO trobz_partner_company_rel(partner_id, company_id)
	SELECT 	rp.id, (SELECT max(id) FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hanoi') 
	FROM	res_partner rp
	WHERE (rp.name = 'Europ Continents Vietnam Co., Ltd - Hanoi') AND NOT EXISTS (
		SELECT 1
		FROM trobz_partner_company_rel
		WHERE partner_id = rp.id AND company_id IN (SELECT id FROM res_company WHERE name='Europ Continents Vietnam Co., Ltd - Hanoi') 
	);

UPDATE 	stock_production_lot
SET 	company_id = (
	SELECT id
	FROM res_company
	WHERE name IN ('Europ Continents Vietnam Co., Ltd - Hochiminh City')
	LIMIT 1
);

UPDATE 	purchase_order po
SET 	company_id = (
	SELECT company_id
	FROM trobz_partner_company_rel
	WHERE partner_id IN (
		SELECT partner_id
		FROM stock_warehouse
		WHERE id = po.warehouse_id
	)
	LIMIT 1
);

UPDATE 	stock_picking sp
SET	company_id = (
	SELECT company_id
	FROM purchase_order
	WHERE id = sp.purchase_id
)
WHERE	type = 'in' AND purchase_id IS NOT NULL;

UPDATE 	stock_picking sp
SET	company_id = (
	SELECT company_id
	FROM res_users
	WHERE id IN (
		SELECT user_id
		FROM sale_order
		WHERE id = sp.sale_id
	)
	LIMIT 1
)
WHERE	type = 'out' AND sale_id IS NOT NULL AND EXISTS (
	SELECT 1
	FROM sale_order
	WHERE id = sp.sale_id AND user_id IS NOT NULL
);

UPDATE 	stock_picking sp
SET	company_id = (
	SELECT company_id
	FROM res_users
	WHERE id IN (
		SELECT create_uid
		FROM sale_order
		WHERE id = sp.sale_id
	)
	LIMIT 1
)
WHERE	type = 'out' AND sale_id IS NOT NULL AND EXISTS (
	SELECT 1
	FROM sale_order
	WHERE id = sp.sale_id AND user_id IS NULL
);

UPDATE 	stock_picking sp
SET	company_id = (
	SELECT company_id 
	FROM res_users
	WHERE id = sp.create_uid
)
WHERE 	purchase_id IS NULL AND sale_id IS NULL;

UPDATE	stock_move sm
SET 	company_id = (
	SELECT company_id
	FROM stock_picking
	WHERE id = sm.picking_id
)
WHERE 	picking_id IS NOT NULL;

UPDATE 	stock_move sm
SET 	company_id = (
	SELECT company_id
	FROM stock_inventory
	WHERE id IN (SELECT inventory_id FROM stock_inventory_move_rel WHERE move_id = sm.id)
	LIMIT 1
)
WHERE picking_id IS NULL AND EXISTS (
	SELECT 1
	FROM stock_inventory_move_rel
	WHERE move_id = sm.id
);

UPDATE 	stock_move sm
SET	company_id = (
	SELECT company_id
	FROM res_users
	WHERE id IN (
		SELECT user_id
		FROM sale_order
		WHERE id IN (
			SELECT order_id
			FROM sale_order_line
			WHERE id = sm.sale_line_id 
		)
	)
	LIMIT 1
)
WHERE picking_id IS NULL AND sale_line_id IS NOT NULL AND EXISTS (
	SELECT 1
	FROM sale_order
	WHERE id IN (
		SELECT order_id
		FROM sale_order_line
		WHERE id = sm.sale_line_id
	) AND user_id IS NOT NULL
) AND NOT EXISTS (
	SELECT 1
	FROM stock_inventory_move_rel
	WHERE move_id = sm.id
);

UPDATE 	stock_move sm
SET	company_id = (
	SELECT company_id
	FROM res_users
	WHERE id IN (
		SELECT create_uid
		FROM sale_order
		WHERE id IN (
			SELECT order_id
			FROM sale_order_line
			WHERE id = sm.sale_line_id 
		)
	)
	LIMIT 1
)
WHERE picking_id IS NULL AND sale_line_id IS NOT NULL AND EXISTS (
	SELECT 1
	FROM sale_order
	WHERE id IN (
		SELECT order_id
		FROM sale_order_line
		WHERE id = sm.sale_line_id
	) AND user_id IS NULL
) AND NOT EXISTS (
	SELECT 1
	FROM stock_inventory_move_rel
	WHERE move_id = sm.id
);

UPDATE 	stock_move sm
SET	company_id = (
	SELECT company_id
	FROM purchase_order
	WHERE id IN (
		SELECT order_id
		FROM purchase_order_line
		WHERE id = sm.purchase_line_id
	)
	LIMIT 1
)
WHERE picking_id IS NULL AND purchase_line_id IS NOT NULL AND NOT EXISTS (
	SELECT 1
	FROM stock_inventory_move_rel
	WHERE move_id = sm.id
);

UPDATE 	stock_move sm
SET	company_id = (
	SELECT company_id 
	FROM res_users
	WHERE id = sm.create_uid
)
WHERE 	picking_id IS NULL AND purchase_line_id IS NULL AND sale_line_id IS NULL AND NOT EXISTS (
	SELECT 1
	FROM stock_inventory_move_rel
	WHERE move_id = sm.id
);

UPDATE 	account_move am
SET	company_id = (
	SELECT company_id
	FROM account_invoice
	WHERE move_id = am.id
);

UPDATE 	account_move_line aml
SET 	company_id = (
	SELECT company_id
	FROM account_move
	WHERE id = aml.move_id
);
