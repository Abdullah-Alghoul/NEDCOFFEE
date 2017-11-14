 # -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models


class wizard_wageup_contract(models.TransientModel):
    _name = 'wizard.wageup.contract'
    
    employee_ids = fields.Many2many('hr.employee', 'wizard_wageup_contract_employee_rel', 'wizard_wageup_contract_id', 'employee_id', 'Employees')
    
    def report_wizard_wageup_contract(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.wageup.contract'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_import_wageup_contract' , 'datas': datas}
