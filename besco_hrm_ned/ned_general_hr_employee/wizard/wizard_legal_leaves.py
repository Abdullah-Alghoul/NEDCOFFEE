# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_legal_leaves(models.TransientModel):
    _name = 'wizard.legal.leaves'
    
    start_date = fields.Date(string="Start Date", default=fields.Datetime.now)
    end_date = fields.Date(string="End date")
    
    @api.v7
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.legal.leaves'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_holiday_leaves' , 'datas': datas} 
