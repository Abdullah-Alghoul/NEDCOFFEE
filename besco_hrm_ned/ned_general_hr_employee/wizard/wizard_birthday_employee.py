# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_birthday_employee(models.TransientModel):
    _name = 'wizard.birthday.employee'
    
    date = fields.Date(string="Date", default=fields.Datetime.now)
    
    @api.v7
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.birthday.employee'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_birthday_employee' , 'datas': datas} 
