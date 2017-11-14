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
    wb = xlrd.open_workbook(current_path + '/python/tblmasterSupplier.xls')
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
        err_name = ''
        vals = vars = {}
        partner_code = row_values[0]
        sname = row_values[1]
        type = row_values[2]
        repperson1 = row_values[3]
        repperson2 = row_values[4]
        goods = row_values[5]
        ppkg = row_values[6]
        estimated_annual_volume = row_values[7]
        purchase_undelivered_limit = row_values[8]
        property_evaluation = row_values[9]
        remark = row_values[10]
        province = row_values[11]
        district = row_values[12]
        address = row_values[13]
        representative = row_values[14]
        designation = row_values[15]
        tel = row_values[16]
        fax = row_values[17]
        mail = row_values[18]
        mobile = row_values[19]
        taxcode = row_values[20]
        active = int(row_values[21])
        m2mlimit = row_values[22]
#             if partner_code not in ('BM-46','CK-13','CK-17','CK-19','CM-37','CM-38','CM-46','CM-47','CM-49','DN-16','EK-07','EK-08','KP-02','KP-14'):
#                 continue
#                 a = 5
        if partner_code:
            partner_ids = oorpc.search('res.partner', [('partner_code', '=', partner_code)])
            if len(partner_ids) != 0:
                continue
        if taxcode:
            partner_ids = oorpc.search('res.partner', [('vat', '=', taxcode)])
            if len(partner_ids) != 0:
                row_values.append("VAT '%s' was exist!" % (taxcode))
                
        if province:
            state_id = oorpc.search('res.country.state', [('name', '=', province)])
            if not state_id:
                row_values.append("Check state '%s'!" % (province))
            
        if district:
            district_id = oorpc.search('res.district', [('name', '=', district)])
            if not district_id:
                district_id = oorpc.create('res.district', {'name': district, 'state_id': state_id[0]})
            else:
                district_id = district_id[0]
                
        if type:
            if type == u'Thường': 
                type_ned = 'normal'
            elif type == u'Điểm LK': 
                type_ned = 'partner'
            else:
                type_ned = 'normal'
                
        if goods:
            if goods == 'FAQ':
                goods = 'faq'
            elif goods == 'GRADE':
                goods = 'grade'

        
        if not error:
            vals.update({
                'name': sname or False, 
                'partner_code':partner_code,
                'supplier': True, 
                'customer': False, 
                'parent_id': False, 
                'company_type': 'company',
                'type': False,
                'street': address or False, 
                'state_id': state_id and state_id[0] or False, 
                'type_ned': type_ned or False,
                'repperson1': repperson1 or False, 
                'repperson2': repperson2 or False,
                'goods': goods or False, 'ppkg': ppkg or 0.0,
                'property_evaluation': property_evaluation or 0.0, 
                'customer': False, 
                'estimated_annual_volume': estimated_annual_volume or 0.0,
                'purchase_undelivered_limit': purchase_undelivered_limit or 0.0, 
                'comment':remark or False, 
                'street': address or False, 
                'fax': fax or False, 
                'phone': tel or False, 
                'vat': taxcode or False,
                'property_account_payable_id':1622,
                'property_account_receivable_id':1509,
                'property_vendor_advance_acc_id':1623,
                'property_purchase_currency_id':24,
                'mobile': mobile or False, 
                'm2mlimit': m2mlimit or 0.0,
                'active':active
                }) 
            err_name = partner_code or ''
            try:
                new_id = oorpc.create('res.partner', vals)
            except Exception, e:
                print 'partner : ' + partner_code + '\n'
            if new_id and representative: 
                vars.update({
                             'mobile':False,
                             'phone':False,
                             'property_account_receivable_id':False,
                             'property_account_payable_id':False,
                             'property_purchase_currency_id':False,
                             'purchase_undelivered_limit':False,
                             'type_ned':False,'partner_code':False,'name': representative or False, 'supplier': False, 'customer': False, 'parent_id': new_id, 'function': designation or False,
                    'company_type': 'person', 'type': 'contact', 'street': address or False, 'state_id': state_id and state_id[0] or False, 'district_id': district_id or False,
                    'active': active})
                err_name = representative or ''
                
                try:
                    oorpc.create('res.partner', vars)
                except Exception, e:
                    print 'contract : ' + representative +'\n'
                    
                    
#    output.write(err_name + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'COFF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_supplier_v9(oorpc)
    print 'Done.'
    
