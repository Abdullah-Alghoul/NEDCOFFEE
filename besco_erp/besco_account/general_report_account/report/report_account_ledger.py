# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.company_name = False
        self.company_address = False
        self.vat = False
        
        self.localcontext.update({
            'get_vietname_date':self.get_vietname_date,
            
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_company_vat':self.get_company_vat,
            
            'get_summary':self.get_summary,
        })
    
    def get_company(self, company_obj):
        if company_obj:
            self.company_name = company_obj.name or ''
            self.company_address = company_obj.street or ''
            self.vat = company_obj.vat or ''
        return True
         
    def get_company_name(self, report):
        if not self.company_name:
            self.get_company(report.company_id)
        return self.company_name
    
    def get_company_address(self):
        return self.company_address    
    
    def get_company_vat(self):
        return self.vat    
    
    def get_vietname_date(self, date):
        if not date:
            return ''
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_summary(self, general_ledger, description, dr=True, cur=1):
        for line in general_ledger:
            if line.description == description:
                if cur == 1:
                    if dr:
                        return float(line.debit) or 0.0
                    else:
                        return float(line.credit) or 0.0
                else:
                    if dr:
                        return float(line.debit_second) or 0.0
                    else:
                        return float(line.credit_second) or 0.0
        return 0
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
