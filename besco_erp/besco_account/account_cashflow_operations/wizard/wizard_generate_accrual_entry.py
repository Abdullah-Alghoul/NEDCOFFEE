# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError

import  time
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
DATE_FORMAT = "%Y-%m-%d"

class wizard_generate_accrual_entry(models.TransientModel):
    _name = "wizard.generate.accrual.entry"
    
    @api.model
    def _get_period(self):
        now = time.strftime('%Y-%m-%d')
        period = self.env['account.period'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
        return period
    
    entry_type = fields.Selection([
        ('accrual','Generate Accrual Entry'),
        ('revert_accrual', 'Revert Accrual Entry')], string='Entry Type', required=True, default='accrual')
    
    period_id = fields.Many2one('account.period', string='Period', required=True, 
                                domain=[('state','=','draft')], default=_get_period)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id)
    
    @api.multi
    def generate_entry(self):
        self.ensure_one()
        operation_line_obj = self.env['account.cash.operation.line']
        if self.entry_type == 'accrual':
            operation_lines = operation_line_obj.search([
                ('state', '=', 'confirm'), ('date', '>=', self.period_id.date_start), ('date', '<', self.period_id.date_stop), 
                ('accrual_move_id', '=', False)])
            entry_date = self.period_id.date_stop
        else:
            operation_lines = operation_line_obj.search([
                ('state', '=', 'confirm'), ('date', '>=', self.period_id.date_start), ('date', '<', self.period_id.date_stop), 
                ('accrual_move_id', '!=', False), ('reversed_accrual_move_id', '=', False)])
            date_stop =  datetime.strptime(self.period_id.date_stop, DATE_FORMAT) + relativedelta(days=+1)
            entry_date = date_stop.strftime(DATE_FORMAT)
            
        created_move_ids = []
        for line in operation_lines:
            if line.date == self.entry_type:
                #THANH: trung ngay cuoi ky (ngay thanh toan = ngay 31) thi khong sinh but toan uoc tinh lai
                continue
            if self.entry_type == 'accrual' and line.accrual_move_id:
                continue
            if self.entry_type == 'revert_accrual' and line.reversed_accrual_move_id:
                continue
            if self.entry_type == 'accrual':
                max_line = operation_line_obj.search([('cash_id','=',line.cash_id.id), ('date','>=',line.date)], order='date desc', limit=1)
                if max_line and max_line.id == line.id:
                    #THANH: Lan thanh toan cuoi cung cua Operation thi ko sinh accrual
                    continue
                bigger_line = operation_line_obj.search([('cash_id','=',line.cash_id.id), 
                                                      ('id','!=',line.id),
                                                      ('date','>',line.date),
                                                      ('date','<',self.period_id.date_stop)], order='date desc')
                if bigger_line:
                    continue
                
            move = self.create_move(line, entry_date, self.entry_type)
            if self.entry_type == 'accrual':
                line.write({'accrual_move_id': move.id})
            else:
                line.write({'reversed_accrual_move_id': move.id})
            created_move_ids.append(move)
        
        move_line_ids = []
        for move in created_move_ids:
            for line in move.line_ids:
                move_line_ids.append(line.id)
        
        if self.entry_type == 'accrual':
            title = _('Accrual Entries')
        else:
            title = _('Reversed Accrual Entries')
        return {
            'name': title,
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_line_ids)],
        }
    
    @api.multi
    def compute_days(self, start, end):
        #THANH: count number of days between start and end and except saturday 5, sunday 6
        days = 0
        start = datetime.strptime(start, DATE_FORMAT)
        end = datetime.strptime(end, DATE_FORMAT)
        delta = relativedelta(days=+1)
        d = start
        weekend = set([5, 6])
        while d <= end:
            if d.weekday() not in weekend:
                days += 1
            d += delta
        return days
    
    @api.multi
    def create_move(self, operation_line, entry_date, entry_type):
        move_obj = self.env['account.move']
        if entry_type == 'accrual':
            if not operation_line.cash_id.journal_id.accrual_account_id:
                raise UserError(_("You must define Accrual Account on Journal (%s).") % (_(operation_line.cash_id.journal_id.name)))
            
            journal_id = operation_line.cash_id.journal_id.id
            company_currency = operation_line.cash_id.company_id.currency_id
            current_currency = operation_line.cash_id.currency_id
            
#             days = self.compute_days(operation_line.date, self.period_id.date_stop)
            days = (datetime.strptime(self.period_id.date_stop, DATE_FORMAT) - datetime.strptime(operation_line.date, DATE_FORMAT)).days + 1
            interest_amount = operation_line.rate_per_day * days
            amount = current_currency.compute(interest_amount, company_currency)

            reference = operation_line.cash_id.name
            partner_id = operation_line.cash_id.partner_id.id
            debit_account = operation_line.cash_id.account_recognition_id.id
            if operation_line.cash_id.type != 'loan':
                debit_account = operation_line.cash_id.journal_id.accrual_account_id.id
            
            credit_account = operation_line.cash_id.journal_id.accrual_account_id.id
            if operation_line.cash_id.type != 'loan':
                credit_account = operation_line.cash_id.account_recognition_id.id
            
            name = _('Ước tính lãi kỳ %s, %s ngày')%(self.period_id.name, days)
            move_line_1 = {
                'name': name,
                'account_id': credit_account,
                'debit': 0.0,
                'credit': amount,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - interest_amount or 0.0,
#                 'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'sale' else False,
                'date': entry_date,
            }
            move_line_2 = {
                'name': name,
                'account_id': debit_account,
                'credit': 0.0,
                'debit': amount,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and interest_amount or 0.0,
#                 'analytic_account_id': line.asset_id.category_id.account_analytic_id.id if categ_type == 'purchase' else False,
                'date': entry_date,
            }
            move_vals = {
                'ref': reference,
                'date': entry_date or False,
                'journal_id': journal_id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                }
            move = move_obj.create(move_vals)
        else:
            if operation_line.accrual_move_id:
                name = _('Revert ước tính lãi kỳ %s')%(self.period_id.name)
                move_ids = operation_line.accrual_move_id.reverse_moves(entry_date, operation_line.cash_id.journal_id or False)
                move = move_obj.browse(move_ids[0])
                for line in move.line_ids:
                    line.write({'name': name})
            else:
                raise UserError(_("Interest Payment '%s' of Operation number '%s' still not generate Accrual Entry. Please generate it all firstly.")%(_(operation_line.name), operation_line.cash_id.name))
        move.post()
        return move
    
    @api.multi
    def open_accrual_entries(self):
        operation_lines = self.env['account.cash.operation.line'].search([
            ('state', '=', 'confirm'), ('date', '>=', self.period_id.date_start), ('date', '<=', self.period_id.date_stop), 
            '|', ('accrual_move_id', '!=', False), ('reversed_accrual_move_id', '!=', False)])
        
        move_line_ids = []
        for line in operation_lines:
            if line.accrual_move_id:
                move_line_ids.extend([x.id for x in line.accrual_move_id.line_ids])
            if line.reversed_accrual_move_id:
                move_line_ids.extend([x.id for x in line.reversed_accrual_move_id.line_ids])
                
        return {
            'name': _('Accrual Entries'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_line_ids)],
        }