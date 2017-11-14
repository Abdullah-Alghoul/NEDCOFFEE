# -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.exceptions import UserError, RedirectWarning

class wizard_hr_contract_expire(models.TransientModel):
    _name = 'wizard.hr.contract.expire'
    
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True)
    expire_date = fields.Date('Expire Date', required=True)
    old_start_date = fields.Date('Old Start Date')
    user_approve_id = fields.Many2one('res.users', 'User Approve', readonly=True, default=lambda self: self.env.user)
    
    @api.multi
    def save_expire_date(self):
        hr_contract_obj = self.env['hr.contract'].browse(self.contract_id.id)
        today = datetime.now().strftime("%Y-%m-%d")
        if self.expire_date < self.old_start_date:
            raise UserError('Unavailable Expiration Date!')
        if self.expire_date <= today:
            state = 'close'
            hr_contract_obj.write({'expire_date': self.expire_date, 'user_approve_id': self.user_approve_id.id, 'state': 'close'})
        else:
            hr_contract_obj.write({'expire_date': self.expire_date, 'user_approve_id': self.user_approve_id.id})