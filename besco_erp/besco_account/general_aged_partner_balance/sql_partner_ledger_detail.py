# -*- coding: utf-8 -*-
import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class sql_partner_ledger_detail(osv.osv):
    _name = "sql.partner.ledger.detail"
    _auto = False
    
    def get_line(self, cr, uid, start_date, end_date, journal_ids, account_ids, showdetail, partner_ids, company_id, second_currency_id, report=False):
        sql = ''
        filter_am_journal_ids = ''
        if len(journal_ids):
            filter_am_journal_ids += ' and am.journal_id in (%(journal_ids)s)'%({'journal_ids':journal_ids,})

        filter_aml_account_ids = ''
        list_aml_account_ids = ''
        if len(account_ids):
            filter_aml_account_ids += ' and aml.account_id in (%(account_id)s)'%({'account_id':account_ids})
            list_aml_account_ids += ' (%(account_id)s)'%({'account_id':account_ids})
        
        filter_aml_extend_payment = ''
        if report.extend_payment == 'advance':
            filter_aml_extend_payment += " and aml.extend_payment = 'advance'"
        if report.extend_payment == 'payment':
            filter_aml_extend_payment += " and aml.extend_payment != 'advance'"
              
        filter_aml2_account_ids = ''
        if len(account_ids):
            filter_aml2_account_ids += ' and aml2.account_id not in (%(account_id)s)'%({'account_id':account_ids})
        
        #THANH: change second_currency_id into 0 when it is null to prevent sql condition
        if not second_currency_id:
            second_currency_id = 'null'
        
        for partner_id in partner_ids:
            if partner_id != 'null':
                filter_aml_partner_id = ' and aml.partner_id=%s'%(partner_id)
            else:
                filter_aml_partner_id = ' and aml.partner_id is null'
            if showdetail:
                if len(account_ids):
                    #THANH: show report general ledger (VD: ACC 1121 and CP: 6421, 1331)
                    sql_details = _('''
                        /* Lay cac move line co balance nho hon dong co debit or credit == maximum trong cung account.move */
                        select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, aih.date_due as date_due, coalesce(am.ref,am.name) doc_no, 
                        coalesce(aih.comment, coalesce(aml2.name, am.narration)) description,
                        (select acc.code 
                            from account_account acc
                            where acc.id=aml.account_id) acc_code,
                        acc.code cp_acc_code,
                        aml2.credit dr_amount, aml2.debit cr_amount,
                        aml2.second_ex_rate::numeric,
                        
                        case when (aml2.currency_id = %(second_currency_id)s and aml2.credit != 0) then abs(aml2.amount_currency)::numeric
                            else case when aml2.credit != 0 then (aml2.credit * aml2.second_ex_rate)::numeric 
                                else 0.0::numeric
                                end 
                            end dr_second_amount,
                            
                        case when (aml2.currency_id = %(second_currency_id)s and aml2.debit != 0) then abs(aml2.amount_currency)::numeric
                            else case when aml2.debit != 0 then (aml2.debit * aml2.second_ex_rate)::numeric 
                                else 0.0::numeric
                                end 
                            end cr_second_amount,
                        
                        am.partner_id
                            
                        from account_move_line aml2
                                LEFT JOIN account_move am on aml2.move_id=am.id
                                    and am.company_id= %(company_id)s
                                    and am.state = 'posted'
                                    and date(am.date) between '%(start_date)s' and '%(end_date)s'
                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                LEFT JOIN account_invoice aih on aml2.move_id = aih.move_id -- lien ket voi invoice
                                --left join account_voucher avh on aml.move_id = avh.move_id -- lien ket thu/chi
                                LEFT JOIN account_account acc ON aml2.account_id=acc.id
                            JOIN account_move_line aml on aml2.move_id = aml.move_id
                        where 
                            1=1
                            %(filter_aml2_account_ids)s
                            %(filter_aml_account_ids)s 
                            %(filter_aml_extend_payment)s
                            %(filter_am_journal_ids)s
                            %(filter_aml_partner_id)s
                            and abs(aml.balance) = (select max(abs(aml3.balance)) from account_move_line aml3 where aml3.move_id=aml2.move_id limit 1)
                    ''')
                else:
                    sql_details = _('''
                    /* Lay cac move line co balance nho hon dong co debit or credit == maximum trong cung account.move */
                    select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, aih.date_due as date_due, coalesce(am.ref,am.name) doc_no, 
                    coalesce(aih.comment, coalesce(aml.name, am.narration)) description,
                    acc.code acc_code,
                    array_to_string(ARRAY(SELECT DISTINCT a.code
                                      FROM account_move_line m2
                                      LEFT JOIN account_account a ON (m2.account_id=a.id)
                                      WHERE m2.move_id = aml.move_id
                                      AND m2.account_id not in (aml.account_id)), ', ') AS cp_acc_code,
                    
                    aml.debit dr_amount, aml.credit cr_amount,
                    aml.second_ex_rate::numeric,
                    
                    case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                        else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                            else 0.0::numeric
                            end 
                        end dr_second_amount,
                        
                    case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                        else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                            else 0.0::numeric
                            end 
                        end cr_second_amount,
                    
                    am.partner_id
                        
                    from account_move_line aml
                            LEFT JOIN account_move am on aml.move_id=am.id
                                and am.company_id= %(company_id)s
                                %(filter_aml_partner_id)s
                                and am.state = 'posted'
                                and date(am.date) between '%(start_date)s' and '%(end_date)s'
                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                            LEFT JOIN account_invoice aih on aml.move_id = aih.move_id -- lien ket voi invoice, get due date
                            --left join account_voucher avh on aml.move_id = avh.move_id -- lien ket thu/chi
                            LEFT JOIN account_account acc ON aml.account_id=acc.id
                    where 
                        1=1
                        %(filter_aml_account_ids)s  %(filter_aml_extend_payment)s 
                        %(filter_am_journal_ids)s
                        and abs(aml.balance) = (select max(abs(aml2.balance)) from account_move_line aml2 where aml2.move_id=aml.move_id limit 1)
                    ''')
                sql_details = sql_details%({
                      'start_date': start_date,
                      'end_date': end_date,
                      'filter_am_journal_ids': filter_am_journal_ids,
                      'filter_aml2_account_ids': filter_aml2_account_ids,
                      'filter_aml_account_ids': filter_aml_account_ids,
                      'filter_aml_partner_id':filter_aml_partner_id,
                      'company_id': company_id,
                      'com_currency_id': report.company_id.currency_id.id,
                      'second_currency_id': second_currency_id,
                      'balance_id': report.id,
                      'filter_aml_extend_payment': filter_aml_extend_payment,
                      })
                
                sql = _('''
                INSERT INTO report_partner_ledger_detail (create_uid, create_date, write_uid, write_date,
                    balance_id, seq, gl_date, doc_date, date_due, doc_no, description, acc_code, cp_acc_code, debit, credit,
                    debit_second, credit_second, second_ex_rate, partner_id, com_currency_id, second_currency_id)
                    
                    SELECT %(uid)s, current_timestamp, %(uid)s, current_timestamp,
                            %(balance_id)s, seq, gl_date, doc_date, date_due, doc_no, description, acc_code, cp_acc_code,
                            nullif(dr_amount,0) debit, nullif(cr_amount,0) credit,
                            nullif(dr_second_amount,0) dr_second_amount, nullif(cr_second_amount,0) cr_second_amount,
                            second_ex_rate,
                            partner_id, %(com_currency_id)s, %(second_currency_id)s
                    FROM(
                            select 0 as seq, null::date as gl_date, null::date as doc_date, null::date as date_due,
                                (select name from res_partner where id=%(partner_id)s) as doc_no, 
                                'Số dư đầu kỳ'as description,
                                null::text as acc_code, null::text as cp_acc_code,
                                case when dr_amount > cr_amount then dr_amount - cr_amount
                                    else null end dr_amount,
                                case when dr_amount < cr_amount then  cr_amount - dr_amount
                                    else null end cr_amount,
                                0::numeric second_ex_rate,
                                case when dr_second_amount > cr_second_amount then (dr_second_amount - cr_second_amount)::numeric
                                    else null end dr_second_amount,
                                case when dr_second_amount < cr_second_amount then  (cr_second_amount - dr_second_amount)::numeric
                                    else null end cr_second_amount,
                                %(partner_id)s partner_id
                            from (
                                select sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                                    sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
                                from (
                                        select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                                            sum(case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(amount_currency)::numeric
                                                else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) dr_second_amount,
                                            
                                            sum(case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(amount_currency)::numeric
                                                else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) cr_second_amount
                                        
                                        from account_move_line aml
                                            LEFT JOIN account_move am on am.id = aml.move_id
                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                    %(filter_aml_account_ids)s
                                                    %(filter_am_journal_ids)s
                                                    and am.company_id= %(company_id)s
                                                    %(filter_aml_partner_id)s
                                                    %(filter_aml_extend_payment)s
                                                    and am.state = 'posted'
                                                    and am.date = coalesce((select am.date
                                                                from account_move_line aml3
                                                                    LEFT JOIN account_move am on am.id = aml3.move_id
                                                                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                        %(filter_am_journal_ids)s
                                                                        and am.company_id= %(company_id)s
                                                                        %(filter_aml_partner_id)s
                                                                        %(filter_aml_extend_payment)s
                                                                        and am.state = 'posted'
                                                                where am.date <= '%(end_date)s'::date and aml3.account_id=aml.account_id
                                                                order by am.date desc
                                                                limit 1),'2000-01-01')
                                                                
                                    union all
                                        select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                                            sum(case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(amount_currency)::numeric
                                                else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) dr_second_amount,
                                            
                                            sum(case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(amount_currency)::numeric
                                                else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) cr_second_amount
                                        
                                        from account_move_line aml
                                            LEFT JOIN account_move am on am.id = aml.move_id
                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                                    %(filter_aml_account_ids)s
                                                    %(filter_am_journal_ids)s
                                                    and am.company_id= %(company_id)s
                                                    %(filter_aml_partner_id)s
                                                    %(filter_aml_extend_payment)s
                                                    and am.state = 'posted'
                                                    and am.date between
                                                        coalesce((select am.date
                                                            from account_move_line aml3
                                                                LEFT JOIN account_move am on am.id = aml3.move_id
                                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                    %(filter_am_journal_ids)s
                                                                    and am.company_id= %(company_id)s
                                                                    %(filter_aml_partner_id)s
                                                                    %(filter_aml_extend_payment)s
                                                                    and am.state = 'posted'
                                                            where am.date <= '%(end_date)s'::date and aml3.account_id=aml.account_id
                                                            order by am.date desc
                                                            limit 1),'2000-01-01')
                                                        and ('%(start_date)s'::date - 1)::date
                                    )v
                                ) start_bal
                                
                        union all
                            /*    Lay phat sinh trong ky    */
                            select row_number() over(order by gl_date, doc_date, date_due, doc_no, dr_amount desc, acc_code, cp_acc_code)::int seq, 
                                gl_date, doc_date, date_due, doc_no, description, acc_code, cp_acc_code,
                                dr_amount, cr_amount,
                                second_ex_rate,
                                dr_second_amount, cr_second_amount,
                                partner_id
                            from
                                (
                                /* Lay dong co debit or credit nho hon dong maximum trong cung account.move */
                                    select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, aih.date_due as date_due, 
                                    coalesce(am.ref,am.name) doc_no, 
                                    coalesce(aih.comment, coalesce(aml.name, am.narration)) description,
                                    acc.code acc_code,
                                    (select acc.code 
                                        from account_move_line aml2 LEFT JOIN account_account acc ON aml2.account_id=acc.id
                                        where aml2.move_id=aml.move_id order by abs(aml2.balance) desc limit 1) cp_acc_code,
                                    
                                    aml.debit dr_amount, aml.credit cr_amount,
                                    aml.second_ex_rate::numeric,
                                    
                                    case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                                        else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                            else 0.0::numeric
                                            end 
                                        end dr_second_amount,
                                    
                                    case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                                        else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                            else 0.0::numeric
                                            end 
                                        end cr_second_amount,
                                    am.partner_id
                                        
                                    from account_move_line aml
                                        LEFT JOIN account_move am on aml.move_id=am.id
                                            and am.company_id= %(company_id)s
                                            %(filter_aml_partner_id)s
                                            %(filter_aml_extend_payment)s
                                            and am.state = 'posted'
                                            and date(am.date) between '%(start_date)s' and '%(end_date)s'
                                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                        LEFT JOIN account_invoice aih on aml.move_id = aih.move_id -- lien ket voi invoice
                                        --left join account_voucher avh on aml.move_id = avh.move_id -- lien ket thu/chi
                                        LEFT JOIN account_account acc ON aml.account_id=acc.id
                                    where 
                                        1=1
                                        %(filter_aml_account_ids)s 
                                        %(filter_am_journal_ids)s
                                        and abs(aml.balance) < (select abs(aml2.balance) from account_move_line aml2 where aml2.move_id=aml.move_id order by abs(aml2.balance) desc limit 1)
                                    
                                union all
                                    %(sql_details)s
                                
                                union all
                                /* Lay cac move line bu tru cong no */
                                select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, aih.date_due as date_due, coalesce(am.ref,am.name) doc_no, 
                                coalesce(aih.comment, coalesce(aml.name, am.narration)) description,
                                acc.code acc_code,
                                (select acc.code 
                                    from account_move_line aml2 LEFT JOIN account_account acc ON aml2.account_id=acc.id
                                    where aml2.move_id=aml.move_id and aml2.id!=aml.id limit 1) cp_acc_code,
                                    
                                aml.credit dr_amount, aml.debit cr_amount,
                                aml.second_ex_rate::numeric,
                                
                                case when (aml.currency_id = null and aml.debit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                    else 0.0::numeric
                                    end 
                                end dr_second_amount,
                                    
                                case when (aml.currency_id = null and aml.credit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                    else 0.0::numeric
                                    end 
                                end cr_second_amount,
                                am.partner_id
                                    
                                from account_move_line aml
                                    LEFT JOIN account_move am on aml.move_id=am.id
                                        and am.company_id= %(company_id)s
                                        %(filter_aml_partner_id)s
                                        %(filter_aml_extend_payment)s
                                        and am.state = 'posted'
                                        and date(am.date) between '%(start_date)s' and '%(end_date)s'
                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                    LEFT JOIN account_invoice aih on aml.move_id = aih.move_id -- lien ket voi invoice
                                    --left join account_voucher avh on aml.move_id = avh.move_id -- lien ket thu/chi
                                    LEFT JOIN account_account acc ON aml.account_id=acc.id
                                where 1=1
                                     %(filter_aml_account_ids)s 
                                     %(filter_am_journal_ids)s
                                     and (select acc.id from account_move_line aml2 LEFT JOIN account_account acc ON aml2.account_id=acc.id
                                        where aml2.move_id=aml.move_id and aml2.id!=aml.id limit 1) in %(list_aml_account_ids)s 
                                ) x
                            where x.acc_code != x.cp_acc_code --remove dong ma phat sinh chinh no (vd: Acc 112101 thanh toan cho HD co nhieu line)
                            
                        union all
                        /*    Add them dong sum detail    */
                            select 99998 as seq, 
                                null::date gl_date, null::date doc_date, null::date date_due,
                                null::character varying doc_no, 'Số phát sinh trong kỳ'::character varying description,
                                null::character varying acc_code,
                                null::character varying cp_acc_code,
                                sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                                0 second_ex_rate,
                                
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) dr_second_amount,
                                
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) cr_second_amount,
                                %(partner_id)s partner_id
                                    
                            from account_move_line aml
                                LEFT JOIN account_move am on aml.move_id=am.id 
                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation' 
                                    %(filter_aml_account_ids)s
                                    %(filter_am_journal_ids)s
                                    %(filter_aml_partner_id)s
                                    %(filter_aml_extend_payment)s
                                    and am.company_id= %(company_id)s
                                    and am.state = 'posted'
                                    and date(am.date) between '%(start_date)s' and '%(end_date)s'
                                
                        union all
                        /*    Lay so cuoi ky    */
                            select 99999 as seq, null::date as gl_date, null::date as doc_date, null::date date_due,
                                null::text as doc_no, 'Số dư cuối kỳ' as description,
                                null::text as acc_code, null::text as cp_acc_code,
                                case when dr_amount > cr_amount then dr_amount - cr_amount
                                    else null end dr_amount,
                                case when dr_amount < cr_amount then  cr_amount - dr_amount
                                    else null end cr_amount,
                                0::numeric second_ex_rate,
                                case when dr_second_amount > cr_second_amount then (dr_second_amount - cr_second_amount)::numeric
                                    else null end dr_second_amount,
                                case when dr_second_amount < cr_second_amount then  (cr_second_amount - dr_second_amount)::numeric
                                    else null end cr_second_amount,
                                %(partner_id)s partner_id
                            from (
                                select sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                                    sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
                                from (
                                    select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                                    sum(case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) dr_second_amount,
                                    sum(case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) cr_second_amount
                                    from account_move_line aml
                                        LEFT JOIN account_move am on am.id = aml.move_id and am.company_id = %(company_id)s
                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                            %(filter_aml_account_ids)s
                                            %(filter_am_journal_ids)s
                                            %(filter_aml_partner_id)s
                                            %(filter_aml_extend_payment)s
                                            and am.state = 'posted'
                                            and aml.date = coalesce((select am.date
                                                            from account_move_line aml3
                                                                LEFT JOIN account_move am on am.id = aml3.move_id
                                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                    %(filter_am_journal_ids)s
                                                                    and am.company_id= %(company_id)s
                                                                    %(filter_aml_partner_id)s
                                                                    %(filter_aml_extend_payment)s
                                                                    and am.state = 'posted'
                                                            where am.date <= '%(end_date)s'::date and aml3.account_id=aml.account_id
                                                            order by am.date desc
                                                            limit 1),'2000-01-01')
                                    union all
                                    select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                                    sum(case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then (aml.debit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) dr_second_amount,
                                    sum(case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then (aml.credit * aml.second_ex_rate)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) cr_second_amount
                                    from account_move_line aml
                                        LEFT JOIN account_move am on am.id = aml.move_id and am.company_id = %(company_id)s
                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                            %(filter_aml_account_ids)s
                                            %(filter_am_journal_ids)s
                                            %(filter_aml_partner_id)s
                                            %(filter_aml_extend_payment)s
                                            and am.state = 'posted'
                                            and aml.date between 
                                                coalesce((select am.date
                                                    from account_move_line aml3
                                                        LEFT JOIN account_move am on am.id = aml3.move_id
                                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                            %(filter_am_journal_ids)s
                                                            and am.company_id= %(company_id)s
                                                            %(filter_aml_partner_id)s
                                                            %(filter_aml_extend_payment)s
                                                            and am.state = 'posted'
                                                    where am.date <= '%(end_date)s'::date and aml3.account_id=aml.account_id
                                                    order by am.date desc
                                                    limit 1),'2000-01-01')
                                                and '%(end_date)s'::date
                                ) v 
                            ) end_bal)x;
                    
                    -- Them 1 dong khoan cach
                    INSERT INTO report_partner_ledger_detail (create_uid, create_date, write_uid, write_date,
                    balance_id, seq, gl_date, doc_date, doc_no, description, acc_code, cp_acc_code, debit, credit,
                    debit_second, credit_second, second_ex_rate, partner_id, com_currency_id, second_currency_id)
                    
                    SELECT %(uid)s, current_timestamp, %(uid)s, current_timestamp,
                            %(balance_id)s, 999999, null, null, null, null, null, null,
                            null as debit, null as credit,
                            null as dr_second_amount, null as cr_second_amount,
                            null as second_ex_rate, %(partner_id)s as partner_id, null, null
                    ''')
                sql = sql%({
                      'start_date': start_date,
                      'end_date': end_date,
                      'filter_am_journal_ids': filter_am_journal_ids,
                      'filter_aml2_account_ids': filter_aml2_account_ids,
                      'filter_aml_account_ids': filter_aml_account_ids,
                      'filter_aml_partner_id':filter_aml_partner_id,
                      'filter_aml_extend_payment': filter_aml_extend_payment,
                      'company_id': company_id,
                      'com_currency_id': report.company_id.currency_id.id,
                      'second_currency_id': second_currency_id,
                      'balance_id': report.id,
                      'sql_details': sql_details,
                      'uid': uid,
                      'partner_id': partner_id,
                      'list_aml_account_ids': list_aml_account_ids,
                      })
            cr.execute(sql)
        return True
    
    def init(self, cr):
        self.fin_report_partner_balance(cr)
        cr.commit()
        return True
    
    def fin_report_partner_balance(self, cr):
        sql = '''
        DROP FUNCTION fin_report_partner_balance(date,date,integer,integer,integer);
        
        CREATE OR REPLACE FUNCTION fin_report_partner_balance(date, date, integer, integer, integer)
          RETURNS TABLE(
            seq integer,
            partner_id integer,
            partner_code character varying(20),
            partner_name character varying(120),
            
            begin_dr numeric,
            begin_cr numeric,
            period_dr numeric,
            period_cr numeric,
            end_dr numeric,
            end_cr numeric,
            
            begin_dr_2nd numeric,
            begin_cr_2nd numeric,
            period_dr_2nd numeric,
            period_cr_2nd numeric,
            end_dr_2nd numeric,
            end_cr_2nd numeric) AS
            
        $BODY$
                DECLARE
                    rec_data    record;
                    line_no        int;
                    beg_amount    numeric;
                    end_amount    numeric;
                    beg_2nd_amount numeric;
                    end_2nd_amount numeric;
                BEGIN
                    line_no = 0;
                    if $4 <> 0 then
                        for rec_data in
                                select  vw.partner_id, vw.partner_code, vw.partner_name,
                                        sum(beg_dr) begin_dr, sum(beg_cr) begin_cr,
                                        sum(prd_dr) period_dr, sum(prd_cr) period_cr,
                                        
                                        sum(beg_dr_2nd) begin_dr_2nd, sum(beg_cr_2nd) begin_cr_2nd,
                                        sum(prd_dr_2nd) period_dr_2nd, sum(prd_cr_2nd) period_cr_2nd
                                from (
                                        /*    Lay so du dau ky    */
                                        select rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                sum(aml.debit) as beg_dr, sum(aml.credit) as beg_cr, 
                                                0 as prd_dr, 0 as prd_cr,
                                                
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_cr_2nd,
                                                0 as prd_dr_2nd, 0 as prd_cr_2nd
                                        from account_move_line aml 
                                            join account_move amh on amh.id = aml.move_id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                        where 
                                            amh.state = 'posted'
                                            and ajn.type = 'situation'
                                            and aml.account_id = $3
                                            and aml.partner_id = $4
                                            and amh.company_id = $5
                                            and aml.date = coalesce((select am.date
                                                            from account_move_line aml3
                                                                LEFT JOIN account_move am on am.id = aml3.move_id
                                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                    and am.company_id= $5
                                                                    and aml3.partner_id = $4
                                                                    and am.state = 'posted'
                                                            where am.date <= $2::date and aml3.account_id=aml.account_id
                                                            order by am.date desc
                                                            limit 1),'2000-01-01')
                                        group by rpt.id, rpt.ref, rpt.name
                                    union all
                                        select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                sum(aml.debit) as beg_dr, sum(aml.credit) as beg_cr, 
                                                0 as prd_dr, 0 as prd_cr,
                                                
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_cr_2nd,
                                                0 as prd_dr_2nd, 0 as prd_cr_2nd
                                                
                                        from account_move_line aml 
                                            join account_move amh on aml.move_id = amh.id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                            
                                        where 
                                            amh.state = 'posted'
                                            and ajn.type != 'situation'
                                            and aml.account_id = $3
                                            and aml.partner_id = $4
                                            and amh.company_id = $5
                                            and aml.date between
                                                    coalesce((select am.date
                                                        from account_move_line aml3
                                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                and am.company_id= $5
                                                                and aml3.partner_id = $4
                                                                and am.state = 'posted'
                                                        where am.date <= $2::date and aml3.account_id=aml.account_id
                                                        order by am.date desc
                                                        limit 1),'2000-01-01')
                                                and ($1::date - 1)::date
                                        group by rpt.id, rpt.ref, rpt.name
                                        
                                    union all
                                        /*    Lay phat sinh trong ky    */
                                        select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                0 as beg_dr, 0 as beg_cr,
                                                sum(aml.debit) as prd_dr, sum(aml.credit) as prd_cr,
                                                
                                                0 as beg_dr_2nd, 0 as beg_cr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) prd_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) prd_cr_2nd
                                                
                                        from account_move_line aml
                                            join account_move amh on aml.move_id = amh.id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                            
                                        where aml.date between $1 and $2
                                            and amh.state = 'posted'
                                            and ajn.type != 'situation'
                                            and aml.account_id = $3
                                            and aml.partner_id = $4
                                            and amh.company_id = $5
                                        group by rpt.id, rpt.ref, rpt.name
                                    ) vw
                                group by vw.partner_id, vw.partner_code, vw.partner_name
                                having sum(beg_dr) <> 0.0 or sum(beg_cr) <> 0.0 or sum(prd_dr) <> 0.0 or sum(prd_cr) <> 0.0
                                order by 1
                        loop
                            line_no = line_no + 1;
                            beg_amount = rec_data.begin_dr - rec_data.begin_cr;
                            end_amount = beg_amount + rec_data.period_dr - rec_data.period_cr;
                            
                            beg_2nd_amount = rec_data.begin_dr_2nd - rec_data.begin_cr_2nd;
                            end_2nd_amount = beg_2nd_amount + rec_data.period_dr_2nd - rec_data.period_cr_2nd;
                            
                            seq = line_no;
                            partner_id = rec_data.partner_id;
                            partner_code = rec_data.partner_code;
                            partner_name = rec_data.partner_name;
                            
                            if beg_amount >= 0 then
                                begin_dr = beg_amount;
                                begin_cr = 0;
                                
                                begin_dr_2nd = beg_2nd_amount;
                                begin_cr_2nd = 0;
                            else
                                begin_dr = 0;
                                begin_cr = -beg_amount;
                                
                                begin_dr_2nd = 0;
                                begin_cr_2nd = -beg_2nd_amount;
                            end if;
                            
                            period_dr = rec_data.period_dr;
                            period_cr = rec_data.period_cr;
                            
                            period_dr_2nd = rec_data.period_dr_2nd;
                            period_cr_2nd = rec_data.period_cr_2nd;
                            
                            if end_amount >= 0 then
                                end_dr = end_amount;
                                end_cr = 0;
                                
                                end_dr_2nd = end_2nd_amount;
                                end_cr_2nd = 0;
                            else
                                end_dr = 0;
                                end_cr = -end_amount;
                                
                                end_dr_2nd = 0;
                                end_cr_2nd = -end_2nd_amount;
                            end if;
                            RETURN NEXT;
                        end loop;
                    else
                        for rec_data in
                                select  vw.partner_id, vw.partner_code, vw.partner_name,
                                        sum(beg_dr) begin_dr, sum(beg_cr) begin_cr,
                                        sum(prd_dr) period_dr, sum(prd_cr) period_cr,
                                        
                                        sum(beg_dr_2nd) begin_dr_2nd, sum(beg_cr_2nd) begin_cr_2nd,
                                        sum(prd_dr_2nd) period_dr_2nd, sum(prd_cr_2nd) period_cr_2nd
                                from (
                                        /*    Lay so du dau ky    */
                                        select rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                sum(aml.debit) as beg_dr, sum(aml.credit) as beg_cr, 
                                                0 as prd_dr, 0 as prd_cr,
                                                
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_cr_2nd,
                                                0 as prd_dr_2nd, 0 as prd_cr_2nd
                                                
                                        from account_move_line aml 
                                            join account_move amh on amh.id = aml.move_id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            left join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                        where 
                                            amh.state = 'posted'
                                            and ajn.type = 'situation'
                                            and aml.account_id = $3
                                            and amh.company_id = $5
                                            and aml.date =
                                                    coalesce((select am.date
                                                        from account_move_line aml3
                                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                and am.company_id= $5
                                                                and am.state = 'posted'
                                                        where am.date <= $2::date and aml3.account_id=aml.account_id
                                                        order by am.date desc
                                                        limit 1),'2000-01-01')
                                        group by rpt.id, rpt.ref, rpt.name
                                    union all
                                        select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                sum(aml.debit) as beg_dr, sum(aml.credit) as beg_cr, 
                                                0 as prd_dr, 0 as prd_cr,
                                                
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) beg_cr_2nd,
                                                0 as prd_dr_2nd, 0 as prd_cr_2nd
                                                
                                        from account_move_line aml 
                                            join account_move amh on amh.id = aml.move_id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            left join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                        where 
                                            amh.state = 'posted'
                                            and ajn.type != 'situation'
                                            and aml.account_id = $3
                                            and amh.company_id = $5
                                            and aml.date between
                                                    coalesce((select am.date
                                                        from account_move_line aml3
                                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                and am.company_id= $5
                                                                and am.state = 'posted'
                                                        where am.date <= $2::date and aml3.account_id=aml.account_id
                                                        order by am.date desc
                                                        limit 1),'2000-01-01')
                                                and ($1::date - 1)::date
                                        group by rpt.id, rpt.ref, rpt.name
                                    union all
                                        /*    Lay phat sinh trong ky    */
                                        select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name,
                                                0 as beg_dr, 0 as beg_cr,
                                                sum(aml.debit) as prd_dr, sum(aml.credit) as prd_cr,
                                                
                                                0 as beg_dr_2nd, 0 as beg_cr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) prd_dr_2nd,
                                                sum(case when (aml.currency_id = com.second_currency_id and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                                else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                                    else 0.0::numeric
                                                    end 
                                                end) prd_cr_2nd
                                                
                                        from account_move_line aml 
                                            join account_move amh on amh.id = aml.move_id
                                            join account_journal ajn on amh.journal_id = ajn.id
                                            left join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                            join res_company com on com.id = amh.company_id
                                        where aml.date between $1 and $2
                                            and amh.state = 'posted'
                                            and ajn.type != 'situation'
                                            and aml.account_id = $3
                                            and amh.company_id = $5
                                        group by rpt.id, rpt.ref, rpt.name
                                    ) vw
                                group by vw.partner_id, vw.partner_code, vw.partner_name
                                having sum(beg_dr) <> 0.0 or sum(beg_cr) <> 0.0 or sum(prd_dr) <> 0.0 or sum(prd_cr) <> 0.0
                                order by 1
                        loop
                            line_no = line_no + 1;
                            beg_amount = rec_data.begin_dr - rec_data.begin_cr;
                            end_amount = beg_amount + rec_data.period_dr - rec_data.period_cr;
                            
                            beg_2nd_amount = rec_data.begin_dr_2nd - rec_data.begin_cr_2nd;
                            end_2nd_amount = beg_2nd_amount + rec_data.period_dr_2nd - rec_data.period_cr_2nd;
                            
                            seq = line_no;
                            partner_id = rec_data.partner_id;
                            partner_code = rec_data.partner_code;
                            partner_name = rec_data.partner_name;
                            
                            if beg_amount >= 0 then
                                begin_dr = beg_amount;
                                begin_cr = 0;
                                
                                begin_dr_2nd = beg_2nd_amount;
                                begin_cr_2nd = 0;
                            else
                                begin_dr = 0;
                                begin_cr = -beg_amount;
                                
                                begin_dr_2nd = 0;
                                begin_cr_2nd = -beg_2nd_amount;
                            end if;
                            
                            period_dr = rec_data.period_dr;
                            period_cr = rec_data.period_cr;
                            period_dr_2nd = rec_data.period_dr_2nd;
                            period_cr_2nd = rec_data.period_cr_2nd;
                            
                            if end_amount >= 0 then
                                end_dr = end_amount;
                                end_cr = 0;
                                
                                end_dr_2nd = end_2nd_amount;
                                end_cr_2nd = 0;
                            else
                                end_dr = 0;
                                end_cr = -end_amount;
                                
                                end_dr_2nd = 0;
                                end_cr_2nd = -end_2nd_amount;
                            end if;
                            
                            RETURN NEXT;
                        end loop;
                    end if;
                    
                    return;
                END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
        ALTER FUNCTION fin_report_partner_balance(date, date, integer, integer, integer)
          OWNER TO odoo;
        '''
        cr.execute(sql)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
