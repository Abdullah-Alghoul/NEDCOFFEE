# -*- coding: utf-8 -*-
import time

from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency):
        context = self.env.context
        if 'revaluation' in context:
            rate = from_currency.rate
            if rate == 0.0:
                date = context.get('date', time.strftime('%Y-%m-%d'))
                raise Warning(
                    _('No rate found '
                      'for the currency: %s '
                      'at the date: %s') %
                    (from_currency.symbol, date)
                )
        return super(ResCurrency, self)._get_conversion_rate(from_currency, to_currency)
