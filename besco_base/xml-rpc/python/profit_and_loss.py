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
    output = open(current_path + '/python/Profit and Loss - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/Profit and Loss.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = 0
    new_id = False
    reports_id = False
    flag = False
    thuyet_minh= False
    type ='accounts'
    sequence =0
    ma_so =False
    while i<19:
        error = False
        try:
            vals = vars = {}
            if i ==0:
                vals ={
                        'name':'BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH - Mẫu số B 02 - DN (QĐ số 15/2006/QĐ-BTC)',
                        'sign':1,
                        'type':'sum',
                        'sequence':sequence
                       }
                new_id = oorpc.create('account.financial.report', vals)
                reports_id = new_id
                sequence +=1
                if not new_id:
                    raise 
            
            if i == 1:
                # Chỉ tiêu 01.Doanh thu bán hàng và cung cấp dịch vụ
                account_code = ['511','512']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Doanh thu bán hàng và cung cấp dịch vụ'
                thuyet_minh = 'V.25'
                ma_so = '01'
                
            if i == 2:
                # Chỉ tiêu 02.Các khoản giảm trừ doanh thu
                account_code = ['511','521','333']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Các khoản giảm trừ doanh thu'
                ma_so = '02'
            
            if i == 3:
                # Chỉ tiêu 10.Doanh thu thuần về bán hàng và cung cấp dịch vụ
                type = 'sum'
                sign = -1
                flag =True
                name = u'Doanh thu thuần về bán hàng và cung cấp dịch vụ (10=01-02)'
                ma_so = '10'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('01','02'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                
                sequence +=1
                flag = False
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
            
            if i == 4:
                # Chỉ tiêu 11.Giá vốn hàng bán
                account_code = ['632']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Giá vốn hàng bán'
                thuyet_minh = 'V.27'
                ma_so = '11'
            
            if i == 5:
                # Chỉ tiêu 20.Lợi nhuận gộp về bán hàng và cung cấp dịch vụ
                type = 'sum'
                sign = -1
                name = u'Lợi nhuận gộp về bán hàng và cung cấp dịch vụ (20=10-11)'
                ma_so = '20'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('10','11'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                
                sequence +=1
                flag = False
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
            
            if i == 6:
                # Chỉ tiêu 21.Doanh thu hoạt động tài chính
                account_code = ['515','5154']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Doanh thu hoạt động tài chính'
                thuyet_minh = 'V.26'
                ma_so = '21'
            
            if i == 7:
                # Chỉ tiêu 22.Chi phí tài chính
                account_code = ['635']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí tài chính'
                thuyet_minh = 'V.28'
                ma_so = '22'
            
            if i == 8:
                # Chỉ tiêu 23.Chi phí lãi vay
                account_code = ['6352']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí lãi vay'
                ma_so = '23'
            
            if i == 9:
                # Chỉ tiêu 24.Chi phí bán hàng
                account_code = ['641']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí bán hàng'
                ma_so = '24'
            
            if i == 10:
                # Chỉ tiêu 25.Chi phí quản lý doanh nghiệp
                account_code = ['642']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí quản lý doanh nghiệp'
                ma_so = '25'
                
            if i == 11:
                # Chỉ tiêu 30.Lợi nhuận thuần từ hoạt động kinh doanh
                type = 'sum'
                sign = -1
                flag =True
                name = u'Lợi nhuận thuần từ hoạt động kinh doanh  (30=20+21-22-24-25)'
                ma_so = '30'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('20','21','22','24','25'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                sequence +=1
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
                
            
            if i == 12:
                # Chỉ tiêu 31.Thu nhập khác
                account_code = ['711']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Thu nhập khác'
                ma_so = '31'
            
            if i == 13:
                # Chỉ tiêu 32. Chi phí khác
                account_code = ['811']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí khác'
                ma_so = '32'
            
            if i == 14:
                # Chỉ tiêu 40.Lợi nhuận khác (40=31-32)
                type = 'sum'
                sign = -1
                flag =True
                name = u'Lợi nhuận khác (40=31-32)'
                ma_so = '40'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('31','32'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                sequence +=1
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
                
            if i == 15:
                # Chỉ tiêu 50.Tổng lợi nhuận kế toán trước thuế (50=30+40)
                type = 'sum'
                sign = -1
                flag =True
                name = u'Tổng lợi nhuận kế toán trước thuế'
                ma_so = '50'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('30','40'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                sequence +=1
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
            
                
            if i == 16:
                # Chỉ tiêu 51.Chi phí thuế thu nhập doanh nghiệp hiện hành
                account_code = ['8211']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí thuế thu nhập doanh nghiệp hiện hành'
                ma_so = '51'
            
            if i == 17:
                # Chỉ tiêu 52.Chi phí thuế thu nhập doanh nghiệp hoãn lại
                account_code = ['8212']
                account_ids= oorpc.search('account.account', [('report_id', '=', new_id),('code', 'in', account_code)])
                sign = -1
                flag =True
                name = u'Chi phí thuế thu nhập doanh nghiệp hoãn lại'
                ma_so = '52'
            
            if i == 18:
                # Chỉ tiêu 60.Lợi nhuận sau thuế thu nhập doanh nghiệp (60=50-51-52)
                type = 'sum'
                sign = -1
                flag =True
                name = u'Lợi nhuận sau thuế thu nhập doanh nghiệp'
                ma_so = '60'
                
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                
                parent_id = oorpc.create('account.financial.report', vals)
                report_id = oorpc.search('account.financial.report', [('report_id', '=', new_id),('ma_so', 'in', ('50','51','52'))])
                oorpc.write('account.financial.report',report_id, {'parent_id': parent_id})
                sequence +=1
                type ='accounts'
                thuyet_minh = False
                i += 1
                continue
            
            if i == 19:
                # Chỉ tiêu 70.Lãi cơ bản trên cổ phiếu
                type = 'sum'
                sign = -1
                flag =True
                name = u'Lãi cơ bản trên cổ phiếu'
                ma_so = '70'
                
            if flag:
                vals ={
                       'name': name,
                       'thuyet_minh':thuyet_minh,
                       'parent_id':new_id,
                       'sign': sign,
                       'type':type,
                       'sequence': sequence,
                       'display_details': 'detail_flat',
                       'account_ids':[(6,0,account_ids)],
                       'ma_so':ma_so,
                       'report_id':reports_id
                       }
                
                oorpc.create('account.financial.report', vals)
                sequence +=1
                flag = False
                type ='accounts'
                thuyet_minh = False
            i += 1
                
        except Exception, e:
            error = True
        if error:
            output.write(str(row_values) + '\n')
    return True

# import psycopg2
# db1_conn_string = "host='localhost' port='5432' dbname='BM_1' user='openerp' password='cocomart442'"

if __name__ == '__main__':
    (options, args) = define_arg()
    oorpc = OpenObjectRPC('localhost', 'CF', 'admin', '1', '8069')
#     oorpc = OpenObjectRPC('210.245.34.65', 'BM', 'admin', '@dmin123', '8069')
    print 'In progress ...'
    import_tranfer_v9(oorpc)
    print 'Done.'
    
