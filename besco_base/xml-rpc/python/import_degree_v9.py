# -*- coding: utf-8 -*-

import os
import sys
from fileinput import close
os.chdir('../')
current_path = os.getcwd()
sys.path.append(current_path)
from common.oorpc import OpenObjectRPC, define_arg
import xlrd
import psycopg2

def import_bom_v9(oorpc):
    output = open(current_path + '/python/MasterBom - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/import_degree_v9.xls')
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
            mconKett = row_values[0]
            deduction = row_values[1]
            oorpc.create('degree.mc', {'mconkett': mconKett or False, 'deduction': deduction})
            print 'Create Degree: ' + str(mconKett)
                    
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
    oorpc = OpenObjectRPC('203.162.76.14', 'TRAIN_DB', 'admin', '1', '6069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_bom_v9(oorpc)
    print 'Done.'
    
