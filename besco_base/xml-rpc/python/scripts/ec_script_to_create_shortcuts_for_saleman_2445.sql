INSERT INTO ir_ui_view_sc(res_id, resource, "name", user_id)
SELECT  DISTINCT (SELECT id from ir_ui_menu where name = 'New Quotation'), 'ir.ui.menu', 'New Quotation',
	uid FROM res_groups_users_rel WHERE 
	gid = (SELECT id FROM res_groups WHERE name = 'Sale / Salesman')
		AND uid not in (SELECT user_id FROM ir_ui_view_sc WHERE
				res_id = (SELECT id FROM ir_ui_menu WHERE name='New Quotation'));
