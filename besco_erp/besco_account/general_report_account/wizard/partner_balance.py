# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import time
from openerp import models, fields, api, _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

class partner_balance_report(models.TransientModel):
    _name = "partner.balance.report"    
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyears = self.pool.get('account.fiscalyear').search(self._cr, self._uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )
        return fiscalyears and fiscalyears[0] or False
    
    partner_id = fields.Many2one('res.partner', string='Partner', required=False)
    times = fields.Selection([
        ('dates','Date'),
        ('periods', 'Periods'),
        ('quarter','Quarter'),
        ('years','Years')], string='Periods Type', required=True, default='dates')
    period_id_start = fields.Many2one('account.period', string='Period', 
                                      default=lambda self: self.pool.get('account.period').find(self._cr, self._uid, dt=time.strftime('%Y-%m-%d'))[0])
    period_id_end = fields.Many2one('account.period', string='End Period',
                                    default=lambda self: self.pool.get('account.period').find(self._cr, self._uid, dt=time.strftime('%Y-%m-%d'))[0])
    fiscalyear_start = fields.Many2one('account.fiscalyear', string='From Fiscalyear', default=_get_fiscalyear)
    fiscalyear_stop = fields.Many2one('account.fiscalyear', string='To Fiscalyear', default=_get_fiscalyear)
    date_start = fields.Date(string='Date start', default=time.strftime('%Y-%m-%d'))
    date_end = fields.Date(string='Date end', default=time.strftime('%Y-%m-%d'))
    quarter = fields.Selection([
        ('1', '1'),
        ('2','2'),
        ('3','3'),
        ('4','4')], string='Quarter', default='1')
    showdetails = fields.Boolean(string='Get Detail', default=True)
    company_id  = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.user.company_id.id)
    is_customer = fields.Selection([
        ('customer', 'Customer'),
        ('supplier','Suplier'),
        ('all','ALL')], string='Type', default='customer',required=True)
    
    @api.multi
    def finance_report(self): 
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'partner.balance.report'
        data['form'] = self.read([])[0]
            
        return {'type': 'ir.actions.report.xml', 'report_name': 'partner_balance_report' , 'datas': data}
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
