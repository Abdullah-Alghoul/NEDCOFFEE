# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class sql_financial_report(osv.osv):
    _name = "sql.financial.report"
    _auto = False
    
    def get_line(self, cr, uid, start_date, end_date, account_ids, journal_ids, second_currency_id, company_id, 
                 cp_account_ids, cp2_account_ids, report_line):
        
        filter_am_journal_ids = ''
        if len(journal_ids):
            filter_am_journal_ids += ' and am.journal_id in (%(journal_ids)s)'%({'journal_ids':journal_ids,})
        
        filter_aml_account_ids = ''
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
                
#                 filter_aml2_cp_account_ids += ''' and (aml2.reconcile_counterpart_ids is not null 
#                                                         and string_to_array(aml2.reconcile_counterpart_ids,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
#                                                         or string_to_array(aml2.account_id::text,',')::INT[] && string_to_array('%(cp2_account_ids)s',',')::INT[]
#                                                     )
#                                         '''%({'cp2_account_ids':cp2_account_ids})
        
        filter_am_regularization = ' and am.regularization_id is null'
        if not report_line.remove_regularization:
            filter_am_regularization = ''
            
        sql_period_transaction = '''
                /*    Lay phat sinh trong ky    */
                select partner_id, account_id,
                    0.0::numeric begin_debit, 0.0::numeric begin_credit,
                    0.0::numeric begin_dr_2rd_amount, 0.0::numeric begin_cr_2rd_amount,
                    
                    debit, credit, dr_2rd_amount, cr_2rd_amount
                from (
                    select aml.partner_id, aml.account_id,
                        aml.debit, aml.credit,
                        case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                            else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end dr_2rd_amount,
                        
                        case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                            else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end cr_2rd_amount
                            
                    from 
                        account_move_line aml
                        LEFT JOIN account_move am on aml.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                    where am.date between '%(start_date)s' and '%(end_date)s'
                        and am.state = 'posted'
                        %(filter_am_regularization)s
                        %(filter_am_journal_ids)s
                        and am.company_id = %(company_id)s
                        
                        %(filter_aml_account_ids)s
                        %(filter_aml_cp_account_ids)s
                        and abs(aml.balance) <= (select max(abs(aml2.balance)) 
                                                from account_move_line aml2 
                                                where aml2.move_id=aml.move_id 
                                                    %(filter_aml2_group_cp)s
                                                limit 1)
                )x
        '''
            
        if len(cp_account_ids):
            sql_period_transaction = '''
                    /*    Lay phat sinh trong ky    */
                    select partner_id, account_id,
                        0.0::numeric begin_debit, 0.0::numeric begin_credit,
                        0.0::numeric begin_dr_2rd_amount, 0.0::numeric begin_cr_2rd_amount,
                        
                        debit, credit, dr_2rd_amount, cr_2rd_amount
                    from (
                        select 
                            coalesce(aml2.partner_id,am.partner_id) as partner_id, aml.account_id,
                            aml2.credit debit, aml2.debit credit,
                            
                            case when (aml2.currency_id = %(second_currency_id)s and aml2.amount_currency < 0) then abs(aml2.amount_currency)::numeric
                                else case when aml2.second_amount < 0 then abs(aml2.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end dr_2rd_amount,
                                
                            case when (aml2.currency_id = %(second_currency_id)s and aml2.amount_currency > 0) then abs(aml2.amount_currency)::numeric
                                else case when aml2.second_amount > 0 then abs(aml2.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end cr_2rd_amount
                                
                            from account_move_line aml2
                                    LEFT JOIN account_move am on aml2.move_id=am.id
                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                                    JOIN account_account acc ON aml2.account_id=acc.id
                                    JOIN account_move_line aml on aml2.move_id = aml.move_id
                            where am.date between '%(start_date)s' and '%(end_date)s'
                                %(filter_am_journal_ids)s
                                and am.company_id= %(company_id)s
                                and am.state = 'posted'
                                
                                %(filter_aml2_cp_account_ids)s -- filter by counter part account
                                and aml2.account_id != aml.account_id
                                and aml2.group_cp = aml.group_cp
                                
                                %(filter_aml_account_ids)s
                                %(filter_aml_cp_account_ids)s
                    )x
            '''
            
        group_by = ' foo.account_id'
        filter_aml2_group_cp = ' and aml2.group_cp = aml.group_cp'
        filter_aml3_group_cp = ' and aml3.group_cp = aml.group_cp'
        if report_line.group_by == 'partner':
            group_by = ' foo.partner_id, foo.account_id'
            filter_aml2_group_cp = ''
            filter_aml3_group_cp = ''
            sql_period_transaction = '''
                /*    Lay phat sinh trong ky    */
                select partner_id, account_id,
                    0.0::numeric begin_debit, 0.0::numeric begin_credit,
                    0.0::numeric begin_dr_2rd_amount, 0.0::numeric begin_cr_2rd_amount,
                    
                    debit, credit, dr_2rd_amount, cr_2rd_amount
                from (
                    select aml.partner_id, aml.account_id,
                        aml.debit, aml.credit,
                        case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                            else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end dr_2rd_amount,
                        
                        case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                            else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                else 0.0::numeric
                                end 
                            end cr_2rd_amount
                            
                    from 
                        account_move_line aml
                        LEFT JOIN account_move am on aml.move_id=am.id
                        JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type <> 'situation'
                    where am.date between '%(start_date)s' and '%(end_date)s'
                        and am.state = 'posted'
                        %(filter_am_regularization)s
                        %(filter_am_journal_ids)s
                        and am.company_id = %(company_id)s
                        %(filter_aml_account_ids)s
                        %(filter_aml_cp_account_ids)s
                )x
            '''
        
        sql_period_transaction = sql_period_transaction%({
                'start_date': start_date,
                'end_date': end_date,
                'filter_am_journal_ids': filter_am_journal_ids,
                'filter_am_regularization': filter_am_regularization,
                'filter_aml_account_ids':filter_aml_account_ids,
                'filter_aml_cp_account_ids':filter_aml_cp_account_ids,
                'filter_aml2_cp_account_ids': filter_aml2_cp_account_ids,
                'filter_aml2_group_cp': filter_aml2_group_cp,
                'filter_aml3_group_cp': filter_aml3_group_cp, 
                'balance_side': report_line.balance_side,
                'balance_value': report_line.balance_value,
                'group_by': group_by,
                'company_id': company_id,
                'second_currency_id': second_currency_id,
        })
        
        sql = '''
            SELECT 
                    sum(case when ('%(balance_side)s' = 'balance') then balance
                    else case when ('%(balance_side)s' = 'balance_dr' and balance > 0) then balance
                         else case when ('%(balance_side)s' = 'balance_cr' and balance < 0) then abs(balance)
                              else 0.0::numeric
                              end
                         end 
                    end) balance,
                    
                    sum(case when ('%(balance_side)s' = 'balance') then balance_2rd
                    else case when ('%(balance_side)s' = 'balance_dr' and balance_2rd > 0) then balance_2rd
                         else case when ('%(balance_side)s' = 'balance_cr' and balance_2rd < 0) then abs(balance_2rd)
                              else 0.0::numeric
                              end
                         end 
                    end) balance_2rd
                    
            FROM (
                SELECT 
                    %(group_by)s,
                    
                    case when ('%(balance_value)s' = 'begin_value') then (sum(begin_debit) - sum(begin_credit))
                    else case when ('%(balance_value)s' = 'periodical_value') then (sum(debit) - sum(credit))
                         else case when ('%(balance_value)s' = 'end_value') then (sum(begin_debit) - sum(begin_credit) + sum(debit) - sum(credit))
                              else 0.0::numeric
                              end
                         end 
                    end balance,
                    
                    case when ('%(balance_value)s' = 'begin_value') then (sum(begin_dr_2rd_amount) - sum(begin_cr_2rd_amount))
                    else case when ('%(balance_value)s' = 'periodical_value') then (sum(dr_2rd_amount) - sum(cr_2rd_amount))
                         else case when ('%(balance_value)s' = 'end_value') then (sum(begin_dr_2rd_amount) - sum(begin_cr_2rd_amount) + sum(dr_2rd_amount) - sum(cr_2rd_amount))
                              else 0.0::numeric
                              end
                         end 
                    end balance_2rd
                    
                FROM (

                        /*    Lay so du dau ky    */
                        select aml.partner_id, aml.account_id,
                            aml.debit begin_debit, aml.credit begin_credit,
                            
                            case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end begin_dr_2rd_amount,
                            
                            case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end begin_cr_2rd_amount,
                            
                            0.0::numeric debit, 0.0::numeric credit,
                            0.0::numeric dr_2rd_amount, 0.0::numeric cr_2rd_amount
                            
                            
                        from account_move_line aml 
                            join account_move am on am.id = aml.move_id
                            join account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                        where am.state = 'posted'
                            %(filter_am_regularization)s
                            %(filter_am_journal_ids)s
                            %(filter_aml_account_ids)s
                            and am.company_id = %(company_id)s
                            and aml.date = coalesce((select am.date
                                                        from account_move_line aml3
                                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                and am.company_id= %(company_id)s
                                                                and am.state = 'posted'
                                                        where am.date <= '%(end_date)s'::date 
                                                        order by am.date desc
                                                        limit 1), '2000-01-01')
                        UNION ALL
                        select aml.partner_id, aml.account_id,
                            aml.debit begin_debit, aml.credit begin_credit,
                            case when (aml.currency_id = %(second_currency_id)s and aml.debit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end begin_dr_2rd_amount,
                            
                            case when (aml.currency_id = %(second_currency_id)s and aml.credit != 0) then abs(aml.amount_currency)::numeric
                                else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                    end 
                                end begin_cr_2rd_amount,
                            
                            0.0::numeric debit, 0.0::numeric credit,
                            0.0::numeric dr_2rd_amount, 0.0::numeric cr_2rd_amount
                            
                        from account_move_line aml 
                            join account_move am on am.id = aml.move_id
                            join account_journal ajn on am.journal_id = ajn.id and ajn.type != 'situation'
                        where am.state = 'posted' 
                            %(filter_am_regularization)s
                            %(filter_am_journal_ids)s
                            %(filter_aml_account_ids)s
                            and am.company_id = %(company_id)s
                            and aml.date between
                                    coalesce((select am.date
                                        from account_move_line aml3
                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                and am.company_id= %(company_id)s
                                                and am.state = 'posted'
                                        where am.date <= '%(end_date)s'::date 
                                        order by am.date desc
                                        limit 1), '2000-01-01')
                                and ('%(start_date)s'::date - 1)::date
                                
                    UNION ALL
                        %(sql_period_transaction)s
                        
                ) as foo
                GROUP BY %(group_by)s
            ) as king
        '''
        sql = sql%({
              'start_date': start_date,
              'end_date': end_date,
              'filter_am_journal_ids': filter_am_journal_ids,
              'filter_am_regularization': filter_am_regularization,
              'filter_aml_account_ids':filter_aml_account_ids,
              'filter_aml_cp_account_ids':filter_aml_cp_account_ids,
              'filter_aml2_cp_account_ids': filter_aml2_cp_account_ids,
              'filter_aml2_group_cp': filter_aml2_group_cp,
              'filter_aml3_group_cp': filter_aml3_group_cp, 
              'balance_side': report_line.balance_side,
              'balance_value': report_line.balance_value,
              'group_by': group_by,
              'company_id': company_id,
              'second_currency_id': second_currency_id,
              
              'sql_period_transaction': sql_period_transaction,
              })
        cr.execute(sql)
        res = cr.dictfetchall()
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
