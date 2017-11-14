# -*- coding: utf-8 -*-
import time
from openerp import api, fields, models, _

class AccountChart(models.TransientModel):
    _name = "account.chart"
    _description = "Account chart"
    
    @api.model
    def _get_fiscalyear(self):
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return fiscalyear
    
    fiscalyear = fields.Many2one('account.fiscalyear', 'Fiscal year',  default=_get_fiscalyear, help='Keep empty for all open fiscal years')
    period_from = fields.Many2one('account.period', 'Start period')
    period_to = fields.Many2one('account.period', 'End period')
    target_move = fields.Selection([('posted', 'All Posted Entries'),('all', 'All Entries')], 'Target Moves', required=True, default='posted')

    @api.onchange('fiscalyear')
    def onchange_fiscalyear(self):
        self.period_from = False
        self.period_to = False
        if self.fiscalyear:
            start_period = end_period = False
            self.env.cr.execute('''
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               ORDER BY p.date_start ASC, p.special DESC
                               LIMIT 1) AS period_start
                UNION ALL
                SELECT * FROM (SELECT p.id
                               FROM account_period p
                               LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                               WHERE f.id = %s
                               AND p.date_start < NOW()
                               ORDER BY p.date_stop DESC
                               LIMIT 1) AS period_stop''', (self.fiscalyear.id, self.fiscalyear.id))
            periods =  [i[0] for i in self.env.cr.fetchall()]
            if periods and len(periods) > 1:
                start_period = periods[0]
                end_period = periods[1]
            self.period_from = start_period
            self.period_to = end_period
    
    @api.multi
    def account_chart_open_window(self):
        """
        Opens chart of Accounts
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of account chart’s IDs
        @return: dictionary of Open account chart window on given fiscalyear and all Entries or posted entries
        """
        period_obj = self.env['account.period']
        fy_obj = self.env['account.fiscalyear']
        context = self.env.context or {}
        if context is None:
            context = {}
        action_rec = self.env['ir.model.data'].xmlid_to_object('general_account.action_account_tree')
        if action_rec:
            action = action_rec.read([])[0]
            fiscalyear_id = self.fiscalyear and self.fiscalyear.id or False
            action['periods'] = []
            if self.period_from and self.period_to:
                action['periods'] = period_obj.build_ctx_periods(self.period_from.id, self.period_to.id)
            action['context'] = str({'fiscalyear': fiscalyear_id, 'periods': action['periods'], 'state': self.target_move})
            if fiscalyear_id:
                action['name'] += ':' + fy_obj.browse(fiscalyear_id).code
            return action

