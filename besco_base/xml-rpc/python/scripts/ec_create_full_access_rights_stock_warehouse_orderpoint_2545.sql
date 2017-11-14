INSERT INTO ir_model_access(model_id, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'stock.warehouse.orderpoint' LIMIT 1), 
	TRUE,
	'Full Access For Everyone stock.warehouse.orderpoint',
	TRUE,
	TRUE,
	TRUE,
	NULL
WHERE NOT EXISTS (
	SELECT 1
	FROM ir_model_access
	WHERE model_id IN (SELECT id FROM ir_model WHERE model = 'stock.warehouse.orderpoint') AND
		perm_read = TRUE AND
		name = 'Full Access For Everyone stock.warehouse.orderpoint' AND
		perm_unlink = TRUE AND
		perm_write = TRUE AND
		perm_create = TRUE AND
		group_id IS NULL
);