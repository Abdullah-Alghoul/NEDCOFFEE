# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

class account_analytic_distribution(models.Model):
    _name = 'account.analytic.distribution'
    
    @api.multi
    def _compute_amount(self):
        for distribution in self:
            amount = 0.0
            for line in distribution.move_lines:
                amount += line.balance
            distribution.amount = abs(amount)
            
    name = fields.Char(string='Name', required=True, default='/', readonly=True)
    distribution_date = fields.Date(string='Date', default=fields.Date.context_today, required=True, readonly=True, states={'draft': [('readonly', False)]})
    distribution_type = fields.Selection([('fixed', 'Fixed Amount'), 
                                          ('percentage', 'Percentage (%)')], string="Distribution Type", default='percentage', required=True,
                                        readonly=True, states={'draft': [('readonly', False)]})
    distribution_lines = fields.One2many('account.analytic.distribution.line', 'distribution_id', string='Distributions', copy=False,
                                        readonly=True, states={'draft': [('readonly', False)]})
    
    state = fields.Selection([('draft', 'Draft'), 
                              ('done', 'Distributed')], string="Status", default='draft', required=True)
    
    move_lines = fields.One2many('account.move.line', 'distribution_id', string='Moves', readonly=True)
    analytic_lines = fields.One2many('account.analytic.line', 'distribution_id', string='Analytic lines', readonly=True)
    
    amount = fields.Monetary(compute='_compute_amount', string='Amount', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(related="company_id.currency_id", string="Currency", readonly=True)
        
    @api.multi
    def dummy(self):
        #THANH: for button save
        return True
    
    @api.multi
    def action_distribute(self):
        context = self._context
        self.state = 'done'
        if context.get('active_model') == 'account.move.line' and context.get('active_ids'):
            move_lines = self.env['account.move.line'].browse(context['active_ids'])
            #THANH: check total amount must be distributes
            check_amount = 0.0
            check_percentage = 0.0
            for line in self.distribution_lines:
                check_percentage += line.percentage
                check_amount += line.fixed_amount
                    
            if self.distribution_type == 'percentage' and check_percentage != 100:
                raise UserError(_("Distribution must be 100%."))
            if self.distribution_type == 'fixed' and check_amount != self.amount:
                check_amount = line.fixed_amount
                
            #THANH: create analytic line
            amount = 0.0
            general_account_id = False
            for line in self.move_lines:
                amount += line.balance
                if not general_account_id:
                    general_account_id = line.account_id.id
            
            analytic_line_obj = self.env['account.analytic.line']
            base_vals = {
                            'name': move_lines[0].name,
                            'date': move_lines[0].date,
                            'unit_amount': 0,
                            'product_id': False,
                            'product_uom_id': False,
                            'general_account_id': general_account_id,
                            'ref': move_lines[0].ref,
                            #'move_id': self.id,
                            'user_id': self._uid,
                            
                            'distribution_id': self.id,
                        }
            for line in self.distribution_lines:
                if self.distribution_type == 'percentage':
                    value = self.currency_id.round(line.percentage * amount / 100) * -1
                else:
                    value = line.fixed_amount * (amount > 0.0 and -1 or 1)
                vals_line = {
                                'account_id': line.analytic_id.id,
                                'amount': value,
                                #self.company_currency_id.with_context(date=self.date or fields.Date.context_today(self)).compute(amount, self.analytic_account_id.currency_id) if self.analytic_account_id.currency_id else amount,
                            }
                vals_line.update(base_vals)
                analytic_line_obj.create(vals_line)
                
            move_lines.write({'distribution_id': self.id})
            
            if self.name == '/':
                self.name = self.env['ir.sequence'].with_context(ir_sequence_date=self.distribution_date).next_by_code('account.analytic.distribution')
        return True
    
    @api.multi
    def action_remove_distribution(self):
        context = self._context
        self.state = 'draft'
        self.analytic_lines.unlink()
#         if context.get('active_model') == 'account.move.line' and context.get('active_ids'):
#             move_lines = self.env['account.move.line'].browse(context['active_ids'])
#             for line in move_lines:
#                 line.distribution_id.unlink()
        return True
    
class account_analytic_distribution_line(models.Model):
    _name = 'account.analytic.distribution.line'
    
    distribution_id = fields.Many2one('account.analytic.distribution', string='Distribution', ondelete='cascade', index=True)
    analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account', required=True)
    fixed_amount = fields.Float('Fixed Amount')
    percentage = fields.Float('Percentage (%)')
    
    
class account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    distribution_id = fields.Many2one('account.analytic.distribution', string='Distribution', ondelete='cascade', index=True)

    @api.multi
    def action_distribution(self):
        distribution_id = False
        account_type = []
        account_ids = []
        for line in self:
            if len(account_type) > 1:
                raise UserError(_("Only one type Income or Expenses will be distributed at the same time."))
            if len(account_ids) > 1:
                raise UserError(_("Only one Financial Account will be distributed at the same time."))
        
            if line.account_id.user_type_id.type not in ['income', 'expenses']:
                raise UserError(_("Distribution got problem!\nAccount %s is not Income or Expenses.")%(line.account_id.code))
            if line.distribution_id:
                distribution_id = line.distribution_id.id
            if line.account_id.user_type_id.type not in account_type:
                account_type.append(line.account_id.user_type_id.type)
            if line.account_id.id not in account_ids:
                account_ids.append(line.account_id.id)
        
        
        result = self.env.ref('general_account_analytic.action_view_account_analytic_distribution_form').read()[0]
        if distribution_id:
            result['res_id'] = distribution_id
        return result
    
class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    
    distribution_id = fields.Many2one('account.analytic.distribution', string='Distribution', ondelete='cascade', index=True)
    
    
    
    
    