# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp import api, fields as fields2
from openerp.tools import float_is_zero
from openerp.tools.misc import formatLang
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools import float_round, float_is_zero, float_compare
import math

class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    
class ResCurrency(models.Model):
    _inherit = "res.currency"
    
    currency_type = fields.Selection([
        ('basic', 'Basic'),
        ('small', 'Smaller'),
        ('larger', 'Larger')
        ], string='Currency Type', index=True, copy=False, default='basic')
    
    def _get_date_rate(self):
        date = self._context.get('date') or fields2.Datetime.now()
        company_id = self._context.get('company_id') or self.pool['res.users']._get_company(self.env.cr, self.env.uid)
        for currency in self:
            sql = '''
                SELECT coalesce((SELECT rate FROM res_currency_rate 
                                   WHERE currency_id = %s
                                     AND name <= '%s'
                                     AND (company_id is null
                                         OR company_id = %s)
                                    ORDER BY name desc LIMIT 1),
                                 (SELECT rate FROM res_currency_rate 
                                   WHERE currency_id = %s
                                     AND name > '%s'
                                     AND (company_id is null
                                         OR company_id = %s)
                                    ORDER BY name asc LIMIT 1))
                '''%(currency.id, date, company_id, currency.id, date, company_id)
            self.env.cr.execute(sql)
            if self.env.cr.rowcount:
                rate = self.env.cr.fetchone()[0]
                return rate or 1
        return 1

    @api.v8
    @api.multi
    def _get_conversion_rate(self, from_currency, to_currency):
        #THANH: Change the way input conversion rate of odoo
        #1. Currency = Company Currency must has rate = 1
        #2. Other currencies must have rate comparing to Company Currency
        #EXP: Company Currency is VND => rate = 1
        # USD Currency will be 22.000
        # EUR will be 28.000
        #When converon from currency -> to currency => formula is From Amount * From Curr.rate / To Curr.rate
        date = self._context.get('date') or from_currency._context.get('date') or to_currency._context.get('date')
        
        from_rate = from_currency.with_context({'date':date})._get_date_rate()
        to_rate = to_currency.with_context({'date':date})._get_date_rate()
        
        if to_currency.currency_type == 'basic':
            if from_currency.currency_type == 'larger':
                return from_rate, from_rate
            else:
                return from_rate and 1 / from_rate or 1, from_rate
        
        if from_currency.currency_type == 'basic':
            if to_currency.currency_type == 'small':
                return to_rate, to_rate
            else:
                return to_rate and 1 / to_rate or 1, to_rate
        
        #THANH: Both currency is not basic (This method based on only one Basic Currency, Others can be Smaller or Larger)
        #exchange 5 USD -> ? EUR, ex: 28,000 (EUR compare to VND), 22,000 (USD compare to USD)
        #value EUR = 5 * (22,000 / 28,000) = ???
        #In the other case, exchange 5 EUR -> ? USD
        #value USD = 5 * (28,000 / 22,000)
        #fomular = from_amount * (from_rate / to_rate)
        return to_rate and from_rate / to_rate  or 1, to_rate and from_rate / to_rate  or 1
    
    @api.v8
    @api.multi
    def compute(self, from_amount, to_currency, round=True):
        """ Convert `from_amount` from currency `self` to `to_currency`. """
        assert self, "compute from unknown currency"
        assert to_currency, "compute to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            #THANH: get rate firstly
            ex_rate, rate = self._get_conversion_rate(self, to_currency)
            to_amount = from_amount * ( ex_rate or 1)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount
    
    
    @api.v8
    def round(self, amount):
        """ Return `amount` rounded according to currency `self`. """
        
        rounding = 1 / math.pow(10,self.round_decimal_places) 
        return float_round(amount, precision_rounding=rounding)

    @api.v7
    def round(self, cr, uid, currency, amount):
        """Return ``amount`` rounded  according to ``currency``'s
           rounding rules.

           :param Record currency: currency for which we are rounding
           :param float amount: the amount to round
           :return: rounded float
        """
        rounding = 1 / math.pow(10,currency.round_decimal_places) 
        return float_round(amount, precision_rounding=rounding)
    