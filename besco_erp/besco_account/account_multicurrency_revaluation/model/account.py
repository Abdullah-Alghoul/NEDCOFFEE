# -*- coding: utf-8 -*-
from openerp import models, fields, api


class AccountAccountLine(models.Model):
    _inherit = 'account.move.line'
    
    # By convention added columns stats with gl_.
    gl_foreign_balance = fields.Float(string='Aggregated Amount curency')
    gl_balance = fields.Float(string='Aggregated Amount')
    gl_revaluated_balance = fields.Float(string='Revaluated Amount')
    gl_currency_rate = fields.Float(string='Currency rate')


class AccountAccount(models.Model):
    _inherit = 'account.account'

    groupby_account = fields.Boolean(
        string="Group by Account (Revaluation)",
        default=False,
    )
    
    #THANH: Due to VAS, we need this field to get Balance site
    revaluation_balance = fields.Selection([
        ('balance', 'Balance'),
        ('dr_balance', 'Debit Balance'),
        ('cr_balance', 'Credit Balance')], string='Balance Site (Revaluation)', default='balance')
    
    
    _sql_mapping = {
        'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
        'debit': "COALESCE(SUM(l.debit), 0) as debit",
        'credit': "COALESCE(SUM(l.credit), 0) as credit",
        'foreign_balance': "COALESCE(SUM(l.amount_currency), 0) as foreign_balance",
    }

    @api.multi
    def _revaluation_query(self, revaluation_type, revaluation_date, company_id):
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        where_clause = where_clause or ' 1=1 '
        having = ''
#         if revaluation_type == 'realized':
#             having = ' HAVING SUM(l.amount_currency) = 0'
        query = ("SELECT l.account_id as id, l.partner_id, l.currency_id, acc.groupby_account, acc.revaluation_balance, " +
                 ', '.join(self._sql_mapping.values()) +
                 " FROM account_move_line l join account_account acc on l.account_id=acc.id" + #THANH: add join with account to get field groupby_account
                 " join account_move am on l.move_id=am.id" + 
                 " WHERE am.state='posted' AND l.account_id IN %s AND am.company_id= %s AND " + 
                 '''
                    l.date between coalesce((select am.date
                                            from account_move_line aml2
                                                LEFT JOIN account_move am on am.id = aml2.move_id
                                                    JOIN account_journal ajn on am.journal_id = ajn.id and ajn.type = 'situation'
                                                    and am.company_id= %s
                                                    and am.state = 'posted'
                                            where am.date <= %s
                                            order by am.date desc
                                            limit 1),'2000-01-01')
                    AND %s AND 
                 '''  + #THANH: get move line between the nearest begin balance date and revaluation_date
                 " l.currency_id IS NOT NULL AND " + 
                 
                 #" l.reconciled = false AND " + #THANH: due to we get data from opening balance to the revaluation date
                 
                 where_clause +
                 " GROUP BY l.account_id, l.currency_id, l.partner_id, acc.groupby_account, acc.revaluation_balance " +
                 having)
        params = [tuple(self.ids), company_id, company_id, revaluation_date, revaluation_date] + where_params
        return query, params

    @api.multi
    def compute_revaluations(self, revaluation_type, revaluation_date, company_id):
        accounts = {}
        # compute for each account the balance/debit/credit from the move lines
        query, params = self._revaluation_query(revaluation_type, revaluation_date, company_id)
        self.env.cr.execute(query, params)
        lines = self.env.cr.dictfetchall()
        for line in lines:
            # generate a tree
            # - account_id
            # -- currency_id
            # --- partner_id
            # ----- balances
            
            if line['groupby_account']:
                #THANH: only group by account
                account_id, currency_id = line['id'], line['currency_id']
                partner_id = False
                if not accounts.has_key(account_id):
                    accounts.setdefault(account_id, {})
                if accounts.has_key(account_id) and not accounts[account_id].has_key(currency_id):
                    accounts[account_id].setdefault(currency_id, {})
                    init_line = line.copy()
                    accounts[account_id][currency_id].update({partner_id: init_line})
                    accounts[account_id][currency_id][partner_id].update({'partner_id': False, 'balance': 0.0, 'debit': 0.0, 'credit': 0.0, 'foreign_balance': 0.0})
                    
                if accounts.has_key(account_id) and accounts[account_id].has_key(currency_id):
                    balance = accounts[account_id][currency_id][partner_id]['balance']
                    debit = accounts[account_id][currency_id][partner_id]['debit']
                    credit = accounts[account_id][currency_id][partner_id]['credit']
                    foreign_balance = accounts[account_id][currency_id][partner_id]['foreign_balance']
                    accounts[account_id][currency_id][partner_id].update({'balance': line['balance'] + balance, 
                                                                         'debit': line['debit'] + debit, 
                                                                         'credit': line['credit'] + credit, 
                                                                         'foreign_balance': line['foreign_balance'] + foreign_balance})
            else:
                account_id, currency_id, partner_id = line['id'], line['currency_id'], line['partner_id']
    
                accounts.setdefault(account_id, {})
                accounts[account_id].setdefault(currency_id, {})
                accounts[account_id][currency_id].setdefault(partner_id, {})
                accounts[account_id][currency_id][partner_id] = line

        return accounts
