# -*- coding: utf-8 -*-
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

import time
from openerp import models, fields, api, _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

class print_tax_statement(models.TransientModel):
    _name = "print.tax.statement"    
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    @api.model
    def _get_current_month(self):
        return time.strftime('%m')
    
    @api.model
    def _get_ded_vat_account_ids(self):
        res = False
        #THANH: set default accounts from property
        property_obj = self.env['admin.property'].search([('name','=','wizard_report_tax_summary_vas')]) or None
        if property_obj and property_obj.value:
            accounts = property_obj.value.split(',')
            res = self.env['account.account'].search([('code','in',accounts)])
        return res
        
    times = fields.Selection([
        ('dates','Date'),
        ('month', 'Month'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='month')
#     period_id= fields.Many2one('account.period', string='Period', 
#                                       default=lambda self: self.env['account.period'].find(dt=time.strftime('%Y-%m-%d'))[0])
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscalyear', default=_get_fiscalyear)
    date_start = fields.Date(string='Date start', default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date(string='Date end', default=time.strftime('%Y-%m-%d'))
    month = fields.Selection([
        ('01','1'),
        ('02','2'),
        ('03','3'),
        ('04','4'),
        ('05','5'),
        ('06','6'),
        ('07','7'),
        ('08','8'),
        ('09','9'),
        ('10','10'),
        ('11','11'),
        ('12','12')], string='Month', default=_get_current_month)
    quarter = fields.Selection([
        ('1', '1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Quarter', default='1')
    ded_vat_account_ids = fields.Many2many('account.account', string='Deductible VAT Accounts', default=_get_ded_vat_account_ids)
    
    tax_ids = fields.Many2many('account.tax', 'print_tax_statement_tax_rel', 'wizard_id', 'tax_id', string='Taxes')
    show_invoice = fields.Selection([
        ('vat','VAT'),
        ('untaxed','Untaxed Invoices'),
        ('all','All')], string='Show Invoices', 
        required=True, default='vat')
    
    company_id  = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.user.company_id.id)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, default=lambda self: self.env['account.journal'].search([]))
    
    @api.multi
    def get_period(self, report):
        start_date, end_date = False, False
        if report.times == 'dates':
            start_date = report.date_start
            end_date = report.date_end
        else:
            year = report.fiscalyear_id.date_stop.split('-')[0]
            if report.times =='month':
                date = date_object(int(year), int(report.month), 01)
                
                start_date = year + '-%s-01'%(report.month)
                end_date = date + relativedelta(day=1, months=+1, days=-1)
                end_date = end_date.strftime('%Y-%m-%d')
            if report.times == 'years':
                start_date = report.fiscalyear_id.date_start
                end_date   = report.fiscalyear_id.date_stop
            if report.times == 'quarter':
                if report.quarter == '1':
                    start_date = year + '-01-01'
                    end_date = year + '-03-31'
                elif report.quarter == '2':
                    start_date = year + '-04-01'
                    end_date = year + '-06-30'
                elif report.quarter == '3':
                    start_date = year + '-07-01'
                    end_date = year + '-09-30'
                else:
                    start_date = year + '-10-01'
                    end_date = year + '-12-31'
                            
        return start_date, end_date
    
    @api.multi
    def print_report(self): 
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['form'] = self.read([])[0]
        type = self.env.context.get('type', False)
        report_name = 'report_tax_summary'
        if type == 'vat_in':
            report_name = 'report_vat_in'
        if type == 'vat_out':
            report_name = 'report_vat_out'
        start_date, end_date = self.get_period(self)
        journal_ids = [x.id for x in self.journal_ids]
        journal_ids = (','.join(map(str, journal_ids)))
            
        data['form'].update({'start_date': start_date,
                             'end_date': end_date,
                             'journal_ids': journal_ids})
        if report_name:
            return {'type': 'ir.actions.report.xml', 'report_name': report_name, 'datas': data}
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
