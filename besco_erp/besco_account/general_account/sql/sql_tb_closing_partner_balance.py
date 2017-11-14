# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import _

class sql_tb_closing_partner_balance(osv.osv):
    _name = "sql.tb.closing.partner.balance"
    _auto = False
    
    def init(self, cr):
        self.fi_tb_closing_partner_balance(cr)
        return True
    
    def fi_tb_closing_partner_balance(self, cr):
        sql = '''
        delete from pg_proc where proname = 'fi_tb_closing_partner_balance';
        commit;
        
        CREATE OR REPLACE FUNCTION fi_tb_closing_partner_balance(date, date, integer, integer)
          RETURNS TABLE(
            seq integer,
            partner_id integer,
            partner_code character varying(20),
            partner_name character varying(120),
            internal_type character varying(20),
            
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
                    for rec_data in
                            select  vw.partner_id, vw.partner_code, vw.partner_name, vw.internal_type,
                                    sum(beg_dr) begin_dr, sum(beg_cr) begin_cr,
                                    sum(prd_dr) period_dr, sum(prd_cr) period_cr,
                                    
                                    sum(beg_dr_2nd) begin_dr_2nd, sum(beg_cr_2nd) begin_cr_2nd,
                                    sum(prd_dr_2nd) period_dr_2nd, sum(prd_cr_2nd) period_cr_2nd
                            from (
                                    /*    Lay so du dau ky    */
                                    select rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name, ajn.internal_type, 
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
                                        and amh.company_id = $4
                                        and aml.date =
                                                coalesce((select am.date
                                                    from account_move_line aml3
                                                        LEFT JOIN account_move am on am.id = aml3.move_id
                                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                            and am.company_id= $4
                                                            and am.state = 'posted'
                                                    where am.date <= $2::date and aml3.account_id=aml.account_id
                                                    order by am.date desc
                                                    limit 1),'2000-01-01')
                                    group by rpt.id, rpt.ref, rpt.name, ajn.internal_type
                                union all
                                    select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name, ajn.internal_type,
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
                                        and ajn.type != 'situation'
                                        and aml.account_id = $3
                                        and amh.company_id = $4
                                        and aml.date between
                                                coalesce((select am.date
                                                    from account_move_line aml3
                                                        LEFT JOIN account_move am on am.id = aml3.move_id
                                                            JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                            and am.company_id= $4
                                                            and am.state = 'posted'
                                                    where am.date <= $2::date and aml3.account_id=aml.account_id
                                                    order by am.date desc
                                                    limit 1),'2000-01-01')
                                            and ($1::date - 1)::date
                                    group by rpt.id, rpt.ref, rpt.name, ajn.internal_type
                                union all
                                    /*    Lay phat sinh trong ky    */
                                    select  rpt.id as partner_id, rpt.ref as partner_code, rpt.name as partner_name, ajn.internal_type,
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
                                        join res_partner rpt on aml.partner_id = rpt.id /* lien ket voi partner */
                                        join res_company com on com.id = amh.company_id
                                    where aml.date between $1 and $2
                                        and amh.state = 'posted'
                                        and ajn.type != 'situation'
                                        and aml.account_id = $3
                                        and amh.company_id = $4
                                    group by rpt.id, rpt.ref, rpt.name, ajn.internal_type
                                ) vw
                            group by vw.partner_id, vw.partner_code, vw.partner_name, vw.internal_type
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
                        internal_type = rec_data.internal_type;
                        
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
                    return;
            END; $BODY$
              LANGUAGE plpgsql VOLATILE
              COST 100
              ROWS 1000;
        '''
        cr.execute(sql)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
