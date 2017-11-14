# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import _

class sql_trial_balance(osv.osv):
    _name = "sql.trial.balance"
    _auto = False
    
    def init(self, cr):
        self.fn_trial_balance_report(cr)
        return True
    
    def fn_trial_balance_report(self,cr):
        #THANH: Try to delete old function which has 3 parameters, newest has 4
        sql = '''
        --delete from pg_proc where proname = 'fin_trial_balance_report';
        --commit;
        
        CREATE OR REPLACE FUNCTION fin_trial_balance_report(IN date, IN date, IN integer, IN date, IN INT[], 
            OUT coa_id integer, OUT coa_code character varying, OUT coa_name character varying, OUT acc_level integer, 
            OUT begin_dr numeric, OUT begin_cr numeric, OUT period_dr numeric, OUT period_cr numeric, OUT ac_dr numeric, OUT ac_cr numeric, OUT end_dr numeric, OUT end_cr numeric,
            OUT begin_dr_2rd numeric, OUT begin_cr_2rd numeric, OUT period_dr_2rd numeric, OUT period_cr_2rd numeric, OUT ac_dr_2rd numeric, OUT ac_cr_2rd numeric, OUT end_dr_2rd numeric, OUT end_cr_2rd numeric)
          RETURNS SETOF record AS
        $BODY$
        DECLARE
            rec_trial    record;
        BEGIN
            for rec_trial in 
                Select  distinct bal.acc_id, bal.code, bal.name, bal.acc_level,
                
                    case when bal.begin_dr > bal.begin_cr then abs(bal.begin_dr - bal.begin_cr)
                        else 0 end begin_dr,
                    case when bal.begin_dr < bal.begin_cr then  abs(bal.begin_dr - bal.begin_cr)
                        else 0 end begin_cr,
                                
                    bal.period_dr period_dr,
                    bal.period_cr period_cr,
                    bal.ac_dr_val ac_dr,
                    bal.ac_cr_val ac_cr,
                    
                    case when (bal.begin_dr - bal.begin_cr + bal.period_dr - bal.period_cr) >= 0
                        then abs(bal.begin_dr - bal.begin_cr + bal.period_dr - bal.period_cr)
                        else 0 end end_dr,
                    case when (bal.begin_dr - bal.begin_cr + bal.period_dr - bal.period_cr) < 0
                        then  abs(bal.begin_dr - bal.begin_cr + bal.period_dr - bal.period_cr)
                        else 0 end end_cr,
                        
                    case when bal.begin_dr_2rd > bal.begin_cr_2rd then abs(bal.begin_dr_2rd - bal.begin_cr_2rd)
                        else 0 end begin_dr_2rd,
                    case when bal.begin_dr_2rd < bal.begin_cr_2rd then  abs(bal.begin_dr_2rd - bal.begin_cr_2rd)
                        else 0 end begin_cr_2rd,
                        
                    bal.period_dr_2rd period_dr_2rd,
                    bal.period_cr_2rd period_cr_2rd,
                    bal.ac_dr_2rd_val ac_dr_2rd,
                    bal.ac_cr_2rd_val ac_cr_2rd,
                    
                    case when (bal.begin_dr_2rd - bal.begin_cr_2rd + bal.period_dr_2rd - bal.period_cr_2rd) >= 0
                        then abs(bal.begin_dr_2rd - bal.begin_cr_2rd + bal.period_dr_2rd - bal.period_cr_2rd)
                        else 0 end end_dr_2rd,
                    case when (bal.begin_dr_2rd - bal.begin_cr_2rd + bal.period_dr_2rd - bal.period_cr_2rd) < 0
                        then  abs(bal.begin_dr_2rd - bal.begin_cr_2rd + bal.period_dr_2rd - bal.period_cr_2rd)
                        else 0 end end_cr_2rd
                    
                From (
                    select bal.acc_id, bal.code, bal.name, bal.acc_level, 
                        sum(bal.begin_dr) begin_dr, sum(bal.begin_cr) begin_cr,
                        sum(bal.period_dr) period_dr, sum(bal.period_cr) period_cr,
                        sum(bal.ac_dr_val) ac_dr_val, sum(bal.ac_cr_val) ac_cr_val,
                        
                        sum(bal.begin_dr_2rd) begin_dr_2rd, sum(bal.begin_cr_2rd) begin_cr_2rd,
                        sum(bal.period_dr_2rd) period_dr_2rd, sum(bal.period_cr_2rd) period_cr_2rd,
                        sum(bal.ac_dr_2rd_val) ac_dr_2rd_val, sum(bal.ac_cr_2rd_val) ac_cr_2rd_val
                    from (
                        /*    Lay so du dau ky    */
                        select acc.id acc_id, acc.code, acc.name, acc.level acc_level,
                            aml.debit begin_dr, aml.credit begin_cr, 
                            0 period_dr, 0 period_cr,
                            0 ac_dr_val, 0 ac_cr_val,
                            
                            case when aml.debit != 0 then abs(abs(aml.second_amount))::numeric 
                                else 0.0::numeric
                            end  begin_dr_2rd,
                            case when aml.credit != 0 then abs(abs(aml.second_amount))::numeric 
                                else 0.0::numeric
                            end begin_cr_2rd,
                                
                            0 period_dr_2rd, 0 period_cr_2rd,
                            0 ac_dr_2rd_val, 0 ac_cr_2rd_val
                            
                        from account_move_line aml 
                            join account_move amh on amh.id = aml.move_id and amh.state = 'posted'
                            join account_journal ajn on amh.journal_id = ajn.id and ajn.type = 'situation'
                            join account_account acc on aml.account_id = acc.id
                        where amh.company_id = $3
                            and aml.date = coalesce((select am.date
                                                        from account_move_line aml3
                                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                                and am.company_id= $3
                                                                and am.state = 'posted'
                                                        where am.date <= $2::date 
                                                        order by am.date desc
                                                        limit 1),'2000-01-01')
                                                            
                        UNION ALL
                        
                        select acc.id acc_id, acc.code, acc.name, acc.level acc_level,
                            sum(aml.debit) begin_dr, sum(aml.credit) begin_cr,
                            0 period_dr, 0 period_cr,
                            0 ac_dr_val, 0 ac_cr_val,
                            
                            sum(case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) begin_dr_2rd,
                            sum(case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) begin_cr_2rd,
                                
                            0 period_dr_2rd, 0 period_cr_2rd,
                            0 ac_dr_2rd_val, 0 ac_cr_2rd_val
                            
                        from account_move_line aml 
                            join account_move amh on amh.id = aml.move_id and amh.state = 'posted'
                            join account_journal ajn on amh.journal_id = ajn.id and ajn.type != 'situation'
                            join account_account acc on aml.account_id = acc.id
                        where amh.company_id = $3
                            and amh.journal_id = ANY($5)
                            
                            and aml.date between
                                    coalesce((select am.date
                                        from account_move_line aml3
                                            LEFT JOIN account_move am on am.id = aml3.move_id
                                                JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                and am.company_id= $3
                                                and am.state = 'posted'
                                        where am.date <= $2::date 
                                        order by am.date desc
                                        limit 1),'2000-01-01')
                                and ($1::date - 1)::date
                        group by acc.id, acc.code, acc.name, acc.level
                        
                        /*    Lay phat sinh trong ky    */
                        UNION ALL
                        
                        select acc.id acc_id, acc.code, acc.name, acc.level acc_level,
                            0 begin_dr, 0 begin_cr,
                            sum(aml.debit) period_dr, sum(aml.credit) period_cr,
                            0 ac_dr_val, 0 ac_cr_val,
                            
                            0 begin_dr_2rd, 0 begin_cr_2rd,
                            sum(case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) period_dr_2rd,
                            sum(case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) period_cr_2rd,
                                
                            0 ac_dr_2rd_val, 0 ac_cr_2rd_val
                            
                        from account_move_line aml 
                            join account_move amh on amh.id = aml.move_id 
                            join account_journal ajn on amh.journal_id = ajn.id and ajn.type != 'situation'
                            join account_account acc on aml.account_id = acc.id
                        where amh.company_id = $3
                            and amh.state = 'posted' and date(aml.date) between date($1::date) and date($2::date)
                            and amh.journal_id = ANY($5)
                            
                        group by acc.id, acc.code, acc.name, acc.level
                        
                        /*    Lay luy ke  */
                        UNION ALL
                        
                        select acc.id acc_id, acc.code, acc.name, acc.level acc_level,
                            0 begin_dr, 0 begin_cr,
                            0 period_dr, 0 period_cr,
                            sum(aml.debit) ac_dr_val, sum(aml.credit) ac_cr_val,
                            
                            0 begin_dr_2rd, 0 begin_cr_2rd,
                            0 period_dr_2rd, 0 period_cr_2rd,
                            
                            sum(case when aml.debit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) ac_dr_2rd_val,
                            sum(case when aml.credit != 0 then abs(aml.second_amount)::numeric 
                                    else 0.0::numeric
                                end) ac_cr_2rd_val
                                
                        from account_move_line aml 
                            join account_move amh on amh.id = aml.move_id and amh.state = 'posted'
                            join account_journal ajn on amh.journal_id = ajn.id and ajn.type != 'situation'
                            join account_account acc on aml.account_id = acc.id
                        where amh.company_id = $3
                            and date(aml.date) between date($4::date) and date($2::date)
                            and amh.journal_id = ANY($5)
                            
                        group by acc.id, acc.code, acc.name, acc.level
                    ) bal
                    group by bal.acc_id, bal.code, bal.name, bal.acc_level
                ) bal
                Window w as (partition by bal.acc_id)
            loop
                coa_id = rec_trial.acc_id;
                coa_code = rec_trial.code;
                coa_name = rec_trial.name;
                acc_level = rec_trial.acc_level;
                
                begin_dr = nullif(rec_trial.begin_dr,0);
                begin_cr = nullif(rec_trial.begin_cr,0);
                period_dr = nullif(rec_trial.period_dr,0);
                period_cr = nullif(rec_trial.period_cr,0);
                end_dr = nullif(rec_trial.end_dr,0);
                end_cr = nullif(rec_trial.end_cr,0);
                ac_dr = nullif(rec_trial.ac_dr,0);
                ac_cr = nullif(rec_trial.ac_cr,0);
                
                begin_dr_2rd = nullif(rec_trial.begin_dr_2rd,0);
                begin_cr_2rd = nullif(rec_trial.begin_cr_2rd,0);
                period_dr_2rd = nullif(rec_trial.period_dr_2rd,0);
                period_cr_2rd = nullif(rec_trial.period_cr_2rd,0);
                end_dr_2rd = nullif(rec_trial.end_dr_2rd,0);
                end_cr_2rd = nullif(rec_trial.end_cr_2rd,0);
                ac_dr_2rd = nullif(rec_trial.ac_dr_2rd,0);
                ac_cr_2rd = nullif(rec_trial.ac_cr_2rd,0);
                return next;
            end loop;
            
            return;
        END; $BODY$
            LANGUAGE plpgsql VOLATILE
            COST 100
            ROWS 1000;
        '''
        cr.execute(sql)
        return True  
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
