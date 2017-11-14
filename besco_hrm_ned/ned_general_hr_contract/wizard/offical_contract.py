 # -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models


class wizard_offical_contract(models.TransientModel):
    _name = 'wizard.offical.contract'
    
    employee_ids = fields.Many2many('hr.employee', 'wizard_off_contract_employee_rel', 'wizard_off_contract_id', 'employee_id', 'Employees')
    
    def report_wizard_offical_contract(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.offical.contract'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_import_offical_contract' , 'datas': datas}
