UPDATE account_account SET accttype='asset'WHERE id in (SELECT id FROM account_account where code like '1%' OR code like '2%');
UPDATE account_account SET accttype='liability'WHERE id in (SELECT id FROM account_account where code like '3%');
UPDATE account_account SET accttype='equity'WHERE id in (SELECT id FROM account_account where code like '4%');
UPDATE account_account SET accttype='income'WHERE id in (SELECT id FROM account_account where code like '5%' OR code like '7%' OR code like '9%');
UPDATE account_account SET accttype='expense'WHERE id in (SELECT id FROM account_account where code like '6%' OR code like '8%');
