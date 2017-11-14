# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp import SUPERUSER_ID

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.bank_name =False
        self.partner = False
        self.account_holder = False
        self.acc_number = False
        self.localcontext.update({
            'get_total':self.get_total,
            'get_date':self.get_date,
            'get_ned_crop':self.get_ned_crop
        })
    
    def get_ned_crop(self):
        sql ='''
            SELECT name FROM ned_crop where state ='current' limit 1
        '''
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return i['name'] or ''
        return ''
    
    def get_total(self,o):
        val =[]
        net_station = net_factory = basic_station = basic_factory = loss_weight = loss_quality = total_gain = 0 
        for i in o.loss_line:
            net_station += i.net_station or 0.0
            net_factory += i.Net_factory or 0.0
            basic_station += i.basic_station or 0.0
            basic_factory += i.basic_factory or 0.0
            
            loss_weight += i.loss_station or 0.0
            loss_quality += i.loss_factory or 0.0
            total_gain += i.total_factory or 0.0
            
        val.append({
                    'net_station':net_station,
                    'net_factory':net_factory,
                    'basic_station':basic_station,
                    'basic_factory':basic_factory,
                    'loss_weight':loss_weight,
                    'loss_quality':loss_quality,
                    'total_gain':total_gain
                    })
        return val
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
