# -*- coding: utf-8 -*-
from openerp.osv import fields, osv

class sql_profit_loss(osv.osv):
    _name = "sql.profit.loss"
    _auto = False
    
   
    
    def get_line(self, cr, start_date, end_date, times, company_id):
        query = '''
            select * from fin_profit_loss_report('%s', '%s', '%s', %s)
        ''' %(start_date, end_date, times, company_id)
        cr.execute(query)
        return cr.dictfetchall()
    
    def init(self, cr):
#         self.fin_profit_loss_data(cr)
#         self.fin_profit_loss_report(cr)
#         
#         self.fin_second_account_balance_pl(cr)
#         self.fin_second_profit_loss_report(cr)
#         cr.commit()
        return True
    
    def fin_profit_loss_data(self, cr):
        cr.execute("select exists (select 1 from pg_type where typname = 'fin_profit_loss_data')")
        res = cr.fetchone()
        if res and res[0]:
            cr.execute('''delete from pg_type where typname = 'fin_profit_loss_data';
                            delete from pg_class where relname='fin_profit_loss_data';
                            commit;''')
        sql = '''
        CREATE TYPE fin_profit_loss_data AS
           (prior_amt1 numeric,
            curr_amt1 numeric,
            prior_amt2 numeric,
            curr_amt2 numeric,
            prior_amt3 numeric,
            curr_amt3 numeric,
            prior_amt4 numeric,
            curr_amt4 numeric,
            prior_amt5 numeric,
            curr_amt5 numeric,
            prior_amt6 numeric,
            curr_amt6 numeric,
            prior_amt7 numeric,
            curr_amt7 numeric,
            prior_amt8 numeric,
            curr_amt8 numeric,
            prior_amt9 numeric,
            curr_amt9 numeric,
            prior_amt10 numeric,
            curr_amt10 numeric,
            prior_amt11 numeric,
            curr_amt11 numeric,
            prior_amt12 numeric,
            curr_amt12 numeric,
            prior_amt13 numeric,
            curr_amt13 numeric,
            prior_amt14 numeric,
            curr_amt14 numeric,
            prior_amt15 numeric,
            curr_amt15 numeric,
            prior_amt16 numeric,
            curr_amt16 numeric,
            prior_amt17 numeric,
            curr_amt17 numeric,
            prior_amt18 numeric,
            curr_amt18 numeric,
            prior_amt71 numeric,
            curr_amt71 numeric);
        '''
        cr.execute(sql)
        return True
    
    def fin_account_balance_pl(self, cr):
#         cr.execute("select exists (select 1 from pg_proc where proname = 'fin_account_balance_pl')")
#         res = cr.fetchone()
#         if res and res[0]:
#             return True
        sql = '''
        DROP FUNCTION IF EXISTS fin_account_balance_pl(IN date, IN date, IN text, IN integer) CASCADE;
        commit;
         
        CREATE OR REPLACE FUNCTION fin_account_balance_pl(IN date, IN date, IN text, IN integer)
          RETURNS TABLE(dr_amount numeric, cr_amount numeric, dr_2rd_amount numeric, cr_2rd_amount numeric) AS
        $BODY$
        DECLARE
            rec        record;
            lst_account text = '';
        BEGIN
            lst_account = fin_get_array_accountid($3);
            
            if lst_account <> '' then
                for rec in execute '
                    select sum(aml.debit) dr_amount, sum(aml.credit) cr_amount,
                    sum(aml.debit * aml.second_ex_rate) dr_2rd_amount, sum(aml.credit * aml.second_ex_rate) cr_2rd_amount
                    from account_move amh join account_move_line aml 
                            on amh.id = aml.move_id
                            and amh.state = ''posted'' 
                            and date(aml.date) between date($1::date) and date($2::date)
                            and aml.account_id in ('||lst_account||')
                    where amh.company_id = $4' using $1, $2, $3, $4
                loop
                    dr_amount = coalesce(rec.dr_amount, 0);
                    cr_amount = coalesce(rec.cr_amount, 0);
                    RETURN NEXT;
                end loop;
            else
                dr_amount = 0;
                cr_amount = 0;
                RETURN NEXT;
            end if;
        END;$BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
        '''
        cr.execute(sql)
        return True
    
    def fin_profit_loss_report(self, cr):
#         cr.execute("select exists (select 1 from pg_proc where proname = 'fin_profit_loss_report')")
#         res = cr.fetchone()
#         if res and res[0]:
#             return True
        sql = '''
        DROP FUNCTION IF EXISTS fin_profit_loss_report(date, date, character varying, integer) CASCADE;
        commit;
        
        CREATE OR REPLACE FUNCTION fin_profit_loss_report(date, date, character varying, integer)
          RETURNS SETOF fin_profit_loss_data AS
        $BODY$
        DECLARE
            _cur_sdate    alias for $1;
            _cur_edate    alias for $2;
            _type        alias for $3;
            rec_pl        record;
            pl_data        fin_profit_loss_data%ROWTYPE;
            prior_sdate    date;
            prior_edate    date;
        BEGIN
            select * into prior_sdate,prior_edate from fn_get_prior_rangedate(_cur_sdate, _type);
            RAISE NOTICE 'Prior date range: % - %', prior_sdate, prior_edate;
            
            -- chỉ tiêu 1,2,3 (doanh thu 511)
            -- 1. lấy chỉ tiêu 02 fisrt
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '511', $4)
            loop
                pl_data.prior_amt2 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '5211,5212,5213', $4)
            loop
                pl_data.curr_amt2 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 2. lấy chỉ tiêu 03
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '5111,5112,5113,5114,5117,5118', $4)
            loop
                pl_data.prior_amt3 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '5111,5112,5113,5114,5117,5118', $4)
            loop
                pl_data.curr_amt3 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0, $4);
            end loop;
            -- 3. tính lại chỉ tiêu 01
            pl_data.prior_amt1 = pl_data.prior_amt2 + pl_data.prior_amt3;
            pl_data.curr_amt1 = pl_data.curr_amt2 + pl_data.curr_amt3;
            
            -- 4. lấy chỉ tiêu 04 (giá vốn 632)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '632', $4)
            loop
                pl_data.prior_amt4 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '632', $4)
            loop
                pl_data.curr_amt4 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 5. tính chỉ tiêu 05 (lợi nhuận gộp) 3 - 4
            pl_data.prior_amt5 = pl_data.prior_amt3 - pl_data.prior_amt4;
            pl_data.curr_amt5 = pl_data.curr_amt3 - pl_data.curr_amt4;
            
            -- 6. lấy chỉ tiêu 06 (doanh thu tai chinh 515)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '515', $4)
            loop
                pl_data.prior_amt6 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '515', $4)
            loop
                pl_data.curr_amt6 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0);
            end loop;
            
            -- 7. lấy chỉ tiêu 07 (chi phí tai chinh 635)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '635', $4)
            loop
                pl_data.prior_amt7 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '635', $4)
            loop
                pl_data.curr_amt7 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 7.1. tách chi phí lãi vay 6351
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '635', $4)
            loop
                pl_data.prior_amt71 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '635', $4)
            loop
                pl_data.curr_amt71 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            
            -- 8. lấy chỉ tiêu 08 (chi phí bán hàng 641)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '6411,6412,6413,6414,6415,6417,6418', $4)
            loop
                pl_data.prior_amt8 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '6411,6412,6413,6414,6415,6417,6418', $4)
            loop
                pl_data.curr_amt8 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 9. lấy chỉ tiêu 09 (chi phí quản lý 642)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '6421,6422,6423,6424,6425,6426,6417,6418', $4)
            loop
                pl_data.prior_amt9 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '6421,6422,6423,6424,6425,6426,6417,6418', $4)
            loop
                pl_data.curr_amt9 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 10. tính chỉ tiêu 10 (lợi nhuận thuần) 5 + 6 - 7 - 8 - 9
            pl_data.prior_amt10 = pl_data.prior_amt5 + pl_data.prior_amt6 - pl_data.prior_amt7 - pl_data.prior_amt8 - pl_data.prior_amt9;
            pl_data.curr_amt10 = pl_data.curr_amt5 + pl_data.curr_amt6 - pl_data.curr_amt7 - pl_data.curr_amt8 - pl_data.curr_amt9;
            
            -- 11. lấy chỉ tiêu 11 (thu nhập khác 711)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '711', $4)
            loop
                pl_data.prior_amt11 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '711', $4)
            loop
                pl_data.curr_amt11 = coalesce(rec_pl.dr_amount,0) - coalesce(rec_pl.cr_amount,0);
            end loop;
            -- 12. lấy chỉ tiêu 12 (chi phí khác 811)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '811', $4)
            loop
                pl_data.prior_amt12 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '811', $4)
            loop
                pl_data.curr_amt12 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 13. tính chỉ tiêu 13 (lợi nhuận khác) 11 - 12
            pl_data.prior_amt13 = pl_data.prior_amt11 - pl_data.prior_amt12;
            pl_data.curr_amt13 = pl_data.curr_amt11 - pl_data.curr_amt12;
            -- 14. tính chỉ tiêu 14 (tổng lợi nhuận trước thuế) 10 + 13
            pl_data.prior_amt14 = pl_data.prior_amt10 + pl_data.prior_amt13;
            pl_data.curr_amt14 = pl_data.curr_amt10 + pl_data.curr_amt13;
            
            -- 15. lấy chỉ tiêu 15 (thuế TNDN hiện hành 8211)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '8211', $4)
            loop
                pl_data.prior_amt15 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '8211', $4)
            loop
                pl_data.curr_amt15 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 16. lấy chỉ tiêu 16 (thuế TNDN hoan lại 8212)
            for rec_pl in select* from fin_account_balance_pl(prior_sdate, prior_edate, '8212', $4)
            loop
                pl_data.prior_amt16 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            for rec_pl in select* from fin_account_balance_pl(_cur_sdate, _cur_edate, '8212', $4)
            loop
                pl_data.curr_amt16 = coalesce(rec_pl.cr_amount,0) - coalesce(rec_pl.dr_amount,0);
            end loop;
            -- 17. tính chỉ tiêu 17 (tổng lợi nhuận sau thuế) 14 - 15 - 16
            pl_data.prior_amt17 = pl_data.prior_amt14 - pl_data.prior_amt15 - pl_data.prior_amt16;
            pl_data.curr_amt17 = pl_data.curr_amt14 - pl_data.curr_amt15 - pl_data.curr_amt16;
            -- 18. tính chỉ tiêu 18 (khong tinh)
            
            return next pl_data;
            return;
        END; $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 100
          ROWS 1000;
        '''
        cr.execute(sql)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: