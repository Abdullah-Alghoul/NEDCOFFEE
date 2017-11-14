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
    output = open(current_path + '/python/MasterItem - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/MasterItem.xls')
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
            name = row_values[2]
            default_code = row_values[0]
            if default_code =='G18-WP1-4C':
                a= 5
            
            category = row_values[1]
            #description_for_quotations = row_values[2]
            invietnamese = row_values[3]
            moisture = row_values[4]
            foreign_matter = row_values[5]
            black_broken = row_values[6]
            broken = row_values[7]
            scr18 = row_values[8]
            scr16 = row_values[9]
            scr13 = row_values[10]
            scr12 = row_values[11]
            uscr12 = row_values[12]
            premium = row_values[13]
            active = row_values[15]
            
            if category:
                category_ids = oorpc.search('product.category', [('name', '=', category)])
                if len(category_ids) == 0:
                    error = True
                    row_values.append("Category  Category '%s'!" % (str(category)))
            
            if name:
                product_ids = oorpc.search('product.product', [('company_code', '=', default_code)])
                if product_ids:
                    oorpc.write('product.product', {'default_code': default_code})
                    continue
            if not error:
                vals = {
                    'name':name,  'categ_id':category_ids[0], 'type': 'product', 'invietnamese': invietnamese or False,
                    'sale_ok':True,
                    'company_code':default_code,
                    'default_code':default_code,
                    'property_stock_procurement': 6, 'property_stock_production': 7, 'list_price': 0.0, 'standard_price': 0.0,
                    'uom_id': 3, 'active': active, 'property_stock_inventory': 5, 'cost_method': 'average', 'sale_delay': 7.0,
                    'sale_ok': True, 'property_stock_account_output': False, 'company_id': 1, 'uom_po_id': 3, 'type': 'product',
                    'property_stock_account_input': False, 
                    'moisture': moisture or 0.0, 'foreign_matter': foreign_matter or 0.0, 'black_broken': black_broken or 0.0, 'broken': broken or 0.0,
                    'premium': premium or 0.0, 'scr18': scr18 or 0.0, 'scr16': scr16 or 0.0, 'scr13': scr13 or 0.0, 'scr12': scr12 or 0.0, 'uscr12': uscr12 or 0.0 
                    }
                product_id = oorpc.create('product.product', vals)
                
        except Exception, e:
            error = True
            row_values.append(e)
        if error:
            output.write(default_code + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'COFF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_product_v9(oorpc)
    print 'Done.'
    
