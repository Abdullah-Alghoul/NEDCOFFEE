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


class general_hr_timesheet(models.Model):    
    _inherit = "general.hr.timesheet"
    
    @api.depends('work_date')
    def _compute_date(self):
        for timesheets in self:
            work_date = datetime.strptime(timesheets.work_date, '%Y-%m-%d').date()
            day = float(work_date.strftime('%d'))
            if day > 25:
                start_date = str(work_date + relativedelta.relativedelta(day=26)) or False
                end_date = str(work_date + relativedelta.relativedelta(months=+1, day=25)) or False
            else:
                start_date = str(work_date + relativedelta.relativedelta(months=-1, day=26)) or False
                end_date = str(work_date + relativedelta.relativedelta(day=25)) or False
                
            timesheets.update({'start_date': datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) or False,
                               'end_date': datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) or False})