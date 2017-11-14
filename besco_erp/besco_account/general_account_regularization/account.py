# -*- encoding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.tools import float_is_zero
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import modules

import time
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class AccountAccount(models.Model):
	_inherit = 'account.account'

	def balance_calculation(self, cr, uid, ids, context, date=time.strftime('%Y-%m-%d'), periods=[]):
		acc_set = ",".join(map(str, ids))
		query = self.pool.get('account.move.line')._query_get(cr, uid,
				context=context)

		if not periods:
			cr.execute(("SELECT a.id, " \
					"COALESCE(SUM(l.debit - l.credit), 0) " \
				"FROM account_account a " \
					"LEFT JOIN account_move_line l " \
					"ON (a.id=l.account_id) " \
				"WHERE a.type != 'view' " \
					"AND a.id IN (%s) " \
					"AND " + query + " " \
					"AND a.active " \
					"AND l.date <= '%s' "
				"GROUP BY a.id") % (acc_set, date))
		else:
			cr.execute(("SELECT a.id, " \
					"COALESCE(SUM(l.debit - l.credit), 0) " \
				"FROM account_account a " \
					"LEFT JOIN account_move_line l " \
					"ON (a.id=l.account_id) " \
				"WHERE a.type != 'view' " \
					"AND a.id IN (%s) " \
					"AND " + query + " " \
					"AND a.active " \
					"AND l.period_id in (%s) " \
				"GROUP BY a.id") % (acc_set, ",".join(map(str, periods))))

		res = {}
		for account_id, sum in cr.fetchall():
			res[account_id] = round(sum,2)
		for id in ids:
			res[id] = round(res.get(id,0.0), 2)
		return res

class AccountRegularizationModel(models.Model):
	_name = 'account.regularization.model'
	_description = 'Account Regularization Model'
	_order = 'sequence'
	
	name = fields.Char(string='Name', size=64, required=True)
	account_ids = fields.Many2many('account.account', 'account_regularization_rel', 'regularization_id', 'account_id', string='Accounts to balance', required=True, domain=[('type','!=','view')])
	debit_account_id = fields.Many2one('account.account', string='Result account, debit', required=True)
	credit_account_id = fields.Many2one('account.account', string='Result account, credit', required=True)
# 	balance_calc = fields.Selection([('date','Date'),('period','Periods')], string='Regularization time calculation', required=True, default='date')
	move_ids = fields.One2many('account.move', 'regularization_id', string='Regularization Moves', readonly=True)
	
	#Thanh: Add somes fields
	company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env['res.company']._company_default_get('account.regularization'))
	sequence = fields.Integer(string='Sequence', required=True)
	journal_id = fields.Many2one('account.journal', string='Entry Journal', required=True)
	active = fields.Boolean(string='Active', default=True)
	

	move_journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
	
	@api.one
	@api.constrains('journal_id', 'move_journal_ids')
	def _check_journal_type(self):
		if len(self.move_journal_ids) and self.journal_id:
			journal_type = []
			for journal in self.move_journal_ids:
				if journal.internal_type not in journal_type:
					journal_type.append(journal.internal_type)
			if len(journal_type) > 1:
				raise UserError(_("Only one journal type Public or Internal define for a Model."))
			if self.journal_id.internal_type not in journal_type:
				raise UserError(_("Entry Journal and Journals must have the same journal type Public or Internal."))
		
		
	@api.multi
	def load_journal(self):
		domain = []
		if self._context.get('journal_type', False):
			domain = [('internal_type','=',self._context['journal_type'])]
		self.move_journal_ids = self.env['account.journal'].search(domain)
		
class AccountRegularization(models.Model):
	_name = 'account.regularization'
	_description = 'Account Regularization'
	_order = 'date_from desc, date_to desc'
		
	@api.multi
	def set_to_draft(self):
		for move in self.move_ids:
			move.with_context(force_cancel=True).button_cancel()
			move.unlink()
		self.state = 'draft'

	@api.multi
	def post(self):
		for this in self:
			partner_id = this.company_id.partner_id.id
			second_currency = this.company_id.second_currency_id or False
			account_obj = self.env['account.account']
			moves = []
			
			#THANH: new way to generate regularization
			regularization_total, regularization_total_2nd = 0.0, 0.0
			regularization_key = {}
			for model in self.model_ids:
				if not model.debit_account_id or not model.credit_account_id:
					raise UserError(_("Debit account and Credit account of model '%s' should not be empty.")%(model.name))
				if not regularization_key.has_key(model.debit_account_id.id):
					regularization_key.update({model.debit_account_id.id: [0.0, 0.0]})
				if not regularization_key.has_key(model.credit_account_id.id):
					regularization_key.update({model.credit_account_id.id: [0.0, 0.0]})
					
				move_lines = []
				total_value, total_2nd_value = 0.0, 0.0
				model_account_ids = [x.id for x in model.account_ids]
				for line in this.balance_lines:
					if line.com_currency_id.round(line.balance) == 0.0:
						continue
					if line.acc_id in model_account_ids:
						account = account_obj.browse(line.acc_id)
						name = _('Kết chuyển %s')%(_(account.name))
						vals = {
				            'name': name,
				            'account_id': line.acc_id,
				            'debit': line.balance < 0 and abs(line.balance) or 0.0,
				            'credit': line.balance > 0 and abs(line.balance) or 0.0 ,
				            'journal_id': model.journal_id.id,
				            'partner_id': partner_id,
				            'analytic_account_id': False,
				            'date': this.date_to,
			        	}
						if second_currency:
							#THANH: update 2nd currency fields
							second_amount = line.balance_second < 0 and abs(line.balance_second) or -line.balance_second
							second_ex_rate = line.balance_second and second_currency.round(abs(line.balance_second) > abs(line.balance) \
																						and abs(line.balance_second / line.balance) \
																						or abs(line.balance / line.balance_second)) \
																or 0.0
							vals.update({
							            'rate_type': 'transaction_rate',
							            'currency_id': second_currency.id,
							            'amount_currency': second_amount,
							            'currency_ex_rate': second_ex_rate,
							            
							            'second_currency_id': second_currency.id,
							            'second_amount': second_amount,
							            'second_ex_rate': second_ex_rate
										})
						move_lines.append((0, 0, vals))
						total_value += line.balance
						total_2nd_value += line.balance_second
				
				if len(move_lines):
					total_vals = {
			            'name': model.name,
			            'account_id': total_value > 0 and model.debit_account_id.id or model.credit_account_id.id, 
			            'debit': total_value > 0 and abs(total_value) or 0.0 ,
			            'credit': total_value < 0 and abs(total_value) or 0.0,
			            'journal_id': model.journal_id.id,
			            'partner_id': partner_id,
			            'currency_id': False,
			            'amount_currency': False,
			            'analytic_account_id': False,
			            'date': this.date_to,
			        }
					if second_currency:
						#THANH: update 2nd currency fields
						second_ex_rate = total_2nd_value and second_currency.round(abs(total_2nd_value) > abs(total_value) \
																					and abs(total_2nd_value / total_value) \
																					or abs(total_value / total_2nd_value)) \
																or 0.0
						total_vals.update({
						            'rate_type': 'transaction_rate',
						            'currency_id': second_currency.id,
						            'amount_currency': total_2nd_value,
						            'currency_ex_rate': second_ex_rate,
						            
						            'second_currency_id': second_currency.id,
						            'second_amount': total_2nd_value,
						            'second_ex_rate': second_ex_rate
									})
					move_lines.append((0, 0, total_vals))
				
					move_vals = {
			            'ref': model.name,
			            'date': this.date_to or False,
			            'journal_id': model.journal_id.id,
			            'line_ids': move_lines,
			            'regularization_id': this.id,
			            }
					move = self.env['account.move'].create(move_vals)
					move.post()
					moves.append(move.id)
				
				if total_value:
					regularization_total += total_value
					regularization_total_2nd += total_2nd_value
					regularization_key[model.debit_account_id.id][0] += total_value > 0 and total_value or 0.0
					regularization_key[model.debit_account_id.id][1] += total_value > 0 and total_2nd_value or 0.0
					regularization_key[model.credit_account_id.id][0] += total_value < 0 and total_value or 0.0
					regularization_key[model.credit_account_id.id][1] += total_value < 0 and total_2nd_value or 0.0	
					
			#THANH: KC 911 -> 421
			if this.re_account_id and regularization_total:
				if not this.description:
					raise UserError(_("Description should not be empty."))
				
				move_lines = []
				
				for key, amount in regularization_key.items():
					total_vals = {
				            'name': this.description,
				            'account_id': key, 
				            'debit': amount[0] < 0 and abs(amount[0]) or 0.0 ,
				            'credit': amount[0] > 0 and abs(amount[0]) or 0.0,
				            'journal_id': this.journal_id.id,
				            'partner_id': partner_id,
				            'date': this.date_to,
			        }
					if second_currency:
							#THANH: update 2nd currency fields
							second_amount = amount[1] < 0 and abs(amount[1]) or -amount[1]
							second_ex_rate = amount[1] and second_currency.round(abs(amount[1]) > abs(amount[0]) \
																				and abs(amount[1] / amount[0]) \
																				or abs(amount[0] / amount[1])) \
														or 0.0
							total_vals.update({
									            'rate_type': 'transaction_rate',
									            'currency_id': second_currency.id,
									            'amount_currency': second_amount,
									            'currency_ex_rate': second_ex_rate,
									            
									            'second_currency_id': second_currency.id,
									            'second_amount': second_amount,
									            'second_ex_rate': second_ex_rate,
												})
					move_lines.append((0, 0, total_vals))
					
				total_vals = {
				            'name': this.description,
				            'account_id': this.re_account_id.id, 
				            'debit': regularization_total > 0 and abs(regularization_total) or 0.0,
				            'credit': regularization_total < 0 and abs(regularization_total) or 0.0,
				            'journal_id': this.journal_id.id,
				            'partner_id': partner_id,
				            'date': this.date_to,
					        }
				if second_currency:
						#THANH: update 2nd currency fields
						second_amount = regularization_total_2nd
						second_ex_rate = regularization_total_2nd and second_currency.round(abs(regularization_total_2nd) > abs(regularization_total) \
																			and abs(regularization_total_2nd / regularization_total) \
																			or abs(regularization_total / regularization_total_2nd)) \
													or 0.0
						total_vals.update({
								            'rate_type': 'transaction_rate',
								            'currency_id': second_currency.id,
								            'amount_currency': second_amount,
								            'currency_ex_rate': second_ex_rate,
								            
								            'second_currency_id': second_currency.id,
								            'second_amount': second_amount,
								            'second_ex_rate': second_ex_rate,
											})
				move_lines.append((0, 0, total_vals))
				
				move_vals = {
		            'ref': this.description,
		            'date': this.date_to or False,
		            'journal_id': this.journal_id.id,
		            'line_ids': move_lines,
		            'regularization_id': this.id,
		            }
				move = self.env['account.move'].create(move_vals)
				move.post()
				moves.append(move.id)
			
			if 	moves:
				this.move_ids = moves
		self.state = 'post'

	@api.multi
	def load_data(self):
		for report in self:
			second_currency_id = report.company_id.second_currency_id and report.company_id.second_currency_id.id or 'null'
			
			sql ='''
			    DELETE from account_regularization_line where regularization_id = %s;
			'''%(report.id)
			self.env.cr.execute(sql)
			for i in report.model_ids:
				account_ids = [x.id for x in i.account_ids]
				journal_ids = [x.id for x in i.move_journal_ids]
				if len(account_ids) and len(journal_ids):
					account_ids = (','.join(map(str, account_ids)))
					journal_ids = (','.join(map(str, journal_ids)))
					sql = _('''
			            INSERT INTO account_regularization_line (create_uid, create_date, write_uid, write_date,
			                acc_id, acc_code, regularization_id, 
			                debit, credit, balance, 
			                debit_second, credit_second, balance_second,
			                com_currency_id, second_currency_id)
			                
		              	SELECT %(uid)s, current_timestamp, %(uid)s, current_timestamp,
				                acc_id, acc_code, %(regularization_id)s,
				                debit, credit, (debit - credit) balance,
				                debit_second, credit_second, (debit_second - credit_second) balance_second,
				                %(com_currency_id)s, %(second_currency_id)s
			                
		                FROM (
			                    select acc.id acc_id, acc.code acc_code,
			                        sum(aml.debit) debit, sum(aml.credit) credit,
			                        sum(case when aml.debit != 0 then abs(aml.second_amount)::numeric 
			                                else 0.0::numeric
			                            end) debit_second,
			                        sum(case when aml.credit != 0 then abs(aml.second_amount)::numeric 
			                                else 0.0::numeric
			                            end) credit_second
			                            
			                    from account_move_line aml 
			                        join account_move amh on amh.id = aml.move_id
			                        join account_journal ajn on amh.journal_id = ajn.id and ajn.type != 'situation'
			                        join account_account acc on aml.account_id = acc.id
			                    where amh.company_id = %(company_id)s 
			                    	and amh.state = 'posted' 
			                    	and amh.journal_id in (%(journal_ids)s)
			                    	and date(aml.date) between '%(start_date)s' and '%(end_date)s'
			                    	and aml.account_id in (%(account_ids)s)
			                    group by acc.id, acc.code
			                    order by acc.code
			                ) bal
					''')
					sql = sql%({
	                  'start_date': report.date_from,
	                  'end_date': report.date_to,
	                  'company_id': report.company_id.id,
	                  'com_currency_id': report.company_id.currency_id.id,
	                  'second_currency_id': second_currency_id,
	                  'regularization_id': report.id,
	                  'uid': self.env.user.id,
	                  'account_ids': account_ids,
	                  'journal_ids': journal_ids,
	                  })
					self.env.cr.execute(sql)
			return True
		
		
	entry_count = fields.Integer(compute='_entry_count', string='# Asset Entries')
	re_account_id = fields.Many2one('account.account', string="Retained Earning Account", required=False, 
								readonly=True, states={'draft': [('readonly', False)]})
	
	date_from = fields.Date(string='From Date', required=True, default=time.strftime('%Y-%m-%d'), 
							readonly=True, states={'draft': [('readonly', False)]}, copy=False)
	date_to = fields.Date(string='To Date', required=True, default=time.strftime('%Y-%m-%d'), 
							readonly=True, states={'draft': [('readonly', False)]}, copy=False)
	
	state = fields.Selection([
            ('draft','Draft'),
            ('post', 'Posted'),
            ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, default='draft')
	
	company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id.id, readonly=True, states={'draft': [('readonly', False)]})
	second_currency_id = fields.Many2one(related='company_id.second_currency_id', string="2nd Company Currency", readonly=True)
		
	balance_lines = fields.One2many('account.regularization.line','regularization_id',string = "Balance Lines", copy=False)
	balance_lines_2rd = fields.One2many('account.regularization.line','regularization_id',string = "2nd Balance Lines", copy=False)
	
	model_ids = fields.Many2many('account.regularization.model', string='Regularization Models', required=True, 
# 								domain = "[('journal_id','=',journal_id)]",
								domain = "[]",
								readonly=True, states={'draft': [('readonly', False)]}, copy=False)
	move_ids = fields.Many2many('account.move', string="Moves", readonly=True, copy=False)
	
	description = fields.Text('Description', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
	
	#THANH: field journal_id will be removed
	journal_id = fields.Many2one('account.journal', string='Journal', help='Journal for the move', required=False, 
								readonly=True, states={'draft': [('readonly', False)]})
	
# 	@api.onchange('journal_id')
# 	def _onchange_journal_id(self):
# 		if self.journal_id:
# 			model_ids = [x.id for x in self.env['account.regularization.model'].search([('active','=',True), ('journal_id','=',self.journal_id.id)])]
# 			self.model_ids = [(6, 0, model_ids)]
# 		else:
# 			self.model_ids = False
			
class AccountRegularizationLine(models.Model):
	_name = 'account.regularization.line'
	_description = 'Account Regularization Details'
	order = 'acc_code'
	
	regularization_id = fields.Many2one('account.regularization', string='Parent')
	acc_id = fields.Integer(string="Account ID") 
	acc_code = fields.Char(string="Account Code") 

	debit = fields.Monetary(string="Debit",currency_field='com_currency_id')
	credit = fields.Monetary(string="Credit",currency_field='com_currency_id')
	balance = fields.Monetary(string="Balance",currency_field='com_currency_id')
	
	debit_second = fields.Monetary(string="2nd Debit",currency_field='second_currency_id')
	credit_second = fields.Monetary(string="2nd Credit",currency_field='second_currency_id')
	balance_second = fields.Monetary(string="2nd Balance",currency_field='second_currency_id')
	
	com_currency_id = fields.Many2one('res.currency', string="Currency")
	second_currency_id = fields.Many2one('res.currency', string="2nd Currency")

class AccountMove(models.Model):
	_inherit = "account.move"

	regularization_id = fields.Many2one('account.regularization', string='Regularization')
	
	@api.multi
	def button_cancel(self):
		#THANH: Kiểm tra nếu bút toán liên quan đến kết chuyển thì báo lỗi
		pass_check = self._context and self._context.get('force_cancel',False) or False
		for move in self:
			if move.regularization_id and not pass_check:
				raise UserError(_("This Journal Entry created from menu Regularization. You must cancel Regularization firstly."))
		return super(AccountMove, self).button_cancel()
	
