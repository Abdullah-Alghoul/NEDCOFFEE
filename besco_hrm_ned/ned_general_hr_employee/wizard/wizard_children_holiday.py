# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_children_holiday(models.TransientModel):
    _name = 'wizard.children.holiday'
    
    date = fields.Date(string="Date", default=fields.Datetime.now)
    company_price = fields.Float('Company Price')
    union_price = fields.Float('Union Price')
    
    @api.v7
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.children.holiday'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_children_holiday' , 'datas': datas} 
