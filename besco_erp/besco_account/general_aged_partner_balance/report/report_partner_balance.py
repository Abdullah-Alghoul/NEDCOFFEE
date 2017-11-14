# -*- coding: utf-8 -*-
import logging
from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse
from openerp import api, fields, models, _

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
        
        self.dau_vao = [0,0,0]
        self.dau_ra = [0,0,0]
        
        self.total = [0,0,0,0,0,0]
        self.total_2nd = [0,0,0,0,0,0]
        
        self.partner_total = [0,0]
        
        self.localcontext.update({
            'get_date':self.get_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            
            'set_dau_vao': self.set_dau_vao,
            'set_dau_ra': self.set_dau_ra,
            
            'get_dau_vao': self.get_dau_vao,
            'get_dau_ra': self.get_dau_ra,
            
            'set_total': self.set_total,
            'get_total': self.get_total,
            
            'get_report_name': self.get_report_name,
            'set_partner_total': self.set_partner_total,
            'get_partner_total': self.get_partner_total,
            'get_partner_trongky': self.get_partner_trongky,
        })
    
    def get_report_name(self, o):
        if o.type == 'receivable':
            return _('PHẢI THU')
        
        if o.type == 'payable':
            return _('PHẢI TRẢ')
        
        if o.type == 'both':
            return _('PHẢI THU, PHẢI TRẢ')
    
    def set_partner_total(self, o, p, description):
        for line in o.ledger_detail_lines:
            if line.partner_id.id == p.id and line.description == description:
                self.partner_total[0] = line.debit
                self.partner_total[1] = line.credit
                
    def get_partner_total(self):
        return self.partner_total
    
    def get_partner_trongky(self, o, p):
        res = []
        for line in o.ledger_detail_lines:
            if line.partner_id.id == p.id and line.gl_date:
                res.append({'gl_date': line.gl_date,
                            'doc_date': line.doc_date,
                            'date_due': line.date_due,
                            'doc_no': line.doc_no,
                            'description': line.description,
                            'cp_acc_code': line.cp_acc_code,
                            'debit': line.debit,
                            'credit': line.credit})
        return res
                
    def set_total(self, o):
        self.total = [0,0,0,0,0,0]
        self.total_2nd = [0,0,0,0,0,0]
        for line in o.balance_lines:
            self.total[0] += line.begin_dr
            self.total[1] += line.begin_cr
            self.total[2] += line.period_dr
            self.total[3] += line.period_cr
            self.total[4] += line.end_dr
            self.total[5] += line.end_cr
            
            self.total_2nd[0] += line.begin_dr_2nd
            self.total_2nd[1] += line.begin_cr_2nd
            self.total_2nd[2] += line.period_dr_2nd
            self.total_2nd[3] += line.period_cr_2nd
            self.total_2nd[4] += line.end_dr_2nd
            self.total_2nd[5] += line.end_cr_2nd
    
    def get_total(self, currency_type = 1):
        if currency_type == 1:
            return self.total
        else:
            return self.total_2nd
    
    def set_dau_vao(self, p):
        self.dau_vao = [0,0,0]
        for inv in p.vendor_invoice_line:
            self.dau_vao[0] += inv.amount_total_signed
            self.dau_vao[1] += (inv.amount_total_signed - inv.residual)
            self.dau_vao[2] += inv.residual
    
    def set_dau_ra(self, p):
        self.dau_ra = [0,0,0]
        for inv in p.customer_invoice_line:
            self.dau_ra[0] += inv.amount_total_signed
            self.dau_ra[1] += (inv.amount_total_signed - inv.residual)
            self.dau_ra[2] += inv.residual
    
    def get_dau_vao(self):
        return self.dau_vao

    def get_dau_ra(self):
        return self.dau_ra
                    
    def get_date(self, date):
        if not date:
            return ''
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
