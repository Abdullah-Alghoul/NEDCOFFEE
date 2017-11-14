# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################
from openerp import api, fields, models, _, SUPERUSER_ID
from openerp.exceptions import UserError
import xlrd
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_base'))

class system_sequence(models.Model):
    _name = "system.sequence"
    _description = "System Sequence"
    
    product_code = fields.Many2one('ir.sequence', string='Product Code')
    product_barcode = fields.Many2one('ir.sequence', string='Product Barcode')
    finished_good_code = fields.Many2one('ir.sequence', string='Finished Good Code')
    material_code = fields.Many2one('ir.sequence', string='Material Code')
    semi_finished_good_code = fields.Many2one('ir.sequence', string='Semi Finished Good Code')
    consumable_item_code = fields.Many2one('ir.sequence', string='Consumable Item Code')
    tools_code = fields.Many2one('ir.sequence', string='Tools Code')
    partner_code = fields.Many2one('ir.sequence', string='Partner Code')
    
    warehouse_code = fields.Many2one('ir.sequence', string='Warehouse Code')
    location_code = fields.Many2one('ir.sequence', string='Location Code')
    employee_code = fields.Many2one('ir.sequence', string='Employee Code')
    contract_code = fields.Many2one('ir.sequence', string='Contract Code')
    asset_code = fields.Many2one('ir.sequence', string='Asset Code')
    prepaid_expense_code = fields.Many2one('ir.sequence', string='Prepaid Expense Code')
    
    
    def get_current_sequence(self, cr, field_name):
        exist_ids = self.search(cr, SUPERUSER_ID, [])
        if len(exist_ids):
            sys_sequence_id = exist_ids[0]
        else:
            sys_sequence_id = self.init(cr)
        print sys_sequence_id
        sequence = self.browse(cr, SUPERUSER_ID, sys_sequence_id)[field_name]
        if sequence:
            return sequence.next_by_id()
        else:
            raise UserError(_("No sequence defined for '%s' in System Sequence. Please contact your administrator.")%(field_name))
        
    def init(self, cr):
        sequence_obj = self.pool.get('ir.sequence')
        
        sys_sequence_ids = self.search(cr, SUPERUSER_ID, [])
        if not len(sys_sequence_ids):
            sys_sequence_id = self.create(cr, SUPERUSER_ID, {})
        else:
            sys_sequence_id = sys_sequence_ids[0]
            
        wb = xlrd.open_workbook(base_path + '/general_base/data/import_sequence.xls')
        wb.sheet_names()
        sh = wb.sheet_by_index(0)
        for rownum in range(sh.nrows):
            if rownum > 0:
                row_values = sh.row_values(rownum)
                try:
                    sequence_ids = sequence_obj.search(cr, SUPERUSER_ID, [('code','=',row_values[1])])
                    if not len(sequence_ids):
                        number = float(row_values[4])
                        number = int(number)
                        
                        res = {'name': row_values[0], 'code':row_values[1], 
                               'padding': row_values[3], 'prefix': row_values[2],
                               'number_next': number}
                        new_id = sequence_obj.create(cr, SUPERUSER_ID, res)
                        
                        if row_values[1] == 'product_code':
                            cr.execute('UPDATE system_sequence SET product_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'finished_code':
                            cr.execute('UPDATE system_sequence SET finished_good_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'material_code':
                            cr.execute('UPDATE system_sequence SET material_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'semi_code':
                            cr.execute('UPDATE system_sequence SET semi_finished_good_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'consumable_code':
                            cr.execute('UPDATE system_sequence SET consumable_item_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'tools_code':
                            cr.execute('UPDATE system_sequence SET tools_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'customer_code':
                            cr.execute('UPDATE system_sequence SET customer_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'supplier_code':
                            cr.execute('UPDATE system_sequence SET supplier_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'contact_code':
                            cr.execute('UPDATE system_sequence SET contact_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'product_barcode':
                            cr.execute('UPDATE system_sequence SET product_barcode=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'employee_code':
                            cr.execute('UPDATE system_sequence SET employee_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                        elif row_values[1] == 'contract_code':
                            cr.execute('UPDATE system_sequence SET contract_code=%s WHERE id=%s'%(new_id, sys_sequence_id))
                except Exception, e:
                    continue
        return sys_sequence_id