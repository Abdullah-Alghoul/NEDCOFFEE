# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_employee_leaves(models.TransientModel):
    _name = 'wizard.employee.leaves'
    
    employee_id = fields.Many2one("hr.employee", string="Employee")
    year = fields.Selection([(num, str(num)) for num in range( ((fields.datetime.now().year)-10), ((fields.datetime.now().year)+1))],string="Year")
    
    @api.v7
    def print_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.employee.leaves'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_employee_leaves' , 'datas': datas} 
    
