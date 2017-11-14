# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models, _
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class wizard_export_payslips(models.TransientModel):
    _name = 'wizard.export.payslips'
    
    type_report = fields.Selection([('manager', 'Manager'),('officier', 'Officier'),('worker', 'Worker')], string="Type", required=True)
    date_from = fields.Date('Date From', required=True, default=lambda *a: time.strftime('%Y-%m-25'))
    date_to = fields.Date('Date To', required=True)
    
    @api.onchange('date_from')
    def _onchange_date(self):
        for payslip in self:
            date_from = datetime.strptime(payslip.date_from, '%Y-%m-%d').date()
            day = float(date_from.strftime('%d'))
            if day > 25:
                start_date = str(date_from + relativedelta.relativedelta(day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(months=+1, day=25)) or False
            else:
                start_date = str(date_from + relativedelta.relativedelta(months=-1, day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(day=25)) or False
                
            payslip.update({'date_from': datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) or False,
                               'date_to': datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) or False})
    
    def export_wizard_payslips(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.export.payslips'
        datas['form'] = self.read(cr, uid, ids)[0]
        if this.type_report == 'manager':
            return {'type': 'ir.actions.report.xml', 'report_name': 'report_payslip_manager_ned' , 'datas': datas}
        if this.type_report == 'officier':
            return {'type': 'ir.actions.report.xml', 'report_name': 'report_payslip_officier_ned' , 'datas': datas}
        if this.type_report == 'worker':
            return {'type': 'ir.actions.report.xml', 'report_name': 'report_payslip_worker_ned' , 'datas': datas}
    
    @api.onchange('start_date', 'end_date')
    def onchange_dateheader(self):
        if self.end_date and self.start_date > self.end_date:
            self.end_date = False
            warning = {
               'title': _('Import Warning!'),
               'message' : _('Start Date must be smaller than End date !!!')
            }
            return {'warning': warning}