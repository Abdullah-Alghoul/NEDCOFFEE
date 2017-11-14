UPDATE ir_model_access SET create_date = current_date WHERE create_date IS NULL;
UPDATE ir_model_access SET create_uid = 1 WHERE create_uid IS NULL;
DELETE FROM ir_model_access WHERE name in ('trobz.ec.sale.quotation','trobz.ec.quotation.line') and group_id in (SELECT id FROM res_groups WHERE name in ('Sale / Salesman','Sale / Manager', 'Super User'));

INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.sale.quotation' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.sale.quotation',
	FALSE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Sale / Manager')
;
INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.quotation.line' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.quotation.line',
	FALSE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Sale / Manager')
;
INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.sale.quotation' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.sale.quotation',
	FALSE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Sale / Salesman')
;
INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.quotation.line' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.quotation.line',
	FALSE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Sale / Salesman')
;

INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.sale.quotation' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.sale.quotation',
	TRUE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Super User')
;

INSERT INTO ir_model_access(model_id, create_date, perm_read, name, perm_unlink, perm_write, perm_create, group_id)
SELECT 	(SELECT id FROM ir_model WHERE model = 'trobz.ec.quotation.line' LIMIT 1),
	current_date,
	TRUE,
	'trobz.ec.quotation.line',
	TRUE,
	TRUE,
	TRUE,
	(SELECT id FROM res_groups WHERE name = 'Super User')
;
