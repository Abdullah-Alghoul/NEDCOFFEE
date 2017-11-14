# -*- coding: utf-8 -*-
from datetime import datetime, date as date_object
from dateutil.relativedelta import relativedelta

import time
from openerp import models, fields, api, _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

class report_account_cash_operation(models.TransientModel):
    _name = "report.account.cash.operation"    
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    @api.model
    def _get_current_month(self):
        return time.strftime('%m')
    
    times = fields.Selection([
        ('dates','Date'),
        ('month', 'Month'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='month')
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscalyear', default=_get_fiscalyear)
    date_start = fields.Date(string='From Date', default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date(string='To Date', default=time.strftime('%Y-%m-%d'))
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
    
    operation_type = fields.Selection([
        ('loan','Loan'),
        ('invest','Investment'),], string='Cash Operation Type', required=True, default='loan')
    
    date_type = fields.Selection([
        ('start_date','Start Date'),
        ('due_date', 'Maturity Date'),
        ('balance', 'Balance at date')], string='Date Type', required=True, default='start_date')
    
    state = fields.Selection([
#         ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),],          
        string='State', required=False, readonly=False, default='')
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    
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
    def print_cash_operation(self): 
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'report.account.cash.operation'
        
        start_date, end_date = self.get_period(self)
        self.date_start = start_date
        self.date_end = end_date
        data['form'] = self.read([])[0]   
        report_name = 'report_loan'
        return {'type': 'ir.actions.report.xml', 'report_name': report_name , 'datas': data}
    
    @api.multi
    def print_cash_operation_balance(self): 
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'report.account.cash.operation'
        
        self.date_start = time.strftime('%Y-%m-%d')
        self.date_end = False
        
        data['form'] = self.read([])[0]   
        report_name = 'report_loan_balance'
        return {'type': 'ir.actions.report.xml', 'report_name': report_name , 'datas': data}