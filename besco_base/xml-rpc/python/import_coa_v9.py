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

def import_customer_v9(oorpc):
    output = open(current_path + '/python/COA - Errors.txt', 'wb')
    #wb = xlrd.open_workbook(current_path + '/python/coa.xls')
    wb = xlrd.open_workbook(current_path + '/python/MasterCoa.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = -1
    count = 1
    for rownum in range(sh.nrows):
        i += 1
        if i == 0:
            continue
        row_values = sh.row_values(rownum)
        error = False
        try:
            vals = vars = {}
            code = row_values[0]
            account_name = row_values[1]
            type = row_values[2]
            parent = row_values[3] or False
            if parent != '0_ROOT':
                parent = int(parent)
            account_type = row_values[4]
            account_type_id =oorpc.search('account.account.type', [('name', '=', account_type)]) or False
            account_type_id = account_type_id and account_type_id[0] or False
            parent_id = oorpc.search('account.account', [('code', '=', parent)]) or False
            parent_id = parent_id and parent_id[0] or False
            if type in('payable','receivable','Receivable'):
                reconcile = True
            else:
                reconcile = False
            if code != '0_ROOT':
                code = int(code)
            vals ={
                   'reconcile':reconcile,
                   'code':code,
                   'name':account_name,
                   'type':type,
                   'parent_id':parent_id,
                   'user_type_id':account_type_id
                   }
            new_id = oorpc.create('account.account', vals)
            print 'Create Account: ' + str(code)
                
        except Exception, e:
            error = True
            row_values.append(e)
        if error:
            output.write(str(row_values) + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'NED', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_customer_v9(oorpc)
    print 'Done.'
    
