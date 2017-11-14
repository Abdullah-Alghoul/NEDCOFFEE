# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class InsurancePitStructure(models.Model):
    _name = 'insurance.pit.structure'
    
    @api.depends('insurance_ids.of_laborer')
    def _compute_total_laborer(self):
        for structure in self:
            total_laborer = 0.000
            for line in structure.insurance_ids:
                total_laborer += line.of_laborer or 0.000
            structure.total_laborer = total_laborer
    
    name = fields.Char(string="Reference", required=True, default="New", readonly=True, states={'draft': [('readonly', False)]})
    date_confirm = fields.Datetime(string="Date Confirm", readonly=True, copy=False)
    date_expired = fields.Datetime(string="Date Expired", readonly=True, copy=False)
    max_social_insurance = fields.Float(string='Social Insurance', required=True, default=1.0, readonly=True, states={'draft': [('readonly', False)]}, digits=(16, 0))
    max_unemployment_insurance = fields.Float(string='Unemployment Insurance', required=True, default=1.0, readonly=True, states={'draft': [('readonly', False)]}, digits=(16, 0))
    reduction_yourself = fields.Float(string='Reduction of Yourself', required=True, default=1.0, readonly=True, states={'draft': [('readonly', False)]})
    reduction_dependents = fields.Float(string='Reduction of Dependents', required=True, default=1.0, readonly=True, states={'draft': [('readonly', False)]})
    
    total_laborer = fields.Float(compute='_compute_total_laborer', string='Total Laborer', digits=(16, 3), store=True)
    
    insurance_ids = fields.One2many('insurance.structure', 'structure_id', string="Insurance Deduction Rates", readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    structure_line_ids = fields.One2many('insurance.pit.structure.line', 'structure_id', string="Manual input Result", readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    state = fields.Selection([('draft', 'New'), ('cancel', 'Canceled'), ('confirm', 'Confirmed'), ('expired', 'Time-expired')], string="Status", default='draft', copy=False)
    
    
    @api.multi
    def button_confirm(self):
        self.write({'state': 'confirm', 'date_confirm': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def button_expired(self):
        self.write({'state': 'expired', 'date_expired': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
        
    @api.multi
    def unlink(self):
        for structure in self:
            if structure.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(InsurancePitStructure, self).unlink()
    
    @api.multi
    def compute_structure_line(self):
        structure_line = self.env['insurance.pit.structure.line']
        for line in self.structure_line_ids:
            pipb_tax = pa_from = pa_to = ni_from = ni_to = 0
            pipb_tax_old = tax_rate_new = 0.00 
            poai_from = line.poai_from or 0
            
            line_ids = structure_line.search([('structure_id','=',self.id),('poai_to','=',poai_from)], limit=1)
            if line_ids != []:
                line_obj = structure_line.browse(line_ids.id)
                tax_rate_new = line.tax_rate - line_obj.tax_rate or 0.00
                pipb_tax_old = line_obj.pipb_tax or 0.00
                ni_from_old = line_obj.ni_to or 0
            
            pipb_tax = poai_from * tax_rate_new + pipb_tax_old
            if pipb_tax < 0:
                pipb_tax = 0.00
                
            pa_from = poai_from * line.tax_rate - pipb_tax
            if pa_from < 0:
                pa_from = 0
                
            pa_to = line.poai_to * line.tax_rate - pipb_tax
            if pa_to < 0:
                pa_to = 0
            
            ni_from = ni_from_old or 0
            ni_to = line.poai_to - pa_to
            if ni_to < 0:
                ni_to = 0
            line.write({'pipb_tax': pipb_tax,'pa_from': pa_from,'pa_to': pa_to,'ni_from': ni_from,'ni_to': ni_to})
        return True
    
class InsuranceStructure(models.Model):
    _name = 'insurance.structure'
    
    @api.depends('insurance_laborer_id', 'insurance_company_id')
    def _compute_amount(self):
        for structure in self:
            of_laborer = structure.insurance_laborer_id.amount_percentage / 100 or 0.000
            of_company = structure.insurance_company_id.amount_percentage / 100 or 0.000
            sum_value = of_laborer + of_company or 0.00
            structure.update({'of_laborer': of_laborer, 'of_company': of_company, 'sum_value': sum_value})
    
    insurance_laborer_id = fields.Many2one('hr.salary.rule', string='Insurance Type', required=True)
    of_laborer = fields.Float(compute='_compute_amount', string='Of Laborer', digits=(16, 3), readonly=True, store=True)
    
    insurance_company_id = fields.Many2one('hr.salary.rule', string='Insurance Type', required=True)
    of_company = fields.Float(compute='_compute_amount', string="Of company", digits=(16, 3), readonly=True, store=True)
    
    sum_value = fields.Float(compute='_compute_amount', string='Sum', digits=(16, 3), readonly=True, store=True)
    
    structure_id = fields.Many2one('insurance.pit.structure', string='Salary Deduction', copy=False, ondelete='cascade', index=True)
    state = fields.Selection(selection=[('draft', 'New'), ('cancel', 'Canceled'), ('confirm', 'Confirmed'), ('expired', 'Time-expired')],
          related='structure_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
#     @api.multi
#     @api.onchange('insurance_laborer_id')
#     def onchange_insurance_laborer_id(self):
#         if not self.insurance_laborer_id:
#             self.update({'insurance_company_id': False})
#             domain = {'domain': {'insurance_company_id': False}}
#             return domain
#         if self.insurance_company_id:
#             self.update({'insurance_company_id': False})
#         domain = {'domain': {'insurance_company_id':[('category_id','=',self.insurance_laborer_id.category_id.id),('contribution','=','company')]}}
#         return domain
    
    
class InsurancePitStructureLine(models.Model):
    _name = 'insurance.pit.structure.line'
    
    @api.depends('poai_from', 'poai_to', 'tax_rate')
    def _compute_amount(self):
        for line in self:
            pipb_tax = pa_from = pa_to = ni_from = ni_to = 0
            pipb_tax_old = tax_rate_new = 0.00
            poai_from = line.poai_from or 0
            
            line_ids = self.search([('structure_id','=',line.structure_id.id),('poai_to','=',poai_from)], limit=1)
            if line_ids != []:
                line_obj = self.browse(line_ids.id)
                tax_rate_new = line.tax_rate - line_obj.tax_rate or 0.00
                pipb_tax_old = line_obj.pipb_tax or 0.00
                ni_from_old = line_obj.ni_to or 0
            
            pipb_tax = poai_from * tax_rate_new + pipb_tax_old
            if pipb_tax < 0:
                pipb_tax = 0.00
                
            pa_from = poai_from * line.tax_rate - pipb_tax
            if pa_from < 0:
                pa_from = 0
                
            pa_to = line.poai_to * line.tax_rate - pipb_tax
            if pa_to < 0:
                pa_to = 0
            
            ni_from = ni_from_old or 0
            ni_to = line.poai_to - pa_to
            if ni_to < 0:
                ni_to = 0
            line.update({
                'pipb_tax': pipb_tax,
                'pa_from': pa_from,
                'pa_to': pa_to,
                'ni_from': ni_from,
                'ni_to': ni_to
                })
            
    poai_from = fields.Float('Portion Of Assessable Income/ From', required=True, default=0, digits=(16, 0))
    poai_to = fields.Float('To', required=True, default=0, digits=(16, 0))
    tax_rate = fields.Float('Tax rate', required=True, default=0.0)
    
    pipb_tax = fields.Float(compute='_compute_amount', string='Payable In Previous Bracket', readonly=True, store=True, digits=(16, 0))

    pa_from = fields.Float(compute='_compute_amount', string='Payable Amount/ From', readonly=True, store=True, digits=(16, 0))
    pa_to = fields.Float(compute='_compute_amount', string='To', readonly=True, store=True, digits=(16, 0))
    
    ni_from = fields.Float(compute='_compute_amount', string='Net Income/From', readonly=True, store=True, digits=(16, 0))
    ni_to = fields.Float(compute='_compute_amount', string='To', readonly=True, store=True, digits=(16, 0))
    
    structure_id = fields.Many2one('insurance.pit.structure', string='Salary Deduction', ondelete='cascade', index=True, copy=False)
    state = fields.Selection(selection=[('draft', 'New'), ('cancel', 'Canceled'), ('confirm', 'Confirmed'), ('expired', 'Time-expired')],
          related='structure_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
