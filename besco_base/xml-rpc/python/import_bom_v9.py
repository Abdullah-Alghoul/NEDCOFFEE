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
    wb = xlrd.open_workbook(current_path + '/python/MasterBom.xls')
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
            product = row_values[1]
            type = row_values[2]
            last_revised = row_values[3]
            name_line = row_values[4]
            work_center = row_values[5]
            production_stage = row_values[6]
            material = row_values[7]
            type_material = row_values[8]
            
            product_tmpl_id = workcenter_id = product_id = production_stage_id = False
            if product:
                product_tmpl_ids = oorpc.search('product.template', [('name', '=', product)])
                if product_tmpl_ids:
                    product_tmpl_id = product_tmpl_ids[0]
                else:
                    error = True
                    row_values.append("Check Product '%s'!" % (str(product)))
                
                product_ids = oorpc.search('product.product', [('name', '=', product)])
                if product_ids:
                    product_id = product_ids[0]
                else:
                    error = True
                    row_values.append("Check Product '%s'!" % (str(product)))
                
            if work_center: 
                workcenter_ids = oorpc.search('mrp.workcenter', [('name', '=', work_center)])
                if workcenter_ids:
                    workcenter_id = workcenter_ids[0]
                else:
                    error = True
                    row_values.append("Check Work Center '%s'!" % (str(work_center)))
            
            if production_stage:
                production_stage_ids = oorpc.search('mrp.production.stage', [('name', '=', production_stage)])
                if production_stage_ids:
                    production_stage_id = production_stage_ids[0]
                else:
                    error = True
                    row_values.append("Check Production Stage '%s'!" % (str(production_stage)))
                    
            if material:
                material_ids = oorpc.search('product.product', [('name', '=', material)])
                if material_ids:
                    material_id = material_ids[0]
                else:
                    error = True
                    row_values.append("Check Material '%s'!" % (str(material)))
            
            uom_id = oorpc.search('product.uom', [('id', '=', 3)])
            
            if not error:
                bom_id = oorpc.create('mrp.bom', {'code': str(code) or False, 'type': type, 'product_tmpl_id': product_tmpl_id or False, 'product_id': product_id,
                        'product_qty': 1, 'product_uom': uom_id[0], 'active': True})
                print 'Create BoM: ' + str(code)
                if bom_id:
                    bom_line_id = oorpc.create('mrp.bom.stage.line', {'bom_id': bom_id, 'seq': 1, 'name': str(name_line),
                          'workcenter_id': workcenter_id or False, 'production_stage_id': production_stage_id or False})
                    print 'Create BoM Line: ' + str(name_line)
                    if bom_line_id:
                        bom_line_id = oorpc.create('mrp.bom.stage.material.line', {'name': str(material) or False, 'product_id': material_id or False,
                            'product_qty': 1, 'bom_stage_line_id': bom_line_id or False, 'product_uom': uom_id[0], 'type': type_material})
                        print 'Create Material Line: ' + str(material)
                    
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
    import_bom_v9(oorpc)
    print 'Done.'
    
