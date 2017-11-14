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
    wb = xlrd.open_workbook(current_path + '/python/import_balance_sheet.xls')
    wb.sheet_names()
    sh = wb.sheet_by_index(0)
    i = -1
    new_id = False
    reports_id = False
    thuyet_minh= False
    type ='sum'
    sequence =0
    sign = -1
    for rownum in range(sh.nrows):
        row_values = sh.row_values(rownum)
        
        try:
            vals = {}
            name = row_values[0]
            if name in (u'1.1 Cổ phiếu phổ thông có quyền biểu quyết',u'1.2 Cổ phiếu ưu đãi'):
                a =5
            if not name:
                continue
            if name in (u'1',u'NGUỒN VỐN',u'CÁC CHỈ TIÊU NGOẢI BẢNG CÂN ĐỐI KẾ TOÁN'):
                continue
            if name == u'TÀI SẢN ':
                vals ={
                        'name':'BẢNG CÂN ĐỐI KẾ TOÁN - Mẫu số B 01-DN (QĐ số 15/2006/QĐ-BTC)',
                        'sign':1,
                        'type':'sum',
                        'sequence':sequence
                       }
                new_id = oorpc.create('account.financial.report', vals)
                reports_id = new_id
                sequence +=1
                continue
            
            try:
                ma_so = str(int(row_values[6]))
            except Exception, e:
                ma_so = str(row_values[6])
            thuyet_minh = row_values[7]
            
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
        
        except Exception, e:
            row_values.append(e)
        
    #########################################################
    # Cập nhật cha con
    supper_id = oorpc.search('account.financial.report', [('name', '=', u'BẢNG CÂN ĐỐI KẾ TOÁN - Mẫu số B 01-DN (QĐ số 15/2006/QĐ-BTC)')])
    
    #Chi tieu 100 A- TÀI SẢN NGẮN HẠN (100=110+120+130+140+150)
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','100')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('110','120','130','140','150'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]}) 
    
    #Chi tieu 110
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','110')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('111','112'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
     
    #Chi tieu 111
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','111')])
    account_code = ['111','112','113']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 112
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','112')])
    account_code = ['1281','1288']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 120
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','120')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('121','122','123'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
     
    #Chi tieu 121
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','121')])
    account_code = ['121']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 122
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','122')])
    account_code = ['2291']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 123
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','120')])
    account_code = ['1281','1282','1288']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 130
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','130')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('131','132','133','134','135','136','137','139'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
     
    #Chi tieu 131
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','131')])
    account_code = ['131']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 132
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','132')])
    account_code = ['331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 133
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','133')])
    account_code = ['1362','1363','1368']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 134
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','134')])
    account_code = ['337']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 135
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','135')])
    account_code = ['1283']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 136
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','136')])
    account_code = ['1385','1388','334','338','141','244']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 137
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','137')])
    account_code = ['2293']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 139
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','139')])
    account_code = ['1381']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 140
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','140')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('141','149'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
     
    #Chi tieu 141
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','141')])
    account_code = ['151','152','153','154','155','156','157','158']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 149
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','149')])
    account_code = ['2294']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 150
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','150')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('151','152','153','154','155'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
     
    #Chi tieu 151
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','151')])
    account_code = ['242']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 152
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','152')])
    account_code = ['133']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 153
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','153')])
    account_code = ['333']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 154
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','154')])
    account_code = ['171']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #Chi tieu 155
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','155')])
    account_code = ['2288']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
     
    #B- TÀI SẢN DÀI HẠN (200=210+220+240+250+260)
    #Chi tieu 200
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','200')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('210','220','230','240','250','260'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 210
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','210')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('211','212','213','214','215','216','219'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 211
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','211')])
    account_code = ['131']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 212
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','212')])
    account_code = ['331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 213
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','213')])
    account_code = ['1361']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 214
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','214')])
    account_code = ['1362','1363','1368']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 215
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','215')])
    account_code = ['1283']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 216
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','216')])
    account_code = ['1385','1388','334','338','141','244']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 219
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','219')])
    account_code = ['2293']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 220
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','220')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('221','224','227'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 221
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','221')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('222','223'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 222
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','222')])
    account_code = ['211']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 223
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','223')])
    account_code = ['2141']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 224
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','224')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('225','226'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 225
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','225')])
    account_code = ['212']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 226
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','226')])
    account_code = ['2142']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 227
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','227')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('228','229'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 228
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','228')])
    account_code = ['213']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 229
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','229')])
    account_code = ['2143']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 230
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','230')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('231','232'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 231
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','231')])
    account_code = ['217']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 232
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','232')])
    account_code = ['2147']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 240
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','240')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('241','242'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 241
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','241')])
    account_code = ['154']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 242
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','242')])
    account_code = ['242']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 250
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','250')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('251','252','253','254','255'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 251
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','251')])
    account_code = ['221']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 252
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','252')])
    account_code = ['222']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 253
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','253')])
    account_code = ['2281']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 254
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','254')])
    account_code = ['2292']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 255
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','255')])
    account_code = ['1281','1282','1288']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
     #Chi tieu 260
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','260')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('261','262','263','268'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 261
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','261')])
    account_code = ['242']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 262
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','262')])
    account_code = ['243']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 263
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','263')])
    account_code = ['1534','2294']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 268
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','263')])
    account_code = ['2288']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 270
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','270')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('100','200'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #NGUỒN VỐN
    #Chi tieu 300
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','300')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('310','330'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 310
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','310')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('311','312','313','314','315','316','317','318','319','320','321','322','323','324'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 311
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','311')])
    account_code = ['331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 312
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','312')])
    account_code = ['131']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 313
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','313')])
    account_code = ['333']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})

    #Chi tieu 314
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','314')])
    account_code = ['334']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})

    #Chi tieu 315
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','315')])
    account_code = ['335']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 316
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','316')])
    account_code = ['3362','3363','3368']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 317
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','317')])
    account_code = ['337']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 318
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','318')])
    account_code = ['3387']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 319
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','319')])
    account_code = ['338','138','344']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 320
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','320')])
    account_code = ['341','34311']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 321
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','321')])
    account_code = ['352']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 322
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','322')])
    account_code = ['353']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 323
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','323')])
    account_code = ['357']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 324
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','324')])
    account_code = ['171']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 330
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','330')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('331','332','333','334','335','336','337','338','339','340','341','342','343'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 331
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','331')])
    account_code = ['331']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 332
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','332')])
    account_code = ['131']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 333
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','333')])
    account_code = ['335']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 334
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','334')])
    account_code = ['3361']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 335
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','335')])
    account_code = ['3362','3363','3368']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 336
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','336')])
    account_code = ['3387']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 337
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','337')])
    account_code = ['338','344']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 338
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','338')])
    account_code = ['341','34311','34312','34313']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 339
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','339')])
    account_code = ['3432']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 340
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','340')])
    account_code = ['41112']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 341
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','341')])
    account_code = ['347']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 342
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','342')])
    account_code = ['352']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 343
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','343')])
    account_code = ['356']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 400
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','400')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('410','430'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 410
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','410')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('411','412','413','414','415','416','417','418','419','420','421','422'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 411
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','411')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('411a','411b'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 411a
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','411a')])
    account_code = ['41111']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 411b
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','411b')])
    account_code = ['41112']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    
    #Chi tieu 412
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','412')])
    account_code = ['4112']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 413
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','413')])
    account_code = ['4113']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 414
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','414')])
    account_code = ['4118']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 415
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','415')])
    account_code = ['419']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 416
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','416')])
    account_code = ['412']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 417
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','417')])
    account_code = ['413']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 418
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','418')])
    account_code = ['414']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 419
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','419')])
    account_code = ['417']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 420
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','420')])
    account_code = ['418']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 421
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','421')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('421a','421b'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 421a
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','421a')])
    account_code = ['4211']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 421b
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','421b')])
    account_code = ['4212']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 422
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','422')])
    account_code = ['441']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 430
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','430')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('431','432'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    #Chi tieu 431
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','431')])
    account_code = ['461','161']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 432
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','432')])
    account_code = ['466']
    account_ids= oorpc.search('account.account', [('code', 'in', account_code)])
    oorpc.write('account.financial.report',parent_ids, {'account_ids':[(6,0,account_ids)],'type':'accounts'})
    
    #Chi tieu 440
    parent_ids= oorpc.search('account.financial.report', [('report_id', '=', supper_id),('ma_so','=','440')])
    update_parent_ids = oorpc.search('account.financial.report', [('ma_so', 'in', ('300','400'))])
    oorpc.write('account.financial.report',update_parent_ids, {'parent_id': parent_ids[0]})
    
    
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
    
