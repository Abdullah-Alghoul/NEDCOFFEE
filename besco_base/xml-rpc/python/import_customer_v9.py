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
    output = open(current_path + '/python/MasterCustomer - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/tblmasterCustomer.xls')
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
            cusname = row_values[1]
            partner_code =row_values[0]
            if cusname:
                partner_id = oorpc.search('res.partner', [('name', '=', cusname)])
                if partner_id:
                    oorpc.write('res.partner', {'customer': True})
                    print 'Update Customer: ' + cusname
                else:
                    vals.update({'partner_code':partner_code,
                                 'name': cusname or False, 'supplier': False, 'customer': True, 
                                'company_type': 'company', 
                                'active': True,
                                'property_account_payable_id':1622,
                                'property_account_receivable_id':1509,
                                'property_vendor_advance_acc_id':1623}) 
                    new_id = oorpc.create('res.partner', vals)
                    print 'Create Customer: ' + cusname
                
        except Exception, e:
            error = True
            row_values.append(e)
        if error:
            output.write(partner_code + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'COFF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_customer_v9(oorpc)
    print 'Done.'
    
