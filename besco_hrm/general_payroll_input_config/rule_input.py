from openerp import models, fields, api
# from openerp.osv import fields, osv
import time
from openerp import api, tools
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID

class rule_input(models.Model):
    _name="rule.input"
    
    name = fields.Char('Name', default="New")
    date_from = fields.Date("Date", default=lambda *a: time.strftime('%Y-%m-10'))
    date_to = fields.Date("Date To", default= lambda *a: str(datetime.now() + relativedelta(months=+1, day=1, days=-1))[:10])
    job_ids = fields.Many2many('hr.job', 'job_input_ref', 'job_id', 'input_id', string="Jobs")
    company_id = fields.Many2one('res.company', string = "Company")
    
    rule_input_line_ids = fields.One2many('rule.input.line','rule_input_id', string ="Rule Input Lines")
#     hr_salary_rule_id = fields.Many2one('hr.salary.rule', string= "Salary rule")
    hr_salary_rule_code = fields.Char('Salary Rule Code')
    
    quantity = fields.Float('Quantity')
    price = fields.Float('Price', default=4000)
    time = fields.Float('Time')
    unit = fields.Float('Unit')
    
    @api.multi
    def load_time(self):
        clause = ['&','&',('work_date', '<=', self.date_to),('work_date','>=', self.date_from),('state', '=', 'approve')]
        timesheet_ids = self.env['general.hr.timesheet'].search(clause)
        sum = 0
        for timesheet in timesheet_ids:
            for timesheet_line in timesheet.hr_timesheet_line:
                if timesheet_line.employee_id.job_id in self.job_ids:
                    sum += timesheet_line.salary_worked
        self.time = sum
        if sum == 0:
            self.unit = 0
        else:
            self.unit = self.quantity / sum * self.price
        input_line = self.env['rule.input.line']
        hr_rule_input = self.env['hr.rule.input'].search([('code','=','LNS')])
        hr_salary_rule = self.env['hr.salary.rule'].search([('code','=','NS')])
        for i in self.job_ids:
            input_line.create({ 'name': hr_rule_input.id,
                                'job_id': i.id ,
                                'rule_input_id':self.id, 
                                'hr_salary_rule_code': 'NS',
                                'rule_id': hr_salary_rule.id, 
                                'value': self.unit})
            

class rule_input_line(models.Model):
    _name="rule.input.line"
    
    @api.depends('employee_id')
    def _compute_get_contract(self):
        contract_pool = self.env['hr.contract']
        for input_line in self:
            date_from = datetime.strptime(input_line.rule_input_id.date_from, DEFAULT_SERVER_DATE_FORMAT).date()
            date_to = datetime.strptime(input_line.rule_input_id.date_from, DEFAULT_SERVER_DATE_FORMAT).date()
            clause = []
            clause_1 = ['&',('trial_date_end', '<=', date_to),('trial_date_end','>=', date_from)]
            clause_2 = ['&',('trial_date_start', '<=', date_to),('trial_date_start','>=', date_from)]
            
            clause_3 = ['&',('date_end', '<=', date_to),('date_end','>=', date_from)]
            clause_4 = ['&',('date_start', '<=', date_to),('date_start','>=', date_from)]
            clause_5 = ['&',('date_start','<=', date_from),'|',('date_end', '=', False),('date_end','>=', date_to)]
            clause_final =  [('employee_id', '=', input_line.employee_id.id),'|','|','|','|'] + clause_1 + clause_2 + clause_3 + clause_4 + clause_5
            input_line.contract_id = contract_pool.search(clause_final,limit=1).id

    
    name = fields.Many2one('hr.rule.input', string= "Input")
    value = fields.Float(string='Value')
    detail = fields.Text('Detail')
    job_id = fields.Many2one('hr.job', 'Job')
    rule_input_id = fields.Many2one('rule.input',string = "Rule Input")
    contract_id = fields.Many2one('hr.contract',compute='_compute_get_contract',string="Contract", store=True)
    employee_id = fields.Many2one('hr.employee', string = "Employee")    
    rule_id = fields.Many2one(string="Salary rule", related='name.input_id' ,readonly=True, store=True, ondelete='cascade')
#     hr_salary_rule_id = fields.Many2one('hr.salary.rule', related='rule_input_id.hr_salary_rule_id', string= "Salary rule", readonly=True, store=True, ondelete='cascade')
    hr_salary_rule_code = fields.Char('Salary Rule Code', related='rule_input_id.hr_salary_rule_code',  readonly=True, store=True, ondelete='cascade')