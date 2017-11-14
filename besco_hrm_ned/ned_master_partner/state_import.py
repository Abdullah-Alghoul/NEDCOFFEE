# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _

import time

from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
import datetime
import base64

from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook, xldate_as_tuple

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

DATEOFFSET = 693594

class state_import(osv.osv):
    _name = 'state.import'
    
    _columns = {        
        'file': fields.binary('File', help='Choose file Excel'),
        'file_name':  fields.char('Filename', 100, readonly=True),
        
    }
    
    def read_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents=recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
#             for row in range(sh.nrows):
#                 if sh.cell(row,0).value ==u'Mã':
#                     flag = True
#                     continue
#                 if flag==True:
#                     ma = sh.cell(row,0).value
#                     tinh = sh.cell(row,1).value
#                     code = sh.cell(row,1).value
#                     country = 243
#                     res_country_state_line = { 
#                         'name': tinh,
#                         'code': code,
#                         'short_name': ma,
#                         'country_id': country,
#                     }
#                     self.pool.get('res.country.state').create(cr, uid, res_country_state_line)
            for row in range(sh.nrows):
                if sh.cell(row, 0).value == u'Tỉnh thành':
                    flag = True
                    continue
                if flag == True:
                    tinh = sh.cell(row, 0).value
                    quan = sh.cell(row, 2).value
                    
                    res_country_state_ids = self.pool.get('res.country.state').search(cr, uid, [('name', '=' , tinh)])
                    print res_country_state_ids
                    index = 0
                    for i in res_country_state_ids:
                        res_district_line = {
                            'state_id' : res_country_state_ids[index],
                            'name' : quan
                        }
                        index += 1
                    self.pool.get('res.district').create(cr, uid, res_district_line)
#                     res_country_state_line = { 
#                         'name': tinh,
#                         'code': code,
#                     }
#                     self.pool.get('res.country.state').create(cr, uid, res_country_state_line)
        return True
    
