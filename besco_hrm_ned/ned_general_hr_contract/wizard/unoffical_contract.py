 # -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models


class wizard_unoffical_contract(models.TransientModel):
    _name = 'wizard.unoffical.contract'
    
    employee_ids = fields.Many2many('hr.employee', 'wizard_unoff_contract_employee_rel', 'wizard_unoff_contract_id', 'employee_id', 'Employees')
    
    def report_wizard_unoffical_contract(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.unoffical.contract'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_import_unoffical_contract' , 'datas': datas}
