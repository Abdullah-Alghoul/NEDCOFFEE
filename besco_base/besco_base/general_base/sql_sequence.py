# -*- coding: utf-8 -*-
from openerp.osv import osv, fields, expression
import logging
_logger = logging.getLogger(__name__)

class sql_sequence(osv.osv):
    _name = "sql.sequence"
    _auto = False
    
    def init(self, cr):
        #Add python into postgres
        self.add_python_language(cr)
        
        #Create Type
        self.seq_interpolation(cr)
        self.seq_generate_ean13(cr)
        self.numtab(cr)
        self.seq_generate_main(cr)
        self.seq_generate_number(cr)
        return True
    
    def add_python_language(self, cr):
        try:
            cr.execute("select exists (select 1 from pg_language where lanname = 'plpythonu')")
            res = cr.fetchone()
            if res and not res[0]:
                cr.execute('''
                BEGIN;
                
                create language plpythonu;
                
                COMMIT;
                ''')
                cr.commit()
        except:
            pass
        return True
    
    def seq_interpolation(self, cr):
        sql = '''
        DROP FUNCTION IF EXISTS seq_interpolation(character varying, date, integer) CASCADE;
        commit;
        
        CREATE OR REPLACE FUNCTION seq_interpolation(s character varying, d date, obj_id integer)
          RETURNS character varying AS
        $BODY$
            import time
            if (d is None):
                t = time.localtime() # Actually, the server is always in UTC.
            else:
                t = time.strptime(d,'%Y-%m-%d')
            
            def get_shop_code (id):
                if (id is None):
                    return ''
                
                try:
                    plan = plpy.prepare("Select code from sale_shop where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
        
            def get_warehouse_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select code from stock_warehouse where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
        
            def get_com_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select p.ref from res_company co inner join res_partner p on co.partner_id = p.id and p.id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['ref']
                except:
                    return None
                
            def get_cat_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select category_code as code from product_category where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
            
            def get_pos_cat_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select sequence from pos_category where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['sequence']
                except:
                    return None
        
            def get_analys_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select code from account_analytic_account where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
        
            def get_warehouse_type (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select type from stock_warehouse where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['type']
                except:
                    return None
            
            def get_vendor_cat_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select code::int as code from res_partner_category where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
            
            def get_voucher_amount (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select voucher_amount as amount from crm_voucher_publish where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['amount']
                except:
                    return None
            
            def get_pos_code (id):
                if (id is None):
                    return ''
                    
                try:
                    plan = plpy.prepare("Select code from pos_registration where id = $1",["int"])
                    rv = plpy.execute(plan,[id],1)
                    return rv[0]['code']
                except:
                    return None
        
            try:
                
                return (s or '') % {
                        'year':     time.strftime('%Y', t),
                        'month':     time.strftime('%m', t),
                        'day':         time.strftime('%d', t),
                        'y':         time.strftime('%y', t),
                        'doy':         time.strftime('%j', t),
                        'woy':         time.strftime('%W', t),
                        'weekday':     time.strftime('%w', t),
                        'h24':         time.strftime('%H', t),
                        'h12':         time.strftime('%I', t),
                        'min':         time.strftime('%M', t),
                        'sec':         time.strftime('%S', t),
                        'shop':     get_shop_code(obj_id),
                        'warehouse': get_warehouse_code(obj_id),
                        'com':         get_com_code(obj_id),
                        'cat':         get_cat_code(obj_id),
                        'pcat':     get_pos_cat_code(obj_id),
                        'analis':     get_analys_code(obj_id),
                        'whtype':     get_warehouse_type(obj_id),
                        'vcat':     get_vendor_cat_code(obj_id),
                        'vamount':     get_voucher_amount(obj_id),
                        'pos':        get_pos_code(obj_id)
                        }
            except:
                return None
        $BODY$
          LANGUAGE plpythonu VOLATILE
          COST 1;
        '''
        cr.execute(sql)
        return True
    
    def seq_generate_ean13(self, cr):
        sql = '''
        DROP FUNCTION IF EXISTS seq_generate_ean13(text) CASCADE;
        commit;
        
        CREATE OR REPLACE FUNCTION seq_generate_ean13(barcode text)
          RETURNS text AS
        $BODY$
            if barcode is None:
                return None
            
            if len(barcode) <> 12:
                return None
            
            total = 0
            chars = str(barcode)
            for i, c in enumerate(chars):
                total += int(c) if i % 2 == 0 else int(c) * 3
            
            check_sum = (10 - (total % 10)) % 10
            return barcode + str(check_sum)
        $BODY$
          LANGUAGE plpythonu IMMUTABLE STRICT
          COST 100;
        '''
        cr.execute(sql)
        return True
    
    def numtab(self, cr):
        cr.execute("select exists (select 1 from pg_type where typname = 'numtab')")
        res = cr.fetchone()
        if res and res[0]:
            cr.execute('''delete from pg_type where typname = 'numtab';
                            delete from pg_class where relname='numtab';
                            commit;''')
        sql = '''
        CREATE TYPE numtab AS
           (current_number integer,
            generate_code text);
        '''
        cr.execute(sql)
        return True
    
    def seq_generate_main(self, cr):
        sql = '''
        DROP FUNCTION IF EXISTS seq_generate_main(text, text, date, integer, integer, integer, integer, integer, integer, text, text, boolean, boolean) CASCADE;
        commit;
        
        CREATE OR REPLACE FUNCTION seq_generate_main(text, text, date, integer, integer, integer, integer, integer, integer, text, text, boolean, boolean)
          RETURNS SETOF numtab AS
        $BODY$
        Declare
            _prefix     alias for $1;
            _suffix        alias for $2;
            _dd            alias for $3;
            _uid        alias for $4;
            _seq_id        alias for $5;
            _padding    alias for $6;
            _step        alias for $7;
            _com_id        alias for $8;
            _txn_id        alias for $9;
            _txn_tab    alias for $10;
            _roll_rule    alias for $11;
            _isEAN        alias for $12;
            _isPOS        alias for $13;
        
            seqnum        integer;
            y            integer;
            m            integer;
            d            integer;
            gen_number    text;
            strSQL        text;
            rec         numtab%ROWTYPE;
        Begin
            y:= to_char(_dd,'YYYY')::int4;
            m:= to_char(_dd,'MM')::int4;
            d:= to_char(_dd,'DD')::int4;
            
            if _isPOS then
                strSQL := 'select coalesce(max(his.number_current),0) from ir_pos_sequence_his his
                        where his.seq_id = '||_seq_id||' and his.generate_code like ''' + " '''||coalesce(_prefix,'')||'%'' " + '''
                            and his.generate_code like ''' + " '''||'%'||coalesce(_suffix,'')||''''; " + '''
            else
                strSQL := 'select coalesce(max(his.number_current),0) from ir_sequence_his his
                        where his.seq_id = '||_seq_id||' and his.generate_code like ''' + " '''||coalesce(_prefix,'')||'%'' " + '''
                            and his.generate_code like ''' + " '''||'%'||coalesce(_suffix,'')||''''; " + '''     
            end if;
            
            case _roll_rule
                when 'Yearly' then
                    strSQL := strSQL||' and his."year" = '||y;
                when 'Monthly' then
                    strSQL := strSQL||' and his."year" = '||y||' and his."month" = '||m;
                when 'Daily' then
                    strSQL := strSQL||' and his."year" = '||y||' and his."month" = '||m||' and his."day" = '||d;
                else
                    strSQL := strSQL;
            end case;
            --    Lock table before query
            begin
                if _isPOS then
                    execute 'LOCK TABLE ir_pos_sequence_his IN SHARE ROW EXCLUSIVE MODE';
                else
                    execute 'LOCK TABLE ir_sequence_his IN SHARE ROW EXCLUSIVE MODE';
                end if;
                --    get the max number from external sequence his
                execute strSQL into seqnum;
                --    Generate the number
                rec.current_number := seqnum;
                seqnum := seqnum + _step;
                gen_number := coalesce(_prefix,'')||lpad(seqnum::text,_padding,'0')||coalesce(_suffix,'');
                
                if _isEAN then gen_number := seq_generate_ean13(gen_number); end if;
                --    Ghi lich su sinh so
                strSQL := '(create_uid,create_date,write_uid,write_date,seq_id,generate_code,
                            company_id,number_current,"day","month","year",f_key,f_table)
                            values ('||_uid||',current_timestamp,'||_uid||',current_timestamp,'||
                            _seq_id||',''' + " '''||gen_number||''' " + ''','||_com_id||','||seqnum||
                            ','||d||','||m||','||y||','||_txn_id||',''' + " '''||_txn_tab||''')'; " + '''
                if _isPOS then
                    strSQL := 'insert into ir_pos_sequence_his '||strSQL;
                else
                    strSQL := 'insert into ir_sequence_his '||strSQL;
                end if;
                -- Dong khoi transaction
                execute strSQL;
                
            exception when others then
                -- Dong khoi transaction
                rec.current_number := null;
                gen_number := null;
            end;
            rec.generate_code := gen_number;
            return next rec;
            return;
        End;
        $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 1
          ROWS 1000;
        '''
        cr.execute(sql)
        return True
    
    def seq_generate_number(self, cr):
        sql = '''
        DROP FUNCTION IF EXISTS seq_generate_number(date, integer, integer, integer, integer, text) CASCADE;
        commit;
        
        CREATE OR REPLACE FUNCTION seq_generate_number(date, integer, integer, integer, integer, text)
          RETURNS text AS
        $BODY$
        Declare
            _dd         alias for $1;
            _obj_id        alias for $2;
            _seq_id        alias for $3;
            _uid        alias for $4;
            _txn_id        alias for $5;
            _txn_tab    alias for $6;
            
            seq_prefix     text;
            seq_suffix     text;
            d            date:=_dd;
            row            record;
            rec         numtab%ROWTYPE;
        Begin
            --    1) get info from this external sequence
            begin
                select seq.* into row from ir_sequence seq where id = _seq_id and active = true;
                
                if row.date_get = 'System Date' then d := current_date; end if;
                
            exception when others then
                return null;
            end;
            
            --    2) convert the prefix interpolation and suffix interpolation
            
            seq_prefix := seq_interpolation(row.prefix,d,_obj_id);
            seq_suffix := seq_interpolation(row.suffix,d,_obj_id);
            if seq_prefix isnull then seq_prefix := ''; end if;
            if seq_suffix isnull then seq_suffix := ''; end if;
            
            --    3) generate the number & write into external sequence his
            rec := seq_generate_main (seq_prefix,seq_suffix,d,_uid,_seq_id,
                    row.padding,row.number_increment,row.company_id,
                    _txn_id,_txn_tab,row.rollback_rule,row.barcode_seq,row.pos_number_seq
                    );
            
            return rec.generate_code;
        End;
        $BODY$
          LANGUAGE plpgsql VOLATILE
          COST 1;
        '''
        cr.execute(sql)
        return True
    
sql_sequence()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
