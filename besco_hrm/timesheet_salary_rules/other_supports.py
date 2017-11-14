# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID

class expro_hr_timesheet_salary_other_supports(osv.osv):
    _name = 'hr.timesheet.salary.other.supports'   
    _columns = {
        'job_id': fields.many2one('hr.job', 'Job', required=True),
        'start_date': fields.date('Date From'),
        'end_date': fields.date('Date To'),
        'update_time': fields.datetime('Update Time'),
        'line_ids': fields.one2many('hr.timesheet.salary.other.supports.lines', 'other_id', string='Areas'),
    }
    
    def write(self, cr, uid, ids, values , context=None):
        if context is None:
            context = {}
        values['update_time'] = fields.datetime.now()
        return  super(expro_hr_timesheet_salary_other_supports, self).write(cr, uid, ids, values, context=context)
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.job_id.name
            res.append((record.id, name))
        return res

class expro_hr_timesheet_salary_other_supports_lines(osv.osv):
    _name = 'hr.timesheet.salary.other.supports.lines' 
    _columns = {
        'name': fields.many2one('hr.salary.rule', 'Name', required=True),
        'area_id': fields.many2one('res.area.define', 'Area'),
        'operator': fields.selection([
                                ('=', '='),
                                ('!=', '!='),
                                ('>', '>'),
                                ('>=', '>='),
                                ('<', '<'),
                                ('<=', '<='),
                                ('between', 'between')                                                      
                                ], string='Operator'),
        'value_from': fields.integer('Value From'),
        'value_to': fields.integer('Value To'),
        'support_type': fields.selection([
                                ('quantity', 'Quantity'),
                                ('fix_amount', 'Fixed Amount')], string="Support Type", required=True),
        'value': fields.float('Value', required=True),
        'uom': fields.many2one('product.uom', 'UoM'),
        'other_id': fields.many2one('hr.timesheet.salary.other.supports', 'Other Supports'),
        'active': fields.boolean('Active'),
    }
    
    _defaults = {
        'support_type': 'fix_amount',
    }
