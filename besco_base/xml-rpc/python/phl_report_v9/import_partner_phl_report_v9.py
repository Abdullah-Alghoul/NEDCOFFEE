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



def import_partner_phl_report_v9(oorpc):
    output = open(current_path + '/python/phl_report_v9/Teamcode - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/phl_report_v9/Agent_team.xls')
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
            agent_number =  str(int(row_values[7]))
            agent_name = row_values[8]
            if agent_number:
                partner_code = oorpc.search('res.partner',[('partner_code','=',agent_number)])
                if partner_code:
                    print 'Partner was exist'
                else:
                    vals.update({'partner_code':str(agent_number),'name':str(agent_name)})
                    partner_id = oorpc.create('res.partner', vals)
                    print 'Create partner: ' + str(agent_name)     
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
    import_partner_phl_report_v9(oorpc)
    print 'Done.'
    
