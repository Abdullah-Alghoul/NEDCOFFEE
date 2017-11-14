# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError


class quick_create_entry(models.TransientModel):
    _name = "quick.create.entry"
    
    @api.model
    def _default_currency(self):
        return self.env.user.company_id.currency_id
    
    partner_id = fields.Many2one('res.partner', string='Partner')
    amount_currency = fields.Monetary(default=0.0, string='Transaction Amount', currency_field='currency_id',
                                      help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Transaction Currency', help="The optional other currency if it is a multi-currency entry.")
    rate_type = fields.Selection([
            ('transaction_rate', 'Transaction Rate'),
            ('average_rate', 'Average Rate')], 
            string='Rate Type', default='average_rate', required=True)
    
    label = fields.Char('Label', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    dr_account_id = fields.Many2one('account.account', string='Debit Account', required=True, domain=[('deprecated', '=', False),('type','!=','view')])
    cr_account_id = fields.Many2one('account.account', string='Credit Account', required=True, domain=[('deprecated', '=', False),('type','!=','view')])
    amount = fields.Monetary(default=0.0, string='Dr/Cr Amount', required=True, currency_field='company_currency_id')
    
    currency_rate = fields.Float(string='Transaction Rate')
    
    company_currency_id = fields.Many2one('res.currency', default=_default_currency)
    
    @api.onchange('dr_account_id','cr_account_id')
    def _onchange_invoice_line_ids(self):
        currency_id = self.dr_account_id and self.dr_account_id.currency_id and self.dr_account_id.currency_id.id or False
        if not currency_id:
            currency_id = self.cr_account_id and self.cr_account_id.currency_id and self.cr_account_id.currency_id.id or False
        self.currency_id = currency_id
    
    @api.onchange('currency_rate','amount')
    def _onchange_amount(self):
        if self.currency_rate:
            self.amount_currency = self.amount * self.currency_rate
        
    @api.multi
    def update(self):
        context = dict(self._context or {})
        move_line_obj = self.env['account.move.line']
        ctx = {'check_move_validity': False}
        move_ids = context.get('active_ids',False)
        if move_ids:
            move = self.env['account.move'].browse(move_ids[0])
            debit = {'name': self.label,
                     'partner_id': self.partner_id.id,
                     'currency_id': self.currency_id and self.currency_id.id or False,
                     'amount_currency': self.currency_id and self.amount_currency or 0.0,
                     'date': move.date,
                     'debit': self.amount,
                     'credit': 0.0,
                     'move_id': move.id,
                     'account_id': self.dr_account_id.id,
                     'rate_type': self.rate_type,
                     'currency_ex_rate': self.currency_rate,
                     }
            move_line_obj.with_context(ctx).create(debit)
            
            credit = {'name': self.label,
                     'partner_id': self.partner_id.id,
                     'currency_id': self.currency_id and self.currency_id.id or False,
                     'amount_currency': self.currency_id and -self.amount_currency or 0.0,
                     'date': move.date,
                     'debit': 0.0,
                     'credit': self.amount,
                     'move_id': move.id,
                     'account_id': self.cr_account_id.id,
                     'rate_type': self.rate_type,
                     'currency_ex_rate': self.currency_rate,
                     }
            move_line_obj.with_context(ctx).create(credit)
            
        return {'type': 'ir.actions.act_window_close'}
    