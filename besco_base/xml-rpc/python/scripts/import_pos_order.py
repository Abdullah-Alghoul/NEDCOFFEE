# -*- coding: utf-8 -*-

import xmlrpclib
import os
import sys
from fileinput import close
os.chdir('../')
current_path = os.getcwd()
sys.path.append(current_path)
from common.oorpc import OpenObjectRPC, define_arg
import xlrd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import psycopg2

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

db1_conn_string = "host='192.168.4.5' dbname='erp-1-2' user='openerp' password='vtopen34567'"
db2_conn_string = "host='192.168.4.7' port='5432' dbname='erp' user='openerp' password='cocomart442'"

db1_pos_order = ['po.name', 'po.pos_no', 'po.create_uid', 'po.create_date', 'po.sale_journal', 'po.shop_id', 'po.user_id',
                 'po.date_order', 'po.company_id', 'po.pricelist_id', 'po.account_analytic_id', 'po.id']
db2_pos_order = ['name', 'pos_no', 'create_uid', 'create_date', 'sale_journal', 'shop_id', 'user_id', 'date_order', 'company_id', 'pricelist_id', ' account_analytic_id'
                 , 'warehouse_id', 'pos_type', 'state']

db1_po_line = ['pol.order_id', 'pol.create_uid', 'pol.create_date', 'pol.name', 'pol.ean13', 'pol.product_id', 'pol.price_unit', 'pol.qty'
               , 'pol.discount', 'pol.company_id', 'pol.notice', 'pt.name', 'uom.name']
db2_po_line = ['line_no', 'order_id', 'create_uid', 'create_date', 'name', 'product_ean', 'product_id', 'product_uom', 'price_unit', 'qty', 'discount', 'company_id', 'notice']

order_date = '2013-06-01'
shop_name = 'CCM TAN QUY'

def import_pos_order():
    conn1 = psycopg2.connect(db1_conn_string)
    conn2 = psycopg2.connect(db2_conn_string)
    cursor1 = conn1.cursor()
    cursor2 = conn2.cursor()
    
    cursor1.execute("SELECT %s FROM pos_order po join sale_shop ss on po.shop_id=ss.id WHERE date_order::date >= '%s' and ss.name='%s'" % (','.join(map(str, db1_pos_order)), order_date, shop_name))
    old_po = cursor1.fetchall()
    for row in old_po:
        po_vals = [row[0], row[1] or '', 1, (row[3] - relativedelta(hours=7)).strftime(DATETIME_FORMAT)
                   , 35, 4, 1, (row[7] - relativedelta(hours=7)).strftime(DATETIME_FORMAT), row[8], 3, 5, 4, 'POS Order', 'draft']
        sql = '''INSERT INTO pos_order(%s)
            VALUES%s
            RETURNING id''' % (','.join(map(str, db2_pos_order)), tuple(po_vals))
        cursor2.execute(sql)
        new_po_id = cursor2.fetchone()[0]
        cursor1.execute(''' SELECT %s
                            FROM pos_order_line pol 
                                join product_product p on p.id=pol.product_id join product_template pt on p.product_tmpl_id=pt.id
                                join product_packaging pac on pac.id=pol.packaging join product_ul uom on pac.ul=uom.id
                            WHERE pol.order_id=%s''' % (','.join(map(str, db1_po_line)), row[11]))
        old_po_line = cursor1.fetchall()
        stt = 1
        for line in old_po_line:
            try:
                sql = "SELECT p.id FROM product_product p join product_template pt on p.product_tmpl_id=pt.id and pt.name='%s'" % (line[11])
                cursor2.execute(sql)
                res = cursor2.fetchone()
                p_id = res and res[0] or False
                sql = "SELECT id FROM product_uom WHERE name='%s'" % (line[12])
                cursor2.execute(sql)
                res = cursor2.fetchone()
                uom_id = res and res[0] or False
                if p_id and uom_id:
                    po_line_vals = [stt, new_po_id, 1, (line[2] - relativedelta(hours=7)).strftime(DATETIME_FORMAT), line[3], line[4], p_id, uom_id, float(line[6]), float(line[7]), float(line[8]), 1, line[10]]
                    sql = '''INSERT INTO pos_order_line(%s)
                    VALUES%s
                    RETURNING id''' % (','.join(map(str, db2_po_line)), tuple(po_line_vals))
        #            sql = sql.replace("'NULL'", "NULL")
                    cursor2.execute(sql)
                    stt += 1
            except:
                pass
        cursor2.execute('commit')
    return True

if __name__ == '__main__':
    (options, args) = define_arg()
#    oorpc = OpenObjectRPC('localhost', 'vinhthai', 'admin', 'vtadmin', '8069')
#    oorpc = OpenObjectRPC('192.168.4.7', 'erp', 'admin', 'vtadmin', '8069')
    print 'In progress ...'
    import_pos_order()
    print 'Done.'
    
    
    
    

