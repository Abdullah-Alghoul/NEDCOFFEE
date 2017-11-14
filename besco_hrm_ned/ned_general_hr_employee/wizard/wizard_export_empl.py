 # -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models


class WizardExportDataHr(models.TransientModel):
    _name = 'wizard.export.data.hr'
    
    type = fields.Selection([('1', u'Employee'), 
                             ('2', u'Contract')], 'Report Type', required=True)
    
    
    @api.multi
    def print_report(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'wizard.export.data.hr'
        data['form'] = self.read([])[0]
        if self.type == '1':
            return {'type': 'ir.actions.report.xml', 'report_name': 'report_export_empls' , 'datas': data}
        else:
            return {'type': 'ir.actions.report.xml', 'report_name': 'report_export_contracts' , 'datas': data}
