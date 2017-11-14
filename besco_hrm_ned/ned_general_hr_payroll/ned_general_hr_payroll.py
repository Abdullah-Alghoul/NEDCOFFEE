# -*- coding: utf-8 -*-
from operator import itemgetter

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from dateutil import relativedelta
import time

import base64
from tempfile import TemporaryFile
import xlrd
from xlrd import open_workbook, xldate_as_tuple
from _sqlite3 import Row
from lxml import etree

class hr_payslip(models.Model):
    _inherit = "hr.payslip"
    
#     @api.model
#     def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
#         print "do6666666666 truoc"
#         context = self._context
#         ids = []
#         res = super(hr_payslip, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
#         if view_type in ['form']:
#             doc = etree.XML(res['arch'])
#              
#             for node in doc.xpath("//field[@name='employee_id']"):
# #                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_68z"):
# #                     employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','in',('TZ0068Z', 'TZ0076Z'))])
# #                     node.set('domain', "[('id','in',"+str(employee_ids)+")]")
#                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_76z"):
#                     print "do6666666666 form"
#                     employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0076Z')])
#                     node.set('domain', "[('id','in',"+str(employee_ids)+")]")
#                 
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         if view_type in ['tree']:
#             doc = etree.XML(res['arch'])
#             for node in doc.xpath("//field[@name='employee_id']"):
#                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_76z"):
#                     print "do6666666666 tree"
#                     employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0076Z')])
#                     print employee_ids
#                     node.set('domain', "[('employee_id','in',"+str(employee_ids)+")]")
#                  
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res
    
    @api.model
    def _default_date_from(self):
        today = datetime.now().date()
        day = float(today.strftime('%d'))
        if day > 25:
            date_from = str(today + relativedelta.relativedelta(day=26)) or False
        else:
            date_from = str(today + relativedelta.relativedelta(months=-1, day=26)) or False
        return date_from
    
    @api.model
    def _default_date_to(self):
        today = datetime.now().date()
        day = float(today.strftime('%d'))
        if day > 25:
            date_to = str(today + relativedelta.relativedelta(months=+1, day=25)) or False
        else:
            date_to = str(today + relativedelta.relativedelta(day=25)) or False
        return date_to
            
    date_from = fields.Date(string='Date From', readonly=True, states={'draft': [('readonly', False)]}, required=True, 
        default=_default_date_from)
    date_to = fields.Date(string='Date To', readonly=True, states={'draft': [('readonly', False)]}, required=True, 
        default=_default_date_to)
    