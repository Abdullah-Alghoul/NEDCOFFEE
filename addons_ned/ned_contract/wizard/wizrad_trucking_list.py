# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizrad_trucking_list(models.TransientModel):
    _name = "wizard.trucking.list"
    
    
    @api.multi
    def button_report(self):
        datas = {'ids': self._context.get('active_ids') or False}
        datas['model'] = self._context.get('active_ids') or False
        datas['form'] = self.read(self)[0]
        report_name = 'trucking_list_report'
        return {'type': 'ir.actions.report.xml', 'report_name': report_name , 'datas': datas}
