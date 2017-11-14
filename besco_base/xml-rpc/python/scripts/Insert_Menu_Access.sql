
INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Fiscal Years' and m1.parent_id = m2.id and m2.name = 'Periods' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Periods' and m1.parent_id = m2.id and m2.name = 'Periods' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'List of Accounts' and m1.parent_id = m2.id and m2.name = 'Financial Accounts' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Chart of Accounts' and m1.parent_id = m2.id and m2.name = 'Financial Accounts' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Account Subtypes (user-defined)' and m1.parent_id = m2.id and m2.name = 'Financial Accounts' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Financial Journals' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Taxes' and m1.parent_id = m2.id and m2.name = 'Taxes' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Tax codes' and m1.parent_id = m2.id and m2.name = 'Taxes' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Account Templates' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Chart of Accounts Templates' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Generate Chart of Accounts from a Chart Template' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Tax Templates' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Tax Code Templates' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Fiscal Position Templates' and m1.parent_id = m2.id and m2.name = 'Templates' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Fiscal Positions' and m2.parent_id = m3.id and m3.name = 'Financial Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Analytic Accounts' and m2.parent_id = m3.id and m3.name = 'Analytic Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Analytic Chart of Accounts' and m1.parent_id = m2.id and m2.name = 'Analytic Accounts' and m2.parent_id = m3.id and m3.name = 'Analytic Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'New Analytic Account' and m1.parent_id = m2.id and m2.name = 'Analytic Accounts' and m2.parent_id = m3.id and m3.name = 'Analytic Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Analytic Journal Definition' and m2.parent_id = m3.id and m3.name = 'Analytic Accounting'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Payment Terms'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Currencies'
		and m3.parent_id = m4.id and m4.name = 'Configuration' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries Encoding by Line'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries Encoding by Line'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft statements' and m2.parent_id = m3.id and m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft statements' and m2.parent_id = m3.id and m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Statement' and m2.parent_id = m3.id and m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Statement' and m2.parent_id = m3.id and m3.name = 'Entries by Statements'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries Encoding by Move'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Entries Encoding by Move'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Entries Encoding by Line' and m2.parent_id = m3.id and m3.name = 'Analytic Entries'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Entries Encoding by Line' and m2.parent_id = m3.id and m3.name = 'Analytic Entries'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Analytic Entries by Journal' and m2.parent_id = m3.id and m3.name = 'Analytic Entries'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Analytic Entries by Journal' and m2.parent_id = m3.id and m3.name = 'Analytic Entries'
		and m3.parent_id = m4.id and m4.name = 'Entries Encoding' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Automatic reconciliation' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Automatic reconciliation' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Reconcile entries' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Reconcile entries' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unreconcile entries' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unreconcile entries' and m2.parent_id = m3.id and m3.name = 'Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Validate Account Moves'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Validate Account Moves'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Statements reconciliation' and m2.parent_id = m3.id and m3.name = 'Bank Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Statements reconciliation' and m2.parent_id = m3.id and m3.name = 'Bank Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Bank reconciliation' and m2.parent_id = m3.id and m3.name = 'Bank Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Bank reconciliation' and m2.parent_id = m3.id and m3.name = 'Bank Reconciliation'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close a Period' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close a Period' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Generate Fiscal Year Opening Entries' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Generate Fiscal Year Opening Entries' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Cancel Opening Entries' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Cancel Opening Entries' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close a Fiscal Year' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close a Fiscal Year' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close Periods' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Close Periods' and m2.parent_id = m3.id and m3.name = 'End of Year Treatments'
		and m3.parent_id = m4.id and m4.name = 'Periodical Processing' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Chart of Accounts'
		and m3.parent_id = m4.id and m4.name = 'Charts' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Chart of Accounts'
		and m3.parent_id = m4.id and m4.name = 'Charts' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Analytic Chart of Accounts'
		and m3.parent_id = m4.id and m4.name = 'Charts' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Analytic Chart of Accounts'
		and m3.parent_id = m4.id and m4.name = 'Charts' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Aged Partner Balance' and m2.parent_id = m3.id and m3.name = 'Partner Accounts'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Partner Balance' and m2.parent_id = m3.id and m3.name = 'Partner Accounts'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Partner Ledger' and m2.parent_id = m3.id and m3.name = 'Partner Accounts'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Entries' and m2.parent_id = m3.id and m3.name = 'Search Entries'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Entry Lines' and m2.parent_id = m3.id and m3.name = 'Search Entries'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Journals'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Analytic Chart of Accounts' and m2.parent_id = m3.id and m3.name = 'Analytic'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Print Analytic Journals' and m2.parent_id = m3.id and m3.name = 'Analytic'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');
	

INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Account cost and revenue by journal' and m1.parent_id = m2.id and m2.name = 'All Months' and m2.parent_id = m3.id and m3.name = 'Analytic'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m1.id FROM ir_ui_menu m1, ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m1.name = 'Account cost and revenue by journal (This Month)' and m1.parent_id = m2.id and m2.name = 'This Month' and m2.parent_id = m3.id and m3.name = 'Analytic'
		and m3.parent_id = m4.id and m4.name = 'Reporting' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Customer Invoice' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Customer Invoice' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Customer Invoices' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Customer Invoices' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Customer Invoices' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Customer Invoices' and m2.parent_id = m3.id and m3.name = 'Customer Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Supplier Invoice' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Supplier Invoice' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Supplier Invoices' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Supplier Invoices' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Supplier Invoices' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Supplier Invoices' and m2.parent_id = m3.id and m3.name = 'Supplier Invoices'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Customer Refund' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Customer Refund' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Customer Refunds' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Customer Refunds' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Customer Refunds' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Customer Refunds' and m2.parent_id = m3.id and m3.name = 'Customer Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m3.id FROM ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Supplier Refund' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'New Supplier Refund' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Supplier Refunds' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Draft Supplier Refunds' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Supplier Refunds' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Manager');


INSERT INTO ir_ui_menu_group_rel
SELECT (SELECT m2.id FROM ir_ui_menu m2, ir_ui_menu m3, ir_ui_menu m4, ir_ui_menu m5
	WHERE m2.name = 'Unpaid Supplier Refunds' and m2.parent_id = m3.id and m3.name = 'Supplier Refunds'
		and m3.parent_id = m4.id and m4.name = 'Invoices' and m4.parent_id = m5.id and m5.name = 'Financial Management' and m5.parent_id is null),
	(SELECT id FROM res_groups WHERE name = 'Finance / Accountant');
