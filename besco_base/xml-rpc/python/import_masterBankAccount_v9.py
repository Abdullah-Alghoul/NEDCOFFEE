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

def import_tranfer_v9(oorpc):
    output = open(current_path + '/python/MasterShippingLine - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/tblmasterBankAccount.xls')
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
        partner_ids = False
        vals = vars = {}
        acc_number = row_values[0]
        partner_code = row_values[1]
        bank = row_values[2]
        if not acc_number:
            continue
        
        partner_ids = oorpc.search('res.partner', [('partner_code', '=', partner_code)])
        if not partner_ids:
            partner_ids = oorpc.search('res.partner', [('active','=',False),('partner_code', '=', partner_code)])
        if not partner_ids:
            print partner_code + '\n'
        
        banks_ids = oorpc.search('res.bank', [('bic', '=', bank)])
        if len(partner_ids) == 0:
            print bank + '\n'
        vals ={
               'acc_number':acc_number,
               'partner_id':partner_ids and partner_ids[0],
               'bank_id':banks_ids and banks_ids[0] or False
               }
        try:
            new_id = oorpc.create('res.partner.bank', vals)
        except Exception, e:
            print 'partner : '+acc_number+ ' - ' + partner_code + ' - ' + bank +'\n'
                
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'COFF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_tranfer_v9(oorpc)
    print 'Done.'
    
