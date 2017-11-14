DELETE FROM res_groups_wizard_rel WHERE 
	(uid in (select max(id) from ir_act_wizard WHERE name='CSV Sales Report' AND wiz_name='report.ecco.sale.order.wizard')) 
	AND (gid IN (SELECT max(id) FROM res_groups WHERE name='Empty Group'));
