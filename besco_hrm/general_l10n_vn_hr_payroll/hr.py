# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import AccessError, UserError
from openerp import api, SUPERUSER_ID

class hr_employee(models.Model):
    _inherit = "hr.employee"
    
    salary_manager_ids = fields.Many2many('hr.employee','salary_manager_employee_ref','salary_manager_id','employee_id','Salary Manager')
    
    @api.multi
    def write(self, vals):
        print vals.get('salary_manager_ids', False)
        if vals.get('salary_manager_ids', False):
            if not self.env['ir.model.access'].check_groups("general_l10n_vn_hr_payroll.group_hr_salary_manager") or not SUPERUSER_ID:
                raise UserError(_("Can not write value(s) of field Salary Manager, please contact with Salary Manager of your Company."))
        return super(hr_employee, self).write(vals)