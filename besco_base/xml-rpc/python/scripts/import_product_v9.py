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

def import_product_v9(oorpc):
    output = open(current_path + '/python/BANG GIA BAN CANTIN FULL IMPORT - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/BANG GIA BAN CANTIN FULL IMPORT.xls')
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
            vals = {}
            barcode = row_values[0]
            if isinstance(barcode, float):
                barcode = int(barcode)
                barcode = str(barcode)
            if isinstance(barcode, str):
                barcode = barcode.split("'")
                if len(barcode) > 1:
                    barcode = barcode[1]
                else:
                    barcode = barcode[0]
                
            if barcode:
                product_ids = oorpc.search('product.template', [('barcode', '=', barcode)])
                if not len(product_ids):
                    if row_values[2]:
                        uom_ids = oorpc.search('product.uom', [('name', '=', row_values[2])])
                        if not len(uom_ids):
                            error = True
                            row_values.append("No UoM '%s' defined in new system!" % (row_values[2]))
                             
                    if not error:
                        vals.update({
                                'barcode':barcode,
                                'name':row_values[1],
                                'uom_id': uom_ids[0],
                                'uom_po_id': uom_ids[0],
                                'categ_id': 14,
                                'pos_categ_id': 4,
                                'standard_price': row_values[4],
                                'list_price': row_values[5],
                                'type': 'product',
                                })
                        oorpc.create('product.template', vals)
                        print 'Create: ' + str(count)
                        count += 1
                else:
                    p = oorpc.read('product.template', product_ids[0], ['list_price'])
                    
                    vals.update({
                            'standard_price': row_values[4],
                            'list_price': row_values[5],
                            'standard_price': row_values[4],
                            })
                    oorpc.write('product.template', product_ids, vals)
                        
                    print 'Update: ' + str(len(product_ids)) + ' - ' + str(p['list_price']) + ' -> ' + str(row_values[5]) + ' - ' + str(count)
                    count += 1
            else:
                error = True
                
            if error:
                row_values.append("Product Barcode Code '%s' was exist in new system!" % (barcode))
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
#     oorpc = OpenObjectRPC('localhost', 'BM', 'admin', '@dmin123', '8069')
    oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_product_v9(oorpc)
    print 'Done.'
    
    
    
    

