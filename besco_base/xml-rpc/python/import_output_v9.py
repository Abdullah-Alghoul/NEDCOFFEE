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


def import_output_v9(oorpc):
    output = open(current_path + '/python/MasterOutput - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/MasterOutput.xls')
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
            bom = row_values[0]
            product = row_values[1]
            off_topic = row_values[2]
            
            if bom: 
                bom_ids = oorpc.search('mrp.bom', [('code', '=', bom)])
                if bom_ids:
                    bom_id = bom_ids[0]
                else:
                    error = True
                    row_values.append("Check BoM '%s'!" % (str(bom)))
            
            bom_stage_line_ids = oorpc.search('mrp.bom.stage.line', [('bom_id', '=', bom_id)])
            if bom_stage_line_ids:
                bom_stage_line_id = bom_stage_line_ids[0]
            else:
                error = True
                row_values.append("Check BoM Line '%s'!" % (str(bom)))
            
            if product:
                product_ids = oorpc.search('product.product', [('name', '=', product)])
                if product_ids:
                    product_id = product_ids[0]
                else:
                    error = True
                    row_values.append("Check Product '%s'!" % (str(product)))
            
            if off_topic:
                ot = off_topic * 100 or 0.00
            
            uom_id = oorpc.search('product.uom', [('id', '=', 3)])
            
            if not error:
                vals = {'bom_stage_line_id': bom_stage_line_id, 'product_id': product_id or False,
                        'product_qty': 1, 'product_uom': uom_id[0] or False, 'off_topic': ot or 0.00} 
                bom_id = oorpc.create('mrp.bom.stage.output.line', vals)
                print 'Create Product To Produce of BoM ' + str(bom) + ': ' + str(product)
                    
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
    oorpc = OpenObjectRPC('localhost', 'COFF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_output_v9(oorpc)
    print 'Done.'
    
