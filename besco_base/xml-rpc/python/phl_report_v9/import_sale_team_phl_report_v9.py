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



def import_sale_team_phl_report(oorpc):
    output = open(current_path + '/python/phl_report_v9/Teamcode - Errors.txt', 'wb')
    wb = xlrd.open_workbook(current_path + '/python/phl_report_v9/sale_team.xls')
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
            teamcode = str(int(row_values[0]))
            sale_unit = str(row_values[1])
            sale_unit_code = str(int(row_values[2]))
            agent_number = str(int(row_values[3]))
            agent_name =  row_values[4]
            if teamcode:
                #check sale unit 
                sale_unit_ids= oorpc.search('crm.team', [('name', '=', sale_unit)])
                if sale_unit_ids:
                    #id saleunit sale_unit[0]
                    code = oorpc.search('crm.team', [('name', '=', teamcode)])
                    #check teamcode
                    #teamcode[id]
                    if code:
                        user = oorpc.search('res.users',[('login','=',agent_number)])
                        if user:
                           #check ton tai user 
                            oorpc.write('crm.team',code[0], {'member_ids': [(4, user[0])]})
                            print "Update user" + teamcode
                        else:
                            partner = oorpc.search('res.partner',[('partner_code','=',agent_number)])
                            oorpc.write('res.partner',partner[0], {'crm_sale_team': int(code[0])})
                            print 'Update partner'+ teamcode
                    else:
                        # them teamcode moi
                        user_id = oorpc.search('res.users',[('login','=',teamcode)])
                        vals.update({'name': teamcode or False, 'user_id':user_id[0] or False, 'code': teamcode or False, 'parent_id': sale_unit_ids[0] or False}) 
                        new_teamcode_team = oorpc.create('crm.team', vals)
                        
                        user = oorpc.search('res.users',[('login','=',agent_number)])
                        if user:
                           #check ton tai user 
                            oorpc.write('crm.team',new_teamcode_team, {'member_ids': [(4, user[0])]})
                            print "Create user" + teamcode
                        else:
                            partner = oorpc.search('res.partner',[('partner_code','=',agent_number)])
                            oorpc.write('res.partner',partner[0], {'crm_sale_team': int(code[0])})
                            print 'Update partner'+ teamcode
                        
                else:
                    sale_unit_id =  oorpc.search('res.users',[('login','=',sale_unit_code)])
                    value = {'name': sale_unit or False, 'user_id':sale_unit_id[0] or False, 'code': sale_unit or False} 
                    new_sale_team = oorpc.create('crm.team', value)
                    code = oorpc.search('crm.team', [('name', '=', teamcode)])
                    print 'create sale_unit'
                    #check teamcode
                    #teamcode[id]
                    if code:
                        user = oorpc.search('res.users',[('login','=',agent_number)])
                        if user:
                           #check ton tai user 
                            oorpc.write('crm.team',code[0], {'member_ids': [(4, user[0])]})
                            print "Update user" + teamcode
                        else:
                            partner = oorpc.search('res.partner',[('partner_code','=',agent_number)])
                            #code 1405
                            #partner 6861
                            oorpc.write('res.partner',partner[0], {'crm_sale_team': int(code[0])})
                            print 'Update partner'+ teamcode
                    else:
                        # them teamcode moi
                        user_id = oorpc.search('res.users',[('login','=',teamcode)])
                        vals.update({'name': teamcode or False, 'user_id':user_id[0] or False, 'code': teamcode or False, 'parent_id': sale_unit_ids[0] or False}) 
                        new_teamcode_team = oorpc.create('crm.team', vals)
                        
                        user = oorpc.search('res.users',[('login','=',agent_number)])
                        if user:
                           #check ton tai user 
                            oorpc.write('crm.team',new_teamcode_team, {'member_ids': [(4, user[0])]})
                            print "Create user" + teamcode
                        else:
                           partner = oorpc.search('res.partner',[('partner_code','=',agent_number)])
                           oorpc.write('res.partner',partner[0], {'crm_sale_team': int(code[0])})
                           print 'Update partner'+ teamcode
               
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
    import_sale_team_phl_report(oorpc)
    print 'Done.'
    
