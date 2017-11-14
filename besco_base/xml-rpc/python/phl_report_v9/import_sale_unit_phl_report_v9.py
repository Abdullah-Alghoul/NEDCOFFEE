# -*- coding: utf-8 -*-

import xmlrpclib
import os
import sys
from fileinput import close
os.chdir('../../')
current_path = os.getcwd()
sys.path.append(current_path)
from common.oorpc import OpenObjectRPC, define_arg
import xlrd



def import_sale_unit(oorpc):
    output = open(current_path + '/python/phl_report_v9/Teamcode - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/phl_report_v9/sale_unit.xls')
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
            login = str(int(row_values[1]))
            fullname = row_values[0]
            passwords =  str(int(row_values[2]))
            if login:
                a  = str(login)
                user_id = oorpc.search('res.users', [('login', '=', login)])
                if user_id:
                    print 'Update User: ' + str(login)
                else:
                    vals.update({'login': str(login) or False, 'name': str(fullname) or False, 'password': passwords or False,'profile_ids': [(4, 21)] or False}) 
                    new_id = oorpc.create('res.users', vals)
                    sale_unit = oorpc.create('phl.saleunit',{'name':fullname,'code':login})
                     
                    #group_user= oorpc.create('res.groups.users.rel', ({'gid': int(group_ids[0]) or False,'uid':new_id or False}))
                    print 'Create Users: ' + str(login)
                
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
    oorpc = OpenObjectRPC('localhost', 'PHL_report1', 'admin', '1', '8069')
    print 'In progress ...'
    import_sale_unit(oorpc)
    print 'Done.'
    
