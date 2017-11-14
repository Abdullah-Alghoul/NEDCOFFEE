# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api

class ned_general_hr_employee_legal_leaves(models.Model):
    _name = "ned.general.hr.employee.legal.leaves"
    
    name = fields.Char("Description")
    start_date = fields.Date(string = "start date")
    end_date = fields.Date(string = "end date")
    
    employee_line_ids = fields.One2many("legal.leaves.line","legal_leaves_line_id")
     
class legal_leaves_line(models.Model):
    _name = "legal.leaves.line"
      
    legal_leaves_line_id = fields.Many2one("ned.general.hr.employee.legal.leaves", 'Legal Leaves')
      
    employee_id = fields.Many2one("hr.employee",string = "Employee")
    job = fields.Many2one("hr.job" ,string = "Job")
    total_legal_days = fields.Integer(string = "Total Legal days")
    used_days = fields.Integer(string = "Used")
    remain_days = fields.Integer(string = "Remain",compute="_get_remain_days", store=True)
    onleave_days = fields.Integer(string = "On Leave")

    @api.depends('total_legal_days','used_days')
    def _get_remain_days(self):
        self.remain_days = self.total_legal_days - self.used_days
        