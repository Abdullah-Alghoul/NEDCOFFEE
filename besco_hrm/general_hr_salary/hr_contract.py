# -*- coding: utf-8 -*-
from operator import itemgetter

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from dateutil import relativedelta
import time

class hr_contract(models.Model):
    _inherit = 'hr.contract'
    
    
    
    @api.model
    def _default_structure_id(self):
        structure_ids = self.env['insurance.pit.structure'].search([('state', '=', 'confirm')], limit=1)
        return structure_ids
        
    @api.depends('type_salary','wage', 'structure_id','employee_id.dependant_of_taxpayer')
    def _compute_amount(self, wage_net = None):
        for contract in self:
            taxable_salary = pit = total_deduction = gross_salary = social_insurance = total_company = 0
            total_laborer = 0.000
            structure_line = self.env['insurance.pit.structure.line']
            dependant_of_taxpayer =0.0
            if contract.employee_id:
                self.env.cr.execute('''SELECT ID,dependant_of_taxpayer FROM hr_employee WHERE id = %s; '''% (contract.employee_id.id))
                result = self.env.cr.dictfetchall()
                if result:
                    dependant_of_taxpayer =result[0]['dependant_of_taxpayer']
                total_deduction = contract.structure_id.reduction_yourself + (dependant_of_taxpayer * contract.structure_id.reduction_dependents)
            subtract = (contract.wage - total_deduction) or 0
            if subtract < 0:
                taxable_salary = 0
            else:
                line_ids = structure_line.search([('ni_from','<',subtract),('ni_to','>',subtract),('structure_id','=',contract.structure_id.id)], limit=1   )
                if line_ids:
                    structure_line_obj = structure_line.browse(line_ids.id) 
                    taxable_salary = (subtract - structure_line_obj.pipb_tax) / (1 - structure_line_obj.tax_rate)
                else:
                    line_ids = structure_line.search([('ni_from','<',subtract),('ni_to','=',0),('structure_id','=',contract.structure_id.id)], limit=1)
                    if line_ids:
                        structure_line_obj = structure_line.browse(line_ids.id) 
                        taxable_salary = (subtract - structure_line_obj.pipb_tax) / (1 - structure_line_obj.tax_rate)
            
            for line in contract.structure_id.structure_line_ids:
                if taxable_salary > line.poai_from and taxable_salary <= line.poai_to:
                    pit = taxable_salary * line.tax_rate - line.pipb_tax 
                
                elif taxable_salary > line.poai_from and taxable_salary > line.poai_to:
                    pit = taxable_salary * line.tax_rate - line.pipb_tax
            
            if contract.type_salary == 'net':
                if contract.structure_id:
                    self.env.cr.execute("""SELECT total_laborer FROM insurance_pit_structure WHERE id=%s"""%contract.structure_id.id)
                    total_laborer = self.env.cr.fetchone()
                    total_laborer = 0.115
                if ((contract.wage + pit) / (1 - total_laborer)) > contract.structure_id.max_social_insurance:
                    gross_salary = (contract.wage + pit) + (contract.structure_id.max_social_insurance * total_laborer) 
                else:
                    gross_salary = (contract.wage + pit) / (1 - total_laborer)
            
            elif contract.type_salary == 'gross':
                gross_salary = contract.gross_salary

            if gross_salary < contract.structure_id.max_social_insurance:
                social_insurance = gross_salary
            else:
                social_insurance = contract.structure_id.max_social_insurance
            if contract.id:
                self.env.cr.execute("""UPDATE hr_contract SET gross_salary='%s' WHERE id=%s"""%(gross_salary,contract.id))
            contract.update({'total_deduction': total_deduction, 'taxable_salary': taxable_salary, 'pit': pit,'gross_salary':gross_salary, 'social_insurance': social_insurance})
            
    @api.depends('insurance_ids.of_laborer','insurance_ids.of_company')
    def _compute_total_contribution(self):
        for contract in self:
            total_of_laborer = total_of_company = 0.00
            for line in contract.insurance_ids:
                total_of_laborer += line.of_laborer or 0.00
                total_of_company += line.of_company or 0.00
        contract.update({'total_of_laborer': total_of_laborer, 'total_of_company': total_of_company})
    
    gross_salary = fields.Float('Gross Salary', digits=(16, 0), store=True, track_visibility='always')
    structure_id = fields.Many2one('insurance.pit.structure', 'Insurance & PIT Structures', default=_default_structure_id)
    
    total_deduction = fields.Monetary(string='Total Deduction', compute='_compute_amount', digits=(16, 0), readonly=True, store=True, track_visibility='always')
    taxable_salary = fields.Monetary(string='Taxable Income', compute='_compute_amount', digits=(16, 0), readonly=True, store=True, track_visibility='always')
    pit = fields.Monetary(string='PIT', compute='_compute_amount', digits=(16, 0), readonly=True, store=True, track_visibility='always')
    social_insurance = fields.Monetary(compute='_compute_amount', string='Insurance Salary', digits=(16, 0), readonly=True, store=True, track_visibility='always')
    
    total_of_laborer = fields.Monetary(compute='_compute_total_contribution', string="Total Contribution - Employee's contribution", digits=(16, 2), readonly=True, store=True, track_visibility='always')
    total_of_company = fields.Monetary(compute='_compute_total_contribution', string="Total Contribution - Employer's contribution", digits=(16, 2), readonly=True, store=True, track_visibility='always')
    
    insurance_ids = fields.One2many('hr.contract.insurance', 'contract_id', string="Insurance Lines", readonly=True)
    
    @api.multi
    def button_insurance(self):
        if self.structure_id:
            self.env.cr.execute('''DELETE FROM hr_contract_insurance WHERE contract_id = %s''' % (self.id))
            self.write({'history_checked': True})
            for line in self.structure_id.insurance_ids:
                salary = 0
                if line.insurance_laborer_id.code == "BHTN" or line.insurance_company_id.code == "BHTN":
                    if self.gross_salary > self.structure_id.max_unemployment_insurance:
                        salary = self.structure_id.max_unemployment_insurance
                    else:
                        salary = self.gross_salary 
                    self.env['hr.contract.insurance'].create({'contract_id': self.id, 'insurance_laborer_id': line.insurance_laborer_id.id or False, 
                        'of_laborer': line.of_laborer * salary, 'insurance_company_id': line.insurance_company_id.id or False, 'of_company': line.of_company * salary})
                else:
                    if self.gross_salary > self.social_insurance:
                        salary = self.social_insurance
                    else:
                        salary =  self.gross_salary
                    self.env['hr.contract.insurance'].create({'contract_id': self.id, 'insurance_laborer_id': line.insurance_laborer_id.id or False, 
                        'of_laborer': line.of_laborer * salary, 'insurance_company_id': line.insurance_company_id.id or False, 'of_company': line.of_company * salary})
        return True
    
    def run_update(self, cr, uid, use_new_cursor=False, company_id = False, context=None):
        contract_ids = self.pool.get('hr.contract').search(cr, uid, [('state','=','open')])
        for i in contract_ids:
            contract_obj = self.pool.get('hr.contract').browse(cr, uid, i)
            print i
            contract_obj.write({'history_checked': True})
            contract_obj._compute_amount()
            contract_obj.button_insurance()
    
#     @api.multi
#     def button_offical_contract(self):
#         contract_ids = self.search([('employee_id','=',self.employee_id.id),('state','=','open')])
#         if contract_ids:
#             raise UserError(_("Can not be converted to a Offical Contract new when the old contract being used."))
#         
#         gross_salary = 0
#         if self.type_salary == 'net':
#             pit = self.pit or 0
#             total_laborer = self.structure_id.total_laborer or 0.000
#             max_social_insurance = self.structure_id.max_social_insurance or 0
#             if ((self.wage + pit) / (1 - total_laborer)) > max_social_insurance:
#                 gross_salary = (self.wage + pit) + max_social_insurance * total_laborer 
#             else:
#                 gross_salary = (self.wage + pit) / (1 - total_laborer)
#         
#         self.employee_id.write({'job_id': self.job_id.id})
#         
#         self.write({'history_checked': True})
#         new_id = self.copy({ 'name': 'New', 'trial':False, 'state': 'draft','gross_salary': gross_salary})
#         
#         action = self.env.ref('hr_contract.action_hr_contract')
#         result = action.read()[0]
#         res = self.env.ref('hr_contract.hr_contract_view_form', False)
#         result['views'] = [(res and res.id or False, 'form')]
#         result['res_id'] = new_id.id or False
#         return result
    
    def button_offical_contract(self, cr, uid, ids, context=None):
        result = {}
        imd = self.pool.get('ir.model.data')
        action = imd.xmlid_to_object(cr, uid, 'hr_contract.action_hr_contract')
        form_view_id = imd.xmlid_to_res_id(cr, uid, 'hr_contract.hr_contract_view_form_add_page_history')
        for this in self.browse(cr, uid, ids):
            gross_salary = 0
            if this.type_salary == 'net':
                pit = this.pit or 0
                total_laborer = this.structure_id.total_laborer or 0.000
                max_social_insurance = this.structure_id.max_social_insurance or 0
                if ((this.wage + pit) / (1 - total_laborer)) > max_social_insurance:
                    gross_salary = (this.wage + pit) + max_social_insurance * total_laborer 
                else:
                    gross_salary = (this.wage + pit) / (1 - total_laborer)
            working_hours = False
            if this.working_hours:
                working_hours = this.working_hours.id
            first_date=self.first_date(cr,uid,this.trial_date_end,this.expire_date,working_hours,this.company_id.id)
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'target': action.target,
                'res_model': action.res_model,
                'context' : {
                    'default_employee_id' : this.employee_id.id or form_view_id,
                    'default_company_id' : this.company_id.id or False,
                    'default_job_id' : this.job_id.id or False,
                    'default_department_id' : this.department_id.id or False,
                    'default_working_hours': working_hours or False,
                    'default_date_start' : first_date or '',
                    'default_old_id' : this.id or False,
                    'default_trial' : False,
                    'default_gross_salary': gross_salary,
                    'default_trial_date_start' :this.trial_date_start,
                    'default_trial_date_end': this.trial_date_end or '',
                    }
            }
        return result
    
    
class HrContractInsurance(models.Model):
    _name = "hr.contract.insurance"
    
    insurance_laborer_id = fields.Many2one('hr.salary.rule', string='Taxable & Fee', required=True)
    of_laborer = fields.Float(string="Employee's contribution", required=True, default=1, digits=(16,0))
    insurance_company_id = fields.Many2one('hr.salary.rule', string='Taxable & Fee', required=True)
    of_company = fields.Float(string="Employer's contribution", required=True, default=1, digits=(16,0))
    
    contract_id = fields.Many2one('hr.contract', string="HR Contract", copy=False, ondelete='cascade', index=True)

class HrContractHistory(models.Model):
    _inherit = 'hr.contract.history'
    
    @api.multi
    def button_approve(self):
        for history in self:
            gross_salary = 0
            wage = history.wage or 0 
            
            if history.contract_id.type_salary == 'net' and history.contract_id.structure_id:
                pit = history.contract_id.pit or 0
                total_laborer = history.contract_id.structure_id.total_laborer or 0.000
                max_social_insurance = history.contract_id.structure_id.max_social_insurance or 0
                if ((wage + pit) / (1 - total_laborer)) > max_social_insurance:
                    gross_salary = (wage + pit) + max_social_insurance * total_laborer 
                else:
                    gross_salary = (wage + pit) / (1 - total_laborer)
            else:
                gross_salary = wage
                
            history.contract_id.write({'wage': wage, 'gross_salary': gross_salary,'history_checked': True})
        return self.write({'state':'approve', 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'user_approve': self.env.uid})