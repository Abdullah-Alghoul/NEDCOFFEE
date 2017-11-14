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
    wb = xlrd.open_workbook(current_path + '/python/LCTT.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = -1
    new_id = False
    reports_id = False
    thuyet_minh= False
    ma_so = False
    type ='sum'
    sequence =0
    sign = -1
    for rownum in range(sh.nrows):
        row_values = sh.row_values(rownum)
        
        try:
            vals = {}
            name = row_values[0]
            if not name:
                continue
            if name in (u'1',u'NGUỒN VỐN',u'CÁC CHỈ TIÊU NGOẢI BẢNG CÂN ĐỐI KẾ TOÁN'):
                continue
            if name == u'Chỉ tiêu':
                vals ={
                        'name':u'BÁO CÁO LƯU CHUYỂN TIỀN TỆ - Mẫu số B 03-DN (QĐ số 200/2014/TT-BTC)',
                        'sign':1,
                        'type':'sum',
                        'sequence':sequence
                       }
                new_id = oorpc.create('account.financial.report', vals)
                reports_id = new_id
                sequence +=1
                continue
            if row_values[1]:
                try:
                    ma_so = str(int(row_values[1]))
                except Exception, e:
                    ma_so = str(row_values[1])
            thuyet_minh = row_values[2]
            
            vals ={
                   'name': name,
                   'thuyet_minh':thuyet_minh,
                   'parent_id':new_id,
                   'sign': sign,
                   'type':type,
                   'sequence': sequence,
                   'display_details': 'detail_flat',
                   #'account_ids':[(6,0,account_ids)],
                   'ma_so':ma_so,
                   'report_id':reports_id,
                   }
        
            oorpc.create('account.financial.report', vals)
            sequence +=1
            thuyet_minh = False
            ma_so = False
        
        except Exception, e:
            row_values.append(e)
        
    #########################################################
    # Cập nhật cha con
    supper_id = oorpc.search('account.financial.report', [('name', '=', u'BÁO CÁO LƯU CHUYỂN TIỀN TỆ - Mẫu số B 03-DN (QĐ số 200/2014/TT-BTC)')])
     
    #Chi tieu 01 A- TÀI SẢN NGẮN HẠN (100=110+120+130+140+150)
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','01')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('50'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]}) 
#     
    #Chi tieu 02
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','02')])
    account_code = ['6274','6424']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
      
    #Chi tieu 03
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','03')])
    account_code = ['111','112','113']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
      
    #Chi tieu 04
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','04')])
    account_code = ['4131','515','635']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 05
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','05')])
    account_code = ['5117','515,','711','632','635','811']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 06
    #Chi phi lai vay 6352
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','06')])
    account_code = ['6352']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 07
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','07')])
    account_code = ['356','357']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 08 Lợi nhuận kinh doanh trước những thay đổi vốn lưu động Mã số 01 + Mã số 02 + Mã số 03 + Mã số 04 + Mã số 05 + Mã số 06 + Mã số 07.
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','08')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('01','02','03','04','05','06','07'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]}) 
    
    #Chi tieu 09
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','09')])
    account_code = ['131','136','138','133','141','244','331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 10 chua duoc ???
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','10')])
    account_code = ['131','136','138','133','141','244','331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 11 chua duoc ???
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','11')])
    account_code = ['131','136','138','133','141','244','331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    
    exception_code = ['3334']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 12 chua duoc ???
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','12')])
    account_code = ['242']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    
    #Chi tieu 13 chua duoc ???
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','13')])
    account_code = ['242']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    
     
    
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'CF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_product_v9(oorpc)
    print 'Done.'
    
