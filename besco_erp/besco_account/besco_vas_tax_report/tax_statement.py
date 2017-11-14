# -*- coding: utf-8 -*-

import time
import math

from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

class AccountTaxStatement(models.Model):
    _name = "account.tax.statement"
    _description = "Tax Statements"
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyears = self.pool.get('account.fiscalyear').search(self._cr, self._uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )
        return fiscalyears and fiscalyears[0] or False
    
    times = fields.Selection([
        ('dates','Dates'),
        ('periods', 'Periods'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='periods')
    period_id_start = fields.Many2one('account.period', string='From Period', 
                                      default=lambda self: self.pool.get('account.period').find(self._cr, self._uid, dt=time.strftime('%Y-%m-%d'))[0])
    period_id_end = fields.Many2one('account.period', string='To Period',
                                    default=lambda self: self.pool.get('account.period').find(self._cr, self._uid, dt=time.strftime('%Y-%m-%d'))[0])
    fiscalyear_start = fields.Many2one('account.fiscalyear', string='From Fiscalyear', default=_get_fiscalyear)
    fiscalyear_stop = fields.Many2one('account.fiscalyear', string='To Fiscalyear', default=_get_fiscalyear)
    date_start = fields.Date(string='Date start', default=time.strftime('%Y-%m-01'))
    date_end = fields.Date(string='Date end', default=time.strftime('%Y-%m-%d'))
    quarter = fields.Selection([
        ('1','1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Quarter', default='1')
    company_id  = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.user.company_id.id)
    
    @api.multi
    def print_vat_in(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'aged.partner.balance'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'detailed_account_receivable_report'} 
    
    @api.multi
    def print_vat_out(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'aged.partner.balance'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_balance_partner'} 
    
    @api.multi
    def action_load_data(self):
        aged_partner_line = self.pool.get('aged.partner.line')
        aged_invoice_his_line = self.pool.get('aged.partner.his.invoice')
        date_from ='2015-01-01'
        date_to = '2050-01-01'
        
        for this in self:
            if this.date_from:
                date_from = this.date_from
            if this.date_to:
                date_to = this.date_to
                
            self.cr.execute('''
                    DELETE FROM aged_partner_his_invoice_line
                    WHERE invoice_his_id in (select id from aged_partner_his_invoice where balance_id=%s);
                    
                    DELETE FROM aged_partner_his_invoice WHERE balance_id=%s;
                    
                    COMMIT;
               '''%(this.id, this.id,))
            
            sql ='''
                INSERT INTO partner_balance(balance_id, partner_id,begin_dr,begin_cr,period_dr,period_cr,end_dr,end_cr)
                SELECT %s,rp.id,begin_dr,begin_cr,period_dr,period_cr,end_dr,end_cr 
                FROM fin_gen_liability_data('%s','%s',%s) 
                fin join res_partner rp on fin.partner_name = rp.name
            '''%(this.id,date_from, date_to)
            self.cr.execute(sql)
        return True
    
class AccountTaxStatementVATIn(models.Model):
    _name = "account.tax.statement.vat.in"
    _description = "VAT IN"
    
