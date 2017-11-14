#  -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from openerp.addons.base_status.base_state import base_state

class crm_meeting(base_state, osv.Model):
    _inherit = 'crm.meeting'
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'state': fields.selection([('draft', 'Draft'), ('approved', 'Approved'), ('refuse', 'Refuse')], 'Status'),
    }
    
    def _default_employee(self, cr, uid, context=None):
        emp_ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        return emp_ids and emp_ids[0] or False
    
    _defaults = {
        'employee_id': _default_employee,
        'state': 'draft',
    }
    
    def approve(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'approved'})
    
    def refuse(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'refuse'})
    
    def create(self, cr, uid, vals, context=None):
        vals.update({'state':'draft'})
        return super(crm_meeting, self).create(cr, uid, vals, context=context)
    
crm_meeting()
