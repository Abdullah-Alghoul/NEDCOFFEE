# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID
from lxml import etree

class hr_team(osv.osv):
    _name="hr.team"
    _columns={
                'name': fields.char('Hr TimeSheet Team', size=64, required=True, translate=True),
                'code': fields.char('Code', size=8, required=True),
                'active': fields.boolean('Active', help="If the active field is set to "\
                                "false, it will allow you to hide the sales team without removing it."),
                'company_id': fields.many2one('res.company', 'Company'),
                'employee_id': fields.many2one('hr.employee', 'Team Leader'),
                'department_id': fields.many2one('hr.department', 'Department'),
                'member_ids': fields.one2many('hr.employee', 'hr_team_id', 'Team Members'),
                'reply_to': fields.char('Reply-To', size=64),
              }
    
    _defaults = {
        'active': 1,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'hr.team', context=context),
    }
    
    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the HR team must be unique !')
    ]
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        res = {}
        if employee_id: 
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            res = {'department_id': employee.department_id.id or False}
        return {'value': res} 
    
hr_team()

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    _columns={
            'hr_team_id': fields.many2one('hr.team', 'Timesheet Team', ondelete='restrict'),
              }
hr_employee()
    
           
