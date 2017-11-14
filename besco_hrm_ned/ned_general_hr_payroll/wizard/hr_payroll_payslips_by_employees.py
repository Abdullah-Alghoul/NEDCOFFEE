# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil import relativedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError
from openerp import api
from lxml import etree
from openerp import SUPERUSER_ID


class hr_payslip_employees(osv.osv_memory):

    _inherit ='hr.payslip.employees'
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        ids = []
        res = super(hr_payslip_employees, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ['form']:
            doc = etree.XML(res['arch'])
             
            for node in doc.xpath("//field[@name='employee_ids']"):
                
                if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id, "ned_general_hr_security.group_hr_manager_76z"):
                    employee_ids = self.pool.get('hr.employee').search(self.env.cr, SUPERUSER_ID, [('insurance_code_id.name','=','TZ0076Z')])
                    node.set('domain', "[('id','in',"+str(employee_ids)+")]")
                
            xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
