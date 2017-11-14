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

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from openerp import api

class hr_attendance(osv.osv):
    _inherit = "hr.attendance"
    
    def _get_user_department(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for attendance in self.browse(cr, uid, ids, context=context):
            res[attendance.id] = attendance.employee_id.department_id and attendance.employee_id.department_id.id or False
        return res
    
#     def _compute_date_user_tz(self, cr, uid, ids, fieldnames, args, context=None):
#         user_pool = self.pool.get('res.users')
#         res = {}
#         for obj in self.browse(cr, uid, ids, context=context):
#             res[obj.id] = {
#                 'date_user_tz': False,
#                 'day_user_tz': False,
#             }
#             
#             date_user_tz = user_pool._convert_user_datetime(cr, obj.employee_id and obj.employee_id.user_id.id or uid, obj.name)
#             res[obj.id]['date_user_tz'] = date_user_tz.strftime('%Y-%m-%d')
#             res[obj.id]['day_user_tz'] = date_user_tz.strftime('%d-%m-%Y')
#         return res

    def _altern_si_so(self, cr, uid, ids, context=None):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        for att in self.browse(cr, uid, ids, context=context):
            # search and browse for first previous and first next records
            prev_att_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '<', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_add_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '>', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            prev_atts = self.browse(cr, uid, prev_att_ids, context=context)
            next_atts = self.browse(cr, uid, next_add_ids, context=context)
            # check for alternance, return False if at least one condition is not satisfied
            if att.action == 'action':
                return True
            if prev_atts and prev_atts[0].action == att.action: # previous exists and is same action
                return False
            if next_atts and next_atts[0].action == att.action: # next exists and is same action
                return False
            if (not prev_atts) and (not next_atts) and att.action != 'sign_in': # first attendance must be sign_in
                return False
        return True
    
    _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    
    _columns = {
        'department_id': fields.function(_get_user_department, type='many2one', relation='hr.department', string='Department',
            store={
                'hr.attendance': (lambda self, cr, uid, ids, c={}: ids, ['employee_id'], 10),
            }, readonly=True),
                
#         'date_user_tz': fields.function(_compute_date_user_tz, type='date', method=True, string='Date User TZ', store={
#                 'hr.attendance': (lambda self, cr, uid, ids, c={}: ids, ['name'], 10),
#             }, multi='tz'),
#         
#         'day_user_tz': fields.function(_compute_date_user_tz, type='char', method=True, string='Day User TZ', store={
#                 'hr.attendance': (lambda self, cr, uid, ids, c={}: ids, ['name'], 10),
#             }, multi='tz'),
                
        'notes': fields.text('Notes'),
        "attendance_once_sign" : fields.boolean("Attendance once Sign"),
        'end_datetime': fields.datetime('end_datetime'),
        'color': fields.selection([('red', 'No Record'), ('yellow', 'Available Late or Not Enough Time'), ('cyanosis', 'Attendance once Sign'), ('white', 'Normal')],'Color', required=False),
        'schedule_id': fields.many2one('resource.calendar', 'Working Schedule'),
    }
    
    @api.onchange('employee_id')
    def onchange_employee(self):
        for line in self:
            if line.employee_id:
                contract_ids=self.env['hr.contract'].search([('employee_id','=',line.employee_id.id)],limit=1)
                line.schedule_id = contract_ids.working_hours.id