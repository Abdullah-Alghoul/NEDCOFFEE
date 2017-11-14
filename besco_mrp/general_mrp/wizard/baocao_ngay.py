# -*- coding: utf-8 -*-

import time
from osv import fields, osv
from tools.translate import _
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class reports_date(osv.osv):
    _name = 'reports_date'
    _columns = {
              'from_date': fields.date('Từ Ngày', required=True),
              'to_date': fields.date('Đến Ngày', required=True),
              }
    _defaults = { 
        'from_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'to_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }   
reports_date()
