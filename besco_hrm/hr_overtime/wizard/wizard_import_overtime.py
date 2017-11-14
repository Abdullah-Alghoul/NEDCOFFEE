# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools

from openerp.osv import osv
from openerp.tools.translate import _

from openerp.exceptions import UserError

import base64
from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook, xldate_as_tuple

class wizard_import_overtime(models.TransientModel):
    _name = 'wizard.import.overtime'
    
    file = fields.Binary('File', help='Choose file Excel')
    file_name = fields.Char('Filename', readonly=True)
    
    def import_wizard_overtime(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        flag = False
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents=recordlist)
            lst_sheet = excel.sheet_names()
            sh = excel.sheet_by_index(0)
            if len(lst_sheet) > 1:
                sh2 = excel.sheet_by_index(1)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            this_emp_code = ''
            this_line_id = 0
            num_of_rows = sh.nrows
            num_of_cols = sh.ncols
            for row in range(num_of_rows):
                if sh.cell(row, 0).value == u'STT':
                    flag = True
                    continue
                if flag == True:
                    emp_code = sh.cell(row, 1).value
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code', '=', emp_code)])
                    if not len(employee_ids):
                        raise UserError(_("Employee '%s' does not exist in system" % (emp_code)))
                    
                    emp_code = sh.cell(row, 1).value
                    decription = sh.cell(row, 4).value
                     
                    employee_ids = self.pool.get('hr.employee').search(cr, uid, [('code', '=', emp_code)])
                    emp_pool = self.pool.get('hr.employee')
                    emp_ids = emp_pool.search(cr, uid, [('code', '=', emp_code)])
                    emp_obj = emp_pool.browse(cr, uid, emp_ids[0])
                    
                    if emp_code:
                        for col in range(5, num_of_cols):
                            overtime_name = sh.cell(7, col).value
                            overtime_value = sh.cell(row, col).value
                            if overtime_value:
                                overtime_type_ids = self.pool.get('hr.overtime.type').search(cr, uid, [('name', '=', overtime_name)])
                                overtime_type_obj = self.pool.get('hr.overtime.type').browse(cr, uid, overtime_type_ids[0])
                                
                                overtime = { 
                                    'employee_id': employee_ids[0],
                                    'department_id': emp_obj.department_id.id,
                                    'name': decription,
                                    'overtime_type_id': overtime_type_ids[0],
                                    'rate': overtime_type_obj.rate,
                                    'number_of_hours_temp': overtime_value,
                                    'state': 'validate1',
                                }
                                id = self.pool.get('hr.overtime').create(cr, uid, overtime)
                                overtime_type_obj = self.pool.get('hr.overtime').overtime_validate(cr, uid, id)
                                overtime_type_obj = self.pool.get('hr.overtime').overtime_validate2(cr, uid, id)
                                
        return True 
    
    def export_wizard_overtime(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.import.overtime'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_overtime_requests' , 'datas': datas}
        
