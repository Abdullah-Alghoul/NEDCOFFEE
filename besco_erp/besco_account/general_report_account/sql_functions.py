# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class sql_function(osv.osv):
    _name = "sql.function"
    _auto = False
    
    def init(self, cr):
        self.fin_account_balance(cr)
        cr.commit()
        return True
    
    def fin_account_balance(self, cr):
        sql = '''
        delete from pg_proc where proname = 'fin_account_balance';
        commit;
        
        CREATE OR REPLACE FUNCTION fin_account_balance(IN date, IN date, IN INT[], IN integer, IN INT[], IN text, IN text)
          --RETURNS TABLE(dr_amount numeric, cr_amount numeric, dr_2rd_amount numeric, cr_2rd_amount numeric) AS
          RETURNS TABLE(begin_balance numeric, begin_balance_2rd numeric, balance numeric, balance_2rd numeric) AS
        $BODY$
        DECLARE
            rec        record;
        BEGIN
            for rec in execute '
                SELECT sum(begin_balance) begin_balance, sum(begin_balance_2rd) begin_balance_2rd, 
                        sum(balance) balance, sum(balance_2rd) balance_2rd
                FROM (
                    SELECT foo.partner_id, foo.account_id,
                        case when ($7 = ''balance'') then (sum(begin_debit) - sum(begin_credit))
                        else case when ($7 = ''balance_dr'' and sum(begin_debit) > sum(begin_credit)) then (sum(begin_debit) - sum(begin_credit))
                             else case when ($7 = ''balance_cr'' and sum(begin_credit) > sum(begin_debit)) then (sum(begin_credit) - sum(begin_debit))
                                  else 0.0::numeric
                                  end
                             end 
                        end begin_balance,
                        case when ($7 = ''balance'') then (sum(begin_dr_2rd_amount) - sum(begin_cr_2rd_amount))
                        else case when ($7 = ''balance_dr'' and sum(begin_dr_2rd_amount) > sum(begin_cr_2rd_amount)) then (sum(begin_dr_2rd_amount) - sum(begin_cr_2rd_amount))
                             else case when ($7 = ''balance_cr'' and sum(begin_cr_2rd_amount) > sum(begin_dr_2rd_amount)) then (sum(begin_cr_2rd_amount) - sum(begin_dr_2rd_amount))
                                  else 0.0::numeric
                                  end
                             end 
                        end begin_balance_2rd,
                        
                        case when ($7 = ''balance'') then (sum(debit) - sum(credit))
                        else case when ($7 = ''balance_dr'' and sum(debit) > sum(credit)) then (sum(debit) - sum(credit))
                             else case when ($7 = ''balance_cr'' and sum(credit) > sum(debit)) then (sum(credit) - sum(debit))
                                  else 0.0::numeric
                                  end
                             end 
                        end balance,
                        case when ($7 = ''balance'') then (sum(dr_2rd_amount) - sum(cr_2rd_amount))
                        else case when ($7 = ''balance_dr'' and sum(dr_2rd_amount) > sum(cr_2rd_amount)) then (sum(dr_2rd_amount) - sum(cr_2rd_amount))
                             else case when ($7 = ''balance_cr'' and sum(cr_2rd_amount) > sum(dr_2rd_amount)) then (sum(cr_2rd_amount) - sum(dr_2rd_amount))
                                  else 0.0::numeric
                                  end
                             end 
                        end balance_2rd
                    FROM (    
                    
                            /*    Lay so du dau ky    */
                            select aml.partner_id, aml.account_id,
                                aml.debit begin_debit, aml.credit begin_credit,
                                
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end begin_dr_2rd_amount,
                                
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end begin_cr_2rd_amount,
                                
                                0.0::numeric debit, 0.0::numeric credit,
                                0.0::numeric dr_2rd_amount, 0.0::numeric cr_2rd_amount
                                
                                
                            from account_move_line aml 
                                join account_move amh on amh.id = aml.move_id
                                join account_journal ajn on amh.journal_id = ajn.id and ajn.type = ''situation''
                            where amh.regularization_id  is null
                                and amh.state = ''posted'' 
                                and amh.journal_id = ANY($5)
                                and aml.account_id = ANY($3)
                                and amh.company_id = $4
                                and aml.date = coalesce((select am.date
                                                            from account_move_line aml3
                                                                LEFT JOIN account_move am on am.id = aml3.move_id
                                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = ''situation''
                                                                    and am.company_id= $4
                                                                    and am.state = ''posted''
                                                            where am.date <= $2::date 
                                                            order by am.date desc
                                                            limit 1),''2000-01-01'')
                            UNION ALL
                            select aml.partner_id, aml.account_id,
                                aml.debit begin_debit, aml.credit begin_credit,
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end begin_dr_2rd_amount,
                                
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end begin_cr_2rd_amount,
                                
                                0.0::numeric debit, 0.0::numeric credit,
                                0.0::numeric dr_2rd_amount, 0.0::numeric cr_2rd_amount
                                
                            from account_move_line aml 
                                join account_move amh on amh.id = aml.move_id
                                join account_journal ajn on amh.journal_id = ajn.id and ajn.type != ''situation''
                            where amh.regularization_id  is null
                                and amh.state = ''posted'' 
                                and amh.journal_id = ANY($5)
                                and aml.account_id = ANY($3)
                                and amh.company_id = $4
                                and aml.date between
                                        coalesce((select am.date
                                            from account_move_line aml3
                                                LEFT JOIN account_move am on am.id = aml3.move_id
                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = ''situation''
                                                    and am.company_id= $4
                                                    and am.state = ''posted''
                                            where am.date <= $2::date 
                                            order by am.date desc
                                            limit 1),''2000-01-01'')
                                    and ($1::date - 1)::date
                                    
                        UNION ALL
                            /*    Lay phat sinh trong ky    */
                            select aml.partner_id, aml.account_id,
                                0.0::numeric begin_debit, 0.0::numeric begin_credit,
                                0.0::numeric begin_dr_2rd_amount, 0.0::numeric begin_cr_2rd_amount,
                                
                                aml.debit, aml.credit,
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.debit != 0) then abs(amount_currency)::numeric
                                    else case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end dr_2rd_amount,
                                
                                case when (aml.currency_id = (select second_currency_id from res_company where id=$4 limit 1) and aml.credit != 0) then abs(amount_currency)::numeric
                                    else case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                        else 0.0::numeric
                                        end 
                                    end cr_2rd_amount
                            from account_move_line aml 
                                    LEFT JOIN account_move amh on aml.move_id=amh.id
                                    JOIN account_journal ajn on amh.journal_id = ajn.id and ajn.type <> ''situation''
                                    
                            where amh.regularization_id  is null
                                and amh.state = ''posted'' 
                                and date(aml.date) between date($1::date) and date($2::date)
                                and amh.journal_id = ANY($5)
                                and aml.account_id = ANY($3)
                                and amh.company_id = $4
                                ' || $6 || ') as foo
                    GROUP BY foo.partner_id, foo.account_id) as king
            ' using $1, $2, $3, $4, $5, $6, $7
            
            loop
                begin_balance = coalesce(rec.begin_balance, 0.0);
                begin_balance_2rd = coalesce(rec.begin_balance_2rd, 0.0);
                
                balance = coalesce(rec.balance, 0.0);
                balance_2rd = coalesce(rec.balance_2rd, 0.0);
                RETURN NEXT;
            end loop;
        END;$BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
        '''
        cr.execute(sql)
        return True    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
