# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.workcenter_id = False
        self.workcenter_name = False
        self.state_id = False
        self.state_name = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_format_datetime': self.get_format_datetime,
            'get_state_id': self.get_state_id,
            'get_state': self.get_state,
            'get_workcenter_id': self.get_workcenter_id,
            'get_workcenter': self.get_workcenter,
            'get_operation': self.get_operation
        })
        
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_format_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y %H:%M:%S')
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.state_id = wizard_data['state_id'] and wizard_data['state_id'][0] or False
        self.workcenter_id = wizard_data['workcenter_id'] and wizard_data['workcenter_id'][0] or False
        self.state_name = wizard_data['state_id'] and wizard_data['state_id'][1] or False
        self.workcenter_name = wizard_data['workcenter_id'] and wizard_data['workcenter_id'][1] or False
        return True
    
    def get_state_id(self):
        if not self.state_id:
            self.get_header()
        return self.state_id
    
    def get_workcenter_id(self):
        if not self.workcenter_id:
            self.get_header()
        return self.workcenter_id
    
    def get_state(self):
        if not self.state_name:
            self.get_header()
        return self.state_name
    
    def get_workcenter(self):
        if not self.workcenter_name:
            self.get_header()
        return self.workcenter_name
    
    def get_operation(self):
        res = []
        if not self.state_id:
            return self.get_header()
        if not self.workcenter_id:
            return self.get_header()
        sql = '''
            SELECT mp.name as production, mpwl.name as operation, pp.name_template, pu.name as uom, 
                (mpwl.date_planned :: TIMESTAMP) + interval '7 hours' as date_planned,
                (mpwl.date_planned_end :: TIMESTAMP) + interval '7 hours' as date_planned_end, 
                mpwl.product_qty
            FROM mrp_production mp join mrp_production_workcenter_line mpwl on mp.id = mpwl.production_id
                join product_product pp on pp.id = mpwl.product_id
                join product_uom pu on pu.id = mpwl.product_uom
            WHERE mpwl.state in ('draft', 'pause')
                AND mpwl.congdoan_id = %s AND mpwl.workcenter_id = %s
        ''' % (self.state_id, self.workcenter_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            res.append({'production': line['production'] or '',
                        'operation': line['operation'] or '',
                        'name_template': line['name_template'] or '',
                        'product_qty': line['product_qty'] or 0.0,
                        'uom': line['uom'] or '',
                        'date_planned': line['date_planned'] or '',
                        'date_planned_end': line['date_planned_end'] or ''})
                        
        return res
