# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models, _
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

class wizard_export_payrolls(models.TransientModel):
    _name = 'wizard.export.payrolls'
    
    department_ids = fields.Many2many('hr.department', 'export_payroll_job_rel', 'export_payroll_id', 'job_id', 'Jobs')
    start_date = fields.Date('Date From', required=True, default=lambda *a: time.strftime('%Y-%m-01'))
    end_date = fields.Date('Date To', required=True, default=lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    
    def export_wizard_payrolls(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.export.payrolls'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_payrolls' , 'datas': datas}
    
    @api.onchange('start_date', 'end_date')
    def onchange_dateheader(self):
        if self.end_date and self.start_date > self.end_date:
            self.end_date = False
            warning = {
               'title': _('Import Warning!'),
               'message' : _('Start Date must be smaller than End date !!!')
            }
            return {'warning': warning}
