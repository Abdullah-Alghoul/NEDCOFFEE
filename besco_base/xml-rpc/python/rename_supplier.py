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

def import_supplier_v9(oorpc):
    output = open(current_path + '/python/MasterSupplier - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/renamecustomer.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = -1
    count = 1
    for rownum in range(sh.nrows):
        i += 1
        if i == 0:
            continue
        row_values = sh.row_values(rownum)
        partner_code = row_values[0]
        sname = row_values[1]
        shortname = row_values[2]
        if partner_code:
            partner_ids = oorpc.search('res.partner', [('partner_code', '=', partner_code)])
            if len(partner_ids) == 0:
                continue
            if shortname:
                oorpc.write('res.partner',partner_ids[0], {'shortname': shortname})
            else:
                oorpc.write('res.partner',partner_ids[0], {'active': False})

            
                    
                    
#    output.write(err_name + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('203.162.76.14qq', 'DB', 'admin', '1', '6069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_supplier_v9(oorpc)
    print 'Done.'
    
