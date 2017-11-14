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
        self.from_date = False
        self.to_date = False
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_format_datetime': self.get_format_datetime,
            'get_from_date': self.get_from_date,
            'get_to_date': self.get_to_date,
            'get_operation': self.get_operation,
            'get_result': self.get_result,
            'get_workcenter': self.get_workcenter
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
        self.from_date = wizard_data['from_date']
        self.to_date = wizard_data['to_date']
        return True
    
    def get_from_date(self):
        if not self.from_date:
            self.get_header()
        return self.from_date
    
    def get_to_date(self):
        if not self.to_date:
            self.get_header()
        return self.to_date
    
    def get_operation(self):
        res = []
        if not self.from_date:
            return self.get_header()
        if not self.to_date:
            return self.get_header()
        sql = '''
            SELECT DISTINCT mps.name as stage, mps.id as stage_id
            FROM mrp_production_workcenter_line mpwl join mrp_operation_result mor on mor.operation_id = mpwl.id
                join mrp_production_stage mps on mps.id = mpwl.congdoan_id
            WHERE mor.end_date between '%s' and '%s'
                AND mor.state = 'done'
        ''' % (self.from_date, self.to_date)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            res.append({'stage': line['stage'] or '',
                        'stage_id': line['stage_id'] or False})
        return res
    
    def get_workcenter(self, stage_id):
        res = []
        if not self.from_date:
            return self.get_header()
        if not self.to_date:
            return self.get_header()
        if not stage_id:
            return {}
        sql = '''
            SELECT DISTINCT rr.name as resource, mw.id workcenter, mps.id as stage_id
            FROM mrp_production_workcenter_line mpwl join mrp_operation_result mor on mor.operation_id = mpwl.id
                join mrp_production_stage mps on mps.id = mpwl.congdoan_id
                join mrp_workcenter mw on mw.id = mor.resource_id
                join resource_resource rr on rr.id = mw.resource_id
            WHERE mor.end_date between '%s' and '%s'
                AND mor.state = 'done'
                AND mps.id = %s
        ''' % (self.from_date, self.to_date, stage_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            res.append({'resource': line['resource'] or '',
                        'workcenter': line['workcenter'] or False,
                        'stage_id': line['stage_id'] or False})
        return res
    
    def get_result(self, stage_id, workcenter_id):
        res = []
        if not stage_id:
            return {}
        if not workcenter_id:
            return {}
        sql = '''
            SELECT pp.name_template ,mp.name as production, mp.state as stage, mpwl.name as operation,rc.name as calendar, 
                (mor.start_date :: TIMESTAMP) + interval '7 hours' as start_date, 
                (mor.end_date :: TIMESTAMP) + interval '7 hours' as end_date,
                mor.product_qty as result_qty, pu.name as uom,mpwl.product_qty as operation_qty
            FROM mrp_production mp join mrp_production_workcenter_line mpwl on mpwl.production_id = mp.id 
                join mrp_operation_result mor on mor.operation_id = mpwl.id
                join resource_calendar rc on rc.id = mor.calendar_id
                join mrp_production_stage mps on mps.id = mpwl.congdoan_id
                join product_product pp on pp.id = mp.product_id 
                join product_uom pu on pu.id = mor.product_uom
                join mrp_workcenter mw on mw.id = mor.resource_id
                join resource_resource rr on rr.id = mw.resource_id
            WHERE mor.state = 'done' AND mps.id = %s 
                AND mor.end_date between '%s' and '%s'
                AND mw.id = %s
        ''' % (stage_id, self.from_date, self.to_date, workcenter_id)
        self.cr.execute(sql)
        for line in self.cr.dictfetchall():
            res.append({'name_template': line['name_template'] or '',
                        'production': line['production'] or '',
                        'stage': line['stage'] or '',
                        'operation': line['operation'] or '',
                        'calendar': line['calendar'] or '',
                        'start_date': line['start_date'] or '',
                        'end_date': line['end_date'] or '',
                        'result_qty': line['result_qty'] or 0.0,
                        'uom': line['uom'] or '',
                        'operation_qty': line['operation_qty'] or 0.0
                        })
        return res
