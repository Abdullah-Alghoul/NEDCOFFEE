# -*- coding: utf-8 -*-
##############################################################################
#
#    HLVSolution, Open Source Management Solution
#
##############################################################################
import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.get_company(cr, uid)
        self.localcontext.update({
            'get_date':self.get_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_invoice':self.get_invoice,
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address
        })
        
    def get_company(self,cr,uid):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
        
    def get_company_name(self):
        return self.company_name
    
    def get_company_address(self):
        return self.company_address 
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_invoice(self,this,i):
        if not this.date_from:
            sql='''
                SELECT * From account_invoice
                WHERE partner_id = %s
                and state !='draft'
            '''%(i.partner_id.id)
        else:
            sql='''
                SELECT * From account_invoice
                WHERE partner_id = %s
                and date_invoice between '%s' and '%s'
                and state !='draft'
            '''%(i.partner_id.id,this.date_from,this.date_to)
        self.cr.execute(sql)
        return self.cr.dictfetchall()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
