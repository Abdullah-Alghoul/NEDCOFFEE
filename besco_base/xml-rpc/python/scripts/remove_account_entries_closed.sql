DELETE FROM account_move_line WHERE move_id in (select move_id FROM account_invoice);
DELETE FROM account_move WHERE id in (select move_id FROM account_invoice);
