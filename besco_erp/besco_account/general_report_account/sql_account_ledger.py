# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import _

class sql_account_ledger(osv.osv):
    _name = "sql.account.ledger"
    _auto = False
    
    def get_line(self, cr, uid, start_date, end_date, journal_ids, account_ids, cp_account_ids, cp2_account_ids, ex_account_ids, 
                 showdetail, partner_ids, company_id, second_currency_id, report=False):
        sql = ''
        filter_aml_partner_id = ''
        if partner_ids:
            filter_aml_partner_id += ' and aml.partner_id in (%(partner_ids)s)'%({'partner_ids':partner_ids,})
        filter_am_journal_ids = ''
        if len(journal_ids):
            filter_am_journal_ids += ' and am.journal_id in (%(journal_ids)s)'%({'journal_ids':journal_ids,})
        
        filter_aml_account_ids = ''
        if len(ex_account_ids):
            account_ids = tuple(set(account_ids) - set(ex_account_ids))
        if len(account_ids):
            filter_aml_account_ids += ' and aml.account_id in (%(account_id)s)'%({'account_id':account_ids})
        
        filter_aml_cp_account_ids = ''
        filter_aml2_cp_account_ids = ''
        if len(cp_account_ids):
            filter_aml_cp_account_ids += ''' and string_to_array(aml.counterpart_ids,',')::INT[] && string_to_array('%(cp_account_ids)s',',')::INT[]
                                        '''%({'cp_account_ids':cp_account_ids})
            filter_aml2_cp_account_ids += ''' and string_to_array(aml2.account_id::text,',')::INT[] && string_to_array('%(cp_account_ids)s',',')::INT[]
                                        '''%({'cp_account_ids':cp_account_ids})
            if len(cp2_account_ids):
                filter_aml_cp_account_ids += ''' and (aml.reconcile_counterpart_ids is not null  
                                                        and string_to_array(aml.reconcile_counterpart_ids,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
                                                        or string_to_array(aml.counterpart_ids,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
                                                    )
                                        '''%({'cp2_account_ids':cp2_account_ids})
                
                filter_aml2_cp_account_ids += ''' and (aml2.reconcile_counterpart_ids is not null 
                                                        and string_to_array(aml2.reconcile_counterpart_ids,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
                                                        or string_to_array(aml2.account_id::text,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
                                                    )
                                        '''%({'cp2_account_ids':cp2_account_ids})
                                        
            
        #THANH: change second_currency_id into 0 when it is null to prevent sql condition
        if not second_currency_id:
            second_currency_id = 'null'
        
        sql_begin_balance = '''
            select sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
            from (
                    select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                        sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                            else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end) dr_second_amount,
                            
                        sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                            else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end) cr_second_amount
                    
                    from account_move_line aml
                        LEFT JOIN account_move am on am.id = aml.move_id
                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                    where 
                        am.date = coalesce((select am.date
                                from account_move_line aml3
                                    LEFT JOIN account_move am on am.id = aml3.move_id
                                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                        and am.company_id= %(company_id)s
                                        %(filter_aml_partner_id)s
                                        and am.state = 'posted'
                                where am.date <= '%(end_date)s'::date 
                                order by am.date desc
                                limit 1),'2000-01-01')
                        and am.company_id= %(company_id)s
                        and am.state = 'posted'
                        %(filter_am_journal_ids)s
                        
                        %(filter_aml_account_ids)s
                        %(filter_aml_partner_id)s
                        
                        
                union all
                    select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                        sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                            else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end) dr_second_amount,
                            
                        sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                            else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end) cr_second_amount
                    
                    from account_move_line aml
                        LEFT JOIN account_move am on am.id = aml.move_id
                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                    where 
                        am.date between
                            coalesce((select am.date
                                    from account_move_line aml3
                                        LEFT JOIN account_move am on am.id = aml3.move_id
                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                            and am.company_id= %(company_id)s
                                            %(filter_aml_partner_id)s
                                            and am.state = 'posted'
                                    where am.date <= '%(end_date)s'::date 
                                    order by am.date desc
                                    limit 1),'2000-01-01')
                            and ('%(start_date)s'::date - 1)::date
                        and am.company_id= %(company_id)s
                        and am.state = 'posted'
                        %(filter_am_journal_ids)s
                        
                        %(filter_aml_account_ids)s
                        %(filter_aml_cp_account_ids)s -- filter by counter part account
                        %(filter_aml_partner_id)s
                )v
        '''
        sql_begin_balance = sql_begin_balance%({
              'start_date': start_date,
              'end_date': end_date,
              'filter_am_journal_ids': filter_am_journal_ids,
              'filter_aml_account_ids': filter_aml_account_ids,
              'filter_aml_cp_account_ids': filter_aml_cp_account_ids,
              'filter_aml_partner_id':filter_aml_partner_id,
              'company_id': company_id,
              'com_currency_id': report.company_id.currency_id.id,
              'second_currency_id': second_currency_id,
              'ledger_id': report.id,
              })
        
        if len(account_ids):
            sql_period_transaction = _('''
                select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                aml.name description, 
                acc.code acc_code,
                (select acc.code 
                    from account_move_line aml2 
                        JOIN account_account acc ON aml2.account_id=acc.id
                    where aml2.move_id=aml.move_id order by abs(aml2.balance) desc limit 1) cp_acc_code,
                
                aml.debit dr_amount, aml.credit cr_amount,
                aml.second_ex_rate::numeric,
                
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end dr_second_amount,
                    
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end cr_second_amount,
                    
                coalesce(aml.partner_id,am.partner_id) as partner_id,
                aml.amount_currency, aml.currency_ex_rate,
                (select name
                from res_currency
                where id=aml.currency_id) currency_name
                    
                from account_move_line aml
                    LEFT JOIN account_move am on aml.move_id=am.id
                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                    JOIN account_account acc ON aml.account_id=acc.id
                where am.date between '%(start_date)s' and '%(end_date)s'
                    %(filter_am_journal_ids)s
                    and am.company_id= %(company_id)s
                    and am.state = 'posted'
                
                    %(filter_aml_account_ids)s 
                    %(filter_aml_cp_account_ids)s -- filter by counter part account
                    %(filter_aml_partner_id)s
                   
                    and abs(aml.balance) < (select max(abs(aml2.balance)) 
                                            from account_move_line aml2 
                                            where aml2.move_id=aml.move_id 
                                                and aml2.group_cp=aml.group_cp
                                            limit 1)
        
            union all
            
                /* THANH: to show Report Account Ledger (So cai), only show journal item with acount_id and cp account id
                    - Lay cac move line co balance nho hon dong co debit hoac credit == maximum trong cung account.move 
                */
                select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                aml2.name description,
                (select acc.code 
                    from account_account acc
                    where acc.id=aml.account_id) acc_code,
                acc.code cp_acc_code,
                aml2.credit dr_amount, aml2.debit cr_amount,
                aml2.second_ex_rate::numeric,
                
                case when (aml2.currency_id = %(second_currency_id)s and aml2.amount_currency < 0) then abs(aml2.amount_currency)::numeric
                    else case when aml2.second_amount < 0 then abs(aml2.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end dr_second_amount,
                    
                case when (aml2.currency_id = %(second_currency_id)s and aml2.amount_currency > 0) then abs(aml2.amount_currency)::numeric
                    else case when aml2.second_amount > 0 then abs(aml2.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end cr_second_amount,
                
                coalesce(aml2.partner_id,am.partner_id) as partner_id,
                aml2.amount_currency, aml2.currency_ex_rate, 
                (select name
                    from res_currency
                    where id=aml2.currency_id) currency_name
                    
                from account_move_line aml2
                        LEFT JOIN account_move am on aml2.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                        JOIN account_account acc ON aml2.account_id=acc.id
                    JOIN account_move_line aml on aml2.move_id = aml.move_id
                where am.date between '%(start_date)s' and '%(end_date)s'
                    and am.company_id= %(company_id)s
                    and am.state = 'posted'
                    %(filter_am_journal_ids)s
                    
                    %(filter_aml2_cp_account_ids)s -- filter by counter part account
                    %(filter_aml_account_ids)s 
                    %(filter_aml_partner_id)s
                    and aml2.account_id != aml.account_id
                    
                    and aml2.group_cp = aml.group_cp
                    and abs(aml.balance) = (select max(abs(aml3.balance))
                                            from account_move_line aml3 
                                            where aml3.move_id=aml.move_id 
                                                and aml3.group_cp=aml.group_cp
                                            limit 1)
            ''')
        else:
            sql_period_transaction = _('''
            /* THANH: to show Report General Journal (Nhat ky chung), only show journal item with acount_id and cp account id */
                /*  - Lay dong co debit hoac credit nho hon dong maximum trong cung account.move (Danh cho phieu chi cash or bank, chi cho nhieu tk chi phi, VAT, fee)
                    - Quan trong la lay tai khoan doi ung, VD:
                        line 1: Acc: 64281 - CP Acc: 1111
                        line 2: Acc: 1331 - CP Acc: 1111
                        line 3: Acc: 64282 - CP Acc: 1111
                        ...
                */
                select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                aml.name description, 
                acc.code acc_code,
                (select acc.code 
                    from account_move_line aml2 
                        JOIN account_account acc ON aml2.account_id=acc.id
                    where aml2.move_id=aml.move_id order by abs(aml2.balance) desc limit 1) cp_acc_code,
                
                aml.debit dr_amount, aml.credit cr_amount,
                aml.second_ex_rate::numeric,
                
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end dr_second_amount,
                    
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end cr_second_amount,
                    
                coalesce(aml.partner_id,am.partner_id) as partner_id,
                aml.amount_currency, aml.currency_ex_rate,
                (select name
                from res_currency
                where id=aml.currency_id) currency_name
                    
                from account_move_line aml
                    LEFT JOIN account_move am on aml.move_id=am.id
                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                    JOIN account_account acc ON aml.account_id=acc.id
                where am.date between '%(start_date)s' and '%(end_date)s'
                    and am.company_id= %(company_id)s
                    and am.state = 'posted'
                    %(filter_am_journal_ids)s
                    
                    %(filter_aml_cp_account_ids)s -- filter by counter part account
                    %(filter_aml_partner_id)s
                    and abs(aml.balance) < (select max(abs(aml2.balance)) 
                                            from account_move_line aml2 
                                            where aml2.move_id=aml.move_id 
                                                and aml2.group_cp=aml.group_cp
                                            limit 1)
        
            union all
                /*  - Lay dong co debit hoac credit = maximum trong cung account.move (Danh cho phieu chi cash or bank, chi cho nhieu tk chi phi, VAT, fee)
                    - Quan trong la lay tai khoan doi ung (VD: Acc: 1111, CP Acc: 6321,1331,...)
                */
                select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                aml.name description, 
                acc.code acc_code,
                array_to_string(ARRAY(SELECT DISTINCT a.code
                                  FROM account_move_line m2
                                      JOIN account_account a ON (m2.account_id=a.id)
                                  WHERE m2.move_id = aml.move_id
                                  AND m2.account_id not in (aml.account_id)), ', ') AS cp_acc_code,
                
                aml.debit dr_amount, aml.credit cr_amount,
                aml.second_ex_rate::numeric,
                
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end dr_second_amount,
                    
                case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                    else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                        else 0.0::numeric
                        end 
                    end cr_second_amount,
                
                coalesce(aml.partner_id,am.partner_id) as partner_id,
                aml.amount_currency, aml.currency_ex_rate,
                (select name
                        from res_currency
                        where id=aml.currency_id) currency_name
                
                from account_move_line aml
                        LEFT JOIN account_move am on aml.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                        JOIN account_account acc ON aml.account_id=acc.id
                where am.date between '%(start_date)s' and '%(end_date)s'
                    and am.company_id = %(company_id)s
                    and am.state = 'posted'
                    %(filter_am_journal_ids)s 
                    
                    %(filter_aml_cp_account_ids)s -- filter by counter part account
                    %(filter_aml_partner_id)s
                    and abs(aml.balance) = (select max(abs(aml2.balance)) 
                                            from account_move_line aml2 
                                            where aml2.move_id=aml.move_id 
                                                and aml2.group_cp=aml.group_cp
                                            limit 1)
            ''')
        sql_period_transaction = sql_period_transaction%({
              'start_date': start_date,
              'end_date': end_date,
              'filter_am_journal_ids': filter_am_journal_ids,
              'filter_aml_account_ids': filter_aml_account_ids,
              'filter_aml_cp_account_ids': filter_aml_cp_account_ids,
              'filter_aml_partner_id':filter_aml_partner_id,
              'company_id': company_id,
              'com_currency_id': report.company_id.currency_id.id,
              'second_currency_id': second_currency_id,
              
              'filter_aml2_cp_account_ids': filter_aml2_cp_account_ids,
            })
        if report.view_type == 'partner' and len(account_ids):
            sql_period_transaction = '''
                /*  Lay phat sinh trong ky, lay so tong, 
                    khong hien thi chi tiet nhieu No or nhieu Co trong but toan co 1 No nhieu Co va nguoc lai
                */
                    select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                    aml.name description, 
                    acc.code acc_code,
                    array_to_string(ARRAY(SELECT DISTINCT a.code
                                  FROM account_move_line m2
                                      JOIN account_account a ON (m2.account_id=a.id)
                                  WHERE m2.move_id = aml.move_id and m2.id != aml.id), ', ') AS cp_acc_code,
                                  
                    aml.debit dr_amount, aml.credit cr_amount,
                    aml.second_ex_rate::numeric,
                    
                    case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                        else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                            else 0.0::numeric
                            end 
                        end dr_second_amount,
                        
                    case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                        else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                            else 0.0::numeric
                            end 
                        end cr_second_amount,
                        
                    coalesce(aml.partner_id,am.partner_id) as partner_id,
                    aml.amount_currency, aml.currency_ex_rate,
                    (select name
                    from res_currency
                    where id=aml.currency_id) currency_name
                        
                    from account_move_line aml
                        LEFT JOIN account_move am on aml.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                        JOIN account_account acc ON aml.account_id=acc.id
                    where am.date between '%(start_date)s' and '%(end_date)s'
                        and am.company_id= %(company_id)s
                        and am.state = 'posted'
                        %(filter_am_journal_ids)s
                        
                        %(filter_aml_account_ids)s
                        %(filter_aml_cp_account_ids)s -- filter by counter part account
                        %(filter_aml_partner_id)s
            '''
            sql_period_transaction = sql_period_transaction%({
                  'start_date': start_date,
                  'end_date': end_date,
                  'filter_am_journal_ids': filter_am_journal_ids,
                  'filter_aml_account_ids': filter_aml_account_ids,
                  'filter_aml_cp_account_ids': filter_aml_cp_account_ids,
                  'filter_aml_partner_id':filter_aml_partner_id,
                  'company_id': company_id,
                  'com_currency_id': report.company_id.currency_id.id,
                  'second_currency_id': second_currency_id,
            })
            
        if report.view_type == 'liquidity' and len(account_ids):
            sql_period_transaction = '''
                /*  Lay phat sinh trong ky, lay so tong, 
                    khong hien thi chi tiet nhieu No or nhieu Co trong but toan co 1 No nhieu Co va nguoc lai
                */
                    select am.date gl_date, coalesce(am.doc_date,am.date) doc_date, coalesce(am.ref,am.name) doc_no, 
                    aml.name description, 
                    acc.code acc_code,
                    array_to_string(ARRAY(SELECT DISTINCT a.code
                                  FROM account_move_line m2
                                      JOIN account_account a ON (m2.account_id=a.id)
                                  WHERE m2.move_id = aml.move_id and m2.id != aml.id), ', ') AS cp_acc_code,
                                  
                    aml.debit dr_amount, aml.credit cr_amount,
                    aml.second_ex_rate::numeric,
                    
                    case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                        else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                            else 0.0::numeric
                            end 
                        end dr_second_amount,
                        
                    case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                        else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                            else 0.0::numeric
                            end 
                        end cr_second_amount,
                        
                    coalesce(aml.partner_id,am.partner_id) as partner_id,
                    aml.amount_currency, aml.currency_ex_rate,
                    (select name
                    from res_currency
                    where id=aml.currency_id) currency_name
                        
                    from account_move_line aml
                        LEFT JOIN account_move am on aml.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                        JOIN account_account acc ON aml.account_id=acc.id
                    where am.date between '%(start_date)s' and '%(end_date)s'
                        and am.company_id= %(company_id)s
                        and am.state = 'posted'
                        %(filter_am_journal_ids)s
                        
                        %(filter_aml_account_ids)s
                        %(filter_aml_cp_account_ids)s -- filter by counter part account
                        %(filter_aml_partner_id)s

                        --THANH: get data which not related to Account Payment (Ko lien quan phieu thu, chi)
                        and (aml.payment_id is null 
                                and 
                            am.id not in (select api.move_id 
                                            from account_payment_invoice api
                                                join account_payment ap on ap.id=api.line_id
                                            where ap.state = 'posted' and ap.payment_date between '%(start_date)s' and '%(end_date)s'
                                                 and api.move_id is not null
                                            )
                            )
                    
                union all
                    
                    select ap.payment_date gl_date, ap.payment_date doc_date, ap.name doc_no, 
                        ap.communication description,
                        acc.code acc_code,
                        ''::text cp_acc_code,
                        foo.dr_amount dr_amount, foo.cr_amount cr_amount,
                        (select coalesce(rate,0.0) 
                            from res_currency_rate 
                            where currency_id=%(com_currency_id)s 
                                and name=ap.payment_date
                            limit 1) as second_ex_rate,
                        foo.dr_second_amount dr_second_amount, foo.cr_second_amount cr_second_amount,
                        ap.partner_id partner_id,
                        
                        0.0::numeric amount_currency, 
                        0.0::numeric currency_ex_rate,
                        (select name
                        from res_currency
                        where id=ap.currency_id) currency_name
                        
                    from (
                            select 
                                aml.payment_id payment_id, aml.account_id,
                                sum(aml.debit) dr_amount, 
                                sum(aml.credit) cr_amount,
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                    else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) dr_second_amount,
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                    else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) cr_second_amount
                            from account_move_line aml
                                LEFT JOIN account_move am on aml.move_id=am.id
                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                
                                --THANH: link phieu thu, phieu chi de lay so tong (Vi 1 phieu thu chi co the co nhieu HD)
                                JOIN account_payment ap on aml.payment_id = ap.id
                            where am.date between '%(start_date)s' and '%(end_date)s'
                                and am.company_id= %(company_id)s
                                and am.state = 'posted'
                                %(filter_am_journal_ids)s
                                
                                %(filter_aml_account_ids)s
                                %(filter_aml_cp_account_ids)s -- filter by counter part account
                                %(filter_aml_partner_id)s
                                
                                --THANH: get data which not related to Account Payment (Ko lien quan phieu thu, chi)
                                and (aml.payment_id is not null 
                                        and 
                                    am.id not in (select api.move_id 
                                                    from account_payment_invoice api
                                                        join account_payment ap on ap.id=api.line_id
                                                    where ap.state = 'posted' and ap.payment_date between '%(start_date)s' and '%(end_date)s'
                                                         and api.move_id is not null
                                                    )
                                    )
                            group by aml.payment_id, aml.account_id
                        
                        union all
                            
                            select 
                                api.line_id payment_id, aml.account_id,
                                sum(aml.debit) dr_amount, 
                                sum(aml.credit) cr_amount,
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency > 0) then abs(aml.amount_currency)::numeric
                                    else case when aml.second_amount > 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) dr_second_amount,
                                sum(case when (aml.currency_id = %(second_currency_id)s and aml.amount_currency < 0) then abs(aml.amount_currency)::numeric
                                    else case when aml.second_amount < 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end) cr_second_amount
                            from account_move_line aml
                                LEFT JOIN account_move am on aml.move_id=am.id
                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                
                                --THANH: link phieu thu, phieu chi de lay so tong (Vi 1 phieu thu chi co the co nhieu HD)
                                JOIN account_payment_invoice api on am.id = api.move_id
                            where am.date between '%(start_date)s' and '%(end_date)s'
                                and am.company_id= %(company_id)s
                                and am.state = 'posted'
                                %(filter_am_journal_ids)s
                                
                                %(filter_aml_account_ids)s
                                %(filter_aml_cp_account_ids)s -- filter by counter part account
                                %(filter_aml_partner_id)s
                                
                                --THANH: get data which not related to Account Payment (Ko lien quan phieu thu, chi)
                                and (aml.payment_id is null 
                                        and 
                                    am.id in (select api.move_id 
                                                    from account_payment_invoice api
                                                        join account_payment ap on ap.id=api.line_id
                                                    where ap.state = 'posted' and ap.payment_date between '%(start_date)s' and '%(end_date)s'
                                                         and api.move_id is not null
                                            )
                                    )
                            group by api.line_id, aml.account_id
                    ) foo
                    JOIN account_payment ap on foo.payment_id = ap.id
                    JOIN account_account acc ON foo.account_id=acc.id
            '''
            sql_period_transaction = sql_period_transaction%({
                  'start_date': start_date,
                  'end_date': end_date,
                  'filter_am_journal_ids': filter_am_journal_ids,
                  'filter_aml_account_ids': filter_aml_account_ids,
                  'filter_aml_cp_account_ids': filter_aml_cp_account_ids,
                  'filter_aml_partner_id':filter_aml_partner_id,
                  'company_id': company_id,
                  'com_currency_id': report.company_id.currency_id.id,
                  'second_currency_id': second_currency_id,
            })
        if showdetail:
            sql = _('''
            INSERT INTO general_account_ledger_detail (create_uid, create_date, write_uid, write_date,
                ledger_id, seq, gl_date, doc_date, doc_no, description, acc_code, cp_acc_code, debit, credit,
                debit_second, credit_second, second_ex_rate, partner_id, amount_currency, currency_rate, currency_name,com_currency_id, second_currency_id)
                
                SELECT %(uid)s, current_timestamp, %(uid)s, current_timestamp,
                        %(ledger_id)s, seq, gl_date, doc_date, doc_no, description, acc_code, cp_acc_code,
                        nullif(dr_amount,0) debit, nullif(cr_amount,0) credit,
                        nullif(dr_second_amount,0) dr_second_amount, nullif(cr_second_amount,0) cr_second_amount,
                        second_ex_rate,
                        partner_id, 
                        amount_currency, currency_ex_rate, currency_name,
                        %(com_currency_id)s, %(second_currency_id)s
                FROM(
                        select 0 as seq, null::date as gl_date, null::date as doc_date,
                            null::text as doc_no, 'Số dư đầu kỳ' as description,
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
                            null partner_id,
                            0 amount_currency, 0 currency_ex_rate, null::text currency_name
                        from (
                            %(sql_begin_balance)s
                        ) start_bal
                            
                    union all
                        select row_number() over(order by gl_date, doc_date, doc_no, dr_amount desc, acc_code, cp_acc_code)::int seq, 
                            gl_date, doc_date, doc_no, description, acc_code, cp_acc_code,
                            dr_amount, cr_amount,
                            second_ex_rate,
                            dr_second_amount, cr_second_amount,
                            partner_id,
                            amount_currency, currency_ex_rate, currency_name
                        from (
                            %(sql_period_transaction)s
                        ) x
                        
                    union all
                    /*    Add them dong sum detail    */
                        select 99998 as seq, 
                            null::date gl_date, null::date doc_date, null::character varying doc_no, 'Số phát sinh trong kỳ'::character varying description,
                            null::character varying acc_code,
                            null::character varying cp_acc_code,
                            sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                            0 second_ex_rate,
                            sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount,
                            null partner_id,
                            0 amount_currency, 0 currency_ex_rate, null::text currency_name
                        from (
                            %(sql_period_transaction)s
                        ) x
                                    
                    union all
                    /*    Lay so cuoi ky    */
                        select 99999 as seq, null::date as gl_date, null::date as doc_date,
                            null::text as doc_no, 'Số dư cuối kỳ' as description,
                            null::text as acc_code, null::text as cp_acc_code,
                            case when sum(dr_amount) > sum(cr_amount) then sum(dr_amount) - sum(cr_amount)
                                else null end dr_amount,
                            case when sum(dr_amount) < sum(cr_amount) then  sum(cr_amount) - sum(dr_amount)
                                else null end cr_amount,
                            0::numeric second_ex_rate,
                            case when sum(dr_second_amount) > sum(cr_second_amount) then (sum(dr_second_amount) - sum(cr_second_amount))::numeric
                                else null end dr_second_amount,
                            case when sum(dr_second_amount) < sum(cr_second_amount) then  (sum(cr_second_amount) - sum(dr_second_amount))::numeric
                                else null end cr_second_amount,
                            null partner_id,
                            0 amount_currency, 0 currency_ex_rate, null::text currency_name
                        from (
                                %(sql_begin_balance)s
                            union all
                                select 
                                    sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                                    sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
                                from (
                                    %(sql_period_transaction)s
                                ) x
                        ) end_bal
                    )foo
                ''')
            sql = sql%({
                  'start_date': start_date,
                  'end_date': end_date,
                  'filter_am_journal_ids': filter_am_journal_ids,
                  'filter_aml_account_ids': filter_aml_account_ids,
                  'filter_aml_cp_account_ids': filter_aml_cp_account_ids,
                  'filter_aml_partner_id':filter_aml_partner_id,
                  'company_id': company_id,
                  'com_currency_id': report.company_id.currency_id.id,
                  'second_currency_id': second_currency_id,
                  'ledger_id': report.id,
                  'sql_period_transaction': sql_period_transaction,
                  'sql_begin_balance': sql_begin_balance,
                  'uid': uid,
                })
        else:
            sql = _('''
            INSERT INTO general_account_ledger (create_uid, create_date, write_uid, write_date,
                    ledger_id, description, debit, credit, debit_second, credit_second, com_currency_id, second_currency_id)
                SELECT %(uid)s, current_timestamp, %(uid)s, current_timestamp,
                        %(ledger_id)s, description,
                        nullif(dr_amount,0) debit, nullif(cr_amount,0) credit,
                        nullif(dr_second_amount,0) dr_second_amount, nullif(cr_second_amount,0) cr_second_amount,
                        %(com_currency_id)s, %(second_currency_id)s
                FROM(
                        select 0 as seq, 'Số dư đầu kỳ' as description,
                            case when dr_amount > cr_amount then dr_amount - cr_amount
                                else null end dr_amount,
                            case when dr_amount < cr_amount then  cr_amount - dr_amount
                                else null end cr_amount,
                            case when dr_second_amount > cr_second_amount then (dr_second_amount - cr_second_amount)::numeric
                                else null end dr_second_amount,
                            case when dr_second_amount < cr_second_amount then  (cr_second_amount - dr_second_amount)::numeric
                                else null end cr_second_amount
                        from (
                            %(sql_begin_balance)s
                        ) start_bal
                            
                    union all
                        /*    Add dong sum trong ky    */
                        select 900 as seq, 'Số phát sinh trong kỳ'::character varying description,
                            sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                            sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
                        from (
                            %(sql_period_transaction)s
                        ) x
                            
                    union all
                    /*    Lay so cuoi ky    */
                        select 999 as seq, 'Số dư cuối kỳ' as description,
                            case when sum(dr_amount) > sum(cr_amount) then sum(dr_amount) - sum(cr_amount)
                                else null end dr_amount,
                            case when sum(dr_amount) < sum(cr_amount) then  sum(cr_amount) - sum(dr_amount)
                                else null end cr_amount,
                            case when sum(dr_second_amount) > sum(cr_second_amount) then (sum(dr_second_amount) - sum(cr_second_amount))::numeric
                                else null end dr_second_amount,
                            case when sum(dr_second_amount) < sum(cr_second_amount) then  (sum(cr_second_amount) - sum(dr_second_amount))::numeric
                                else null end cr_second_amount
                        from (
                                %(sql_begin_balance)s
                            union all
                                select 
                                    sum(dr_amount) dr_amount, sum(cr_amount) cr_amount,
                                    sum(dr_second_amount) dr_second_amount, sum(cr_second_amount) cr_second_amount
                                from (
                                    %(sql_period_transaction)s
                                ) x
                        ) end_bal
                    )x
                ''')
            sql = sql%({
                  'start_date': start_date,
                  'end_date': end_date,
                  'filter_am_journal_ids': filter_am_journal_ids,
                  'filter_aml_account_ids':filter_aml_account_ids,
                  'filter_aml_cp_account_ids':filter_aml_cp_account_ids,
                  'filter_aml_partner_id':filter_aml_partner_id,
                  'company_id': company_id,
                  'com_currency_id': report.company_id.currency_id.id,
                  'second_currency_id': second_currency_id,
                  'ledger_id': report.id,
                  'sql_begin_balance': sql_begin_balance,
                  'sql_period_transaction': sql_period_transaction,
                  'uid': uid,
                  })
        cr.execute(sql)
        return True
