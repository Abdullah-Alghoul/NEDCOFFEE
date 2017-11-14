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

def import_asset_v9(oorpc):
    output = open(current_path + '/python/MasterSupplier - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/TSCD.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = -1
    for rownum in range(sh.nrows):
        i += 1
        if i == 0:
            continue
        row_values = sh.row_values(rownum)
        error = False
        vals = vars = {}
        asset_code = row_values[0]
        asset_name = row_values[1]
        category_name = row_values[1]
        
        account_income_recognition_id = row_values[4]
        
        date = row_values[6]
        
        value = row_values[7]
        Number_of_Depreciations = row_values[12]
        
#         if code not in ('35/TSCD','38/TSCD','39/TSCD','40/TSCD','41/TSCD','46/TSCD'):
#             continue
#         if category_name:
#             category_id = oorpc.search('account.asset.category', [('name', '=', category_name)])
        
        
        if account_income_recognition_id:
            account_income_recognition_id = oorpc.search('account.account', [('code', '=', account_income_recognition_id)])
        
        if not error:
            vals.update({
                'code':code or '',
                'name': asset_name or False, 
                'category_id':23,
                'company_id':1,
                'asset_type':'asset',
                'currency_id':3,
                'state':'draft',
                'date':str(date),
                'method_time':'number',
                'method':'linear',
                'account_income_recognition_id':account_income_recognition_id and account_income_recognition_id[0] or False,
                'method_number':'number',
                'value':value,
                'warehouse_id':1
                }) 
            try:
                new_id = oorpc.create('account.asset.asset', vals)
            except Exception, e:
                print 'code : ' + code + '\n'
                    
                    
#    output.write(err_name + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'ERP', 'admin', 'TC123321', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_asset_v9(oorpc)
    print 'Done.'
    
