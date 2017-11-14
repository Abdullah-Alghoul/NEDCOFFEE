# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class wizard_export_general_timesheet(models.TransientModel):
    _name = 'wizard.export.general.timesheet'
    
    @api.onchange('date_from','date_to')
    def _compute_time_scope(self):
        for m in self:
            if not m.date_from and not m.date_to:
                continue
            date_from = datetime.strptime(m.date_from[0:10], '%Y-%m-%d').date()
            day = float(date_from.strftime('%d'))
            if day > 25:
                start_date = str(date_from + relativedelta.relativedelta(day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(months=+1, day=25)) or False
            else:
                start_date = str(date_from + relativedelta.relativedelta(months=-1, day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(day=25)) or False

            m.date_from = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) or False
            m.date_to = datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) or False

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')


    def export_wizard_general_timesheet(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.export.general.timesheet'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_general_timesheet', 'datas': datas}
