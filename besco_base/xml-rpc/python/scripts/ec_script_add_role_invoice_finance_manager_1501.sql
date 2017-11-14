DELETE FROM res_roles_users_rel WHERE uid IN (SELECT u.id FROM res_users u JOIN res_groups_users_rel gr ON u.id=gr.uid JOIN res_groups g ON g.id=gr.gid WHERE g.name = 'Finance / Manager') AND rid IN (SELECT id FROM  res_roles WHERE name = 'Invoice');
INSERT INTO res_roles_users_rel(uid,rid)
SELECT DISTINCT u.id,(SELECT id FROM  res_roles WHERE name = 'Invoice') FROM res_users u JOIN res_groups_users_rel gr ON u.id=gr.uid JOIN res_groups g ON g.id=gr.gid WHERE g.name = 'Finance / Manager';
