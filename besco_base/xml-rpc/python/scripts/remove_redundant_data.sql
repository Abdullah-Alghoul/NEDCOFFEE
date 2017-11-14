DELETE FROM account_move_line WHERE move_id in (SELECT move_id FROM trobz_common_payment_request);
DELETE FROM account_move WHERE id in (SELECT move_id FROM trobz_common_payment_request);
DELETE FROM trobz_common_payment_request_line;
DELETE FROM trobz_common_payment_request;
DELETE FROM trobz_common_payment_type WHERE name in ('Import Duty Voucher','VAT Voucher');
