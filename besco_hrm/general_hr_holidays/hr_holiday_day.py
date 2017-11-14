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

class HrHolidayDay(models.Model):
    _name = "hr.holiday.day"
    _order = "date_from desc"
    
    @api.depends('date_from','date_to')
    def _compute_date(self):
        for days in self:
            date_from = datetime.strptime(days.date_from, DEFAULT_SERVER_DATE_FORMAT).date()
            date_to = datetime.strptime(days.date_to, DEFAULT_SERVER_DATE_FORMAT).date()
            total_days = (date_to - date_from).days
            day_count = 0
            
            holiday_day_ids = []
            self.env.cr.execute('''DELETE FROM hr_holiday_day_line WHERE holiday_day_id is NULL''')
            while day_count <= total_days:
                date = date_from + timedelta(days=+day_count)
                self.env.cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (date))
                result = self.env.cr.dictfetchall()
                dayofweek = result and result[0] and result[0]['dayofweek'] or False
                dayofweek = str(int(dayofweek - 1))
                holiday_day_ids.append((0,0,{'holiday_day_id': days.id,'date': date, 'dayofweek': dayofweek}))
                day_count += 1
            days.holiday_day_ids = holiday_day_ids
    
    name = fields.Char(string='Name', size=250, select=1, required=True)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('hr.holiday.day'))
    date_from = fields.Date(string='Date From', select=1, required=True, default=fields.Datetime.now)
    date_to = fields.Date(string='Date To', select=1, required=True, default=fields.Datetime.now)
    holiday_day_ids = fields.One2many('hr.holiday.day.line', 'holiday_day_id', string='Holiday Day Lines', compute='_compute_date', store=True)
    
    @api.multi
    def unlink(self):
        for days in self:
            self.env.cr.execute('''DELETE FROM hr_holiday_day_line WHERE holiday_day_id = %s'''%(days.id))
        return super(HrHolidayDay, self).unlink()
    
    _sql_constraints = [
        ('date_check', "CHECK (date_from <= date_to)", "The start date must be anterior to the end date."),
    ]
    
    
class HrHolidayDayLine(models.Model):
    _name = "hr.holiday.day.line"
    
    date = fields.Date(string='Date', required=True, default=fields.Datetime.now)
    dayofweek = fields.Selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')],
                                 string='Day of Week', required=True, default='0')
    holiday_day_id = fields.Many2one('hr.holiday.day', string='Holiday Day', copy=False, ondelete='restrict', index=True)
    company_id = fields.Many2one(related='holiday_day_id.company_id', string='Company', readonly=True, copy=False, store=True)