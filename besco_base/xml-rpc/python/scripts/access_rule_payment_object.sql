DELETE FROM ir_model_access 
WHERE (model_id IN (SELECT id FROM ir_model WHERE model = 'account.voucher'));
DELETE FROM ir_model_access 
WHERE (model_id IN (SELECT id FROM ir_model WHERE model = 'account.voucher.line'));

INSERT INTO ir_model_access(model_id, perm_read, "name", perm_unlink, perm_write, perm_create, group_id)
SELECT (SELECT id FROM ir_model WHERE model = 'account.voucher'), TRUE, 'Accounting Voucher', TRUE, TRUE, TRUE, (SELECT id FROM res_groups WHERE "name" = 'Employee EC');

INSERT INTO ir_model_access(model_id, perm_read, "name", perm_unlink, perm_write, perm_create, group_id)
SELECT (SELECT id FROM ir_model WHERE model = 'account.voucher.line'), TRUE, 'Accounting Voucher Line', TRUE, TRUE, TRUE, (SELECT id FROM res_groups WHERE "name" = 'Employee EC');


DELETE FROM ir_model_access 
WHERE (model_id IN (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.type'));
DELETE FROM ir_model_access 
WHERE (model_id IN (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.request'));
DELETE FROM ir_model_access 
WHERE (model_id IN (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.request.line'));

INSERT INTO ir_model_access(model_id, perm_read, "name", perm_unlink, perm_write, perm_create, group_id)
SELECT (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.type'), TRUE, 'Payment Type', TRUE, TRUE, TRUE, (SELECT id FROM res_groups WHERE "name" = 'Employee EC');

INSERT INTO ir_model_access(model_id, perm_read, "name", perm_unlink, perm_write, perm_create, group_id)
SELECT (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.request'), TRUE, 'Payment Request', TRUE, TRUE, TRUE, (SELECT id FROM res_groups WHERE "name" = 'Employee EC');

INSERT INTO ir_model_access(model_id, perm_read, "name", perm_unlink, perm_write, perm_create, group_id)
SELECT (SELECT id FROM ir_model WHERE model = 'trobz.common.payment.request.line'), TRUE, 'Payment Request Line', TRUE, TRUE, TRUE, (SELECT id FROM res_groups WHERE "name" = 'Employee EC');
UPDATE ir_model_access SET create_uid=1 WHERE create_uid is NULL;
UPDATE ir_model_access SET create_date=now() WHERE create_date is NULL;

