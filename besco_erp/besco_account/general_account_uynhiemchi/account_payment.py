# -*- coding: utf-8 -*-
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.exceptions import UserError, ValidationError
from openerp import api, fields, models, _

from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    #THANH: Print Payment as VAS template
    @api.multi
    def print_payment(self):
        if self.payment_type == 'inbound':
            return {
                    'type': 'ir.actions.report.xml',
                    'report_name':'phieuthu',
                    }
        else:
            return {
                    'type': 'ir.actions.report.xml',
                    'report_name':'phieuchi',
                    }