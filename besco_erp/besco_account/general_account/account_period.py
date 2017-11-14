# -*- coding: utf-8 -*-
from lxml import etree
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import SUPERUSER_ID, api
from openerp import api, fields, models, _

from openerp.osv import expression
from openerp.exceptions import UserError, ValidationError

class account_fiscalyear(models.Model):
    _name = "account.fiscalyear"
    _description = "Fiscal Year"
    _order = "date_start, id"
    
    @api.one
    def _load_opening(self):
        self.opening_entry_ids = self.env['account.move'].search([('journal_id.type','=','situation'),
                                                                      ('state','=','posted'),
                                                                      ('date','>=',self.date_start),
                                                                      ('date','<=',self.date_stop)])
        
    name = fields.Char('Fiscal Year', required=True, readonly=True, states={'draft': [('readonly', False)]})
    code = fields.Char('Code', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_start = fields.Date('Start Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    date_stop = fields.Date('End Date', required=True, readonly=True, states={'draft': [('readonly', False)]})
    period_ids = fields.One2many('account.period', 'fiscalyear_id', 'Periods', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True, copy=False, default='draft')
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    
    #THANH: 2 fields for closing va opening balance
    next_fiscalyear_id = fields.Many2one('account.fiscalyear', 'Next Fiscal Year', states={'done':[('readonly',True)]},
                                         domain="[('state','=','draft'), ('date_start','>',date_stop)]")
    
    closing_entry_ids = fields.Many2many('account.move', 'account_fiscalyear_closing_entry_rel', 'fiscalyear_id', 'move_id', 
                                         string='Closing Entries', readonly=True)
    closing_balances = fields.One2many('account.fiscalyear.closing', 'fiscalyear_id', 'Closing Balances', copy=False, readonly=True)
    
    opening_entry_ids = fields.Many2many('account.move', 'account_fiscalyear_opening_entry_rel', 'fiscalyear_id', 'move_id', 
                                         string='Opening Entries', compute='_load_opening', store=False, readonly=True)
    
#     opening_balances = fields.Many2many('account.move.line', string='Opening Balances', compute='_load_opening', store=False)
    
    @api.multi
    def load_data(self):
        open_periods = self.env['account.period'].search([('fiscalyear_id','=',self.id), ('state','=','draft')])
        if open_periods:
            raise UserError(_('You have to close all periods before closing this Fiscal Year!'))
        
        account_obj = self.env['account.account']
        closing_obj = self.env['account.fiscalyear.closing']
        uid = self.env.user.id
        
        for fiscalyear in self:
            company_id = self.company_id.id
            currency_id = self.company_id.currency_id and self.company_id.currency_id.id or False
            second_currency_id = self.company_id.second_currency_id and self.company_id.second_currency_id.id or False
            
            #Get company info
            sql ='''
                delete from account_fiscalyear_closing where fiscalyear_id = %s;
            '''%(fiscalyear.id)
            self.env.cr.execute(sql)
            
            journal_ids = [x.id for x in self.env['account.journal'].search([])]
            journal_ids = (','.join(map(str, journal_ids)))
            #THANH: use this to pass list into an sql function
            journal_ids = '{%(journal_ids)s}'%({'journal_ids':journal_ids,})
            
            sql = _('''
                Insert Into account_fiscalyear_closing (create_uid, create_date, write_uid, write_date,
                    account_id, acc_code, acc_name, internal_type, acc_level, 
                    end_dr, end_cr,
                    end_dr_2rd, end_cr_2rd,
                    fiscalyear_id, com_currency_id)
                SELECT  %s, current_timestamp, %s, current_timestamp,
                    coa_id, coa_code, coa_name, internal_type, acc_level, 
                    end_dr, end_cr, 
                    end_dr_2rd, end_cr_2rd, 
                    %s, %s
                FROM fi_tb_closing_fiscalyear('%s'::DATE, '%s'::DATE, %s::integer, '%s'::DATE, '%s'::INT[])
                WHERE 
                    (end_dr notnull or end_cr notnull)
                    and acc_level != 10
                ORDER BY acc_level, coa_code
            ''')
            sql = sql%(uid, uid, fiscalyear.id, currency_id, fiscalyear.date_start, fiscalyear.date_stop, company_id, fiscalyear.date_stop, journal_ids)
            self.env.cr.execute(sql)
            
            #THANH: run this sql before insert details partner balance because it will compute balance details also
            sql = _('''
                    Insert Into account_fiscalyear_closing (create_uid, create_date, write_uid, write_date,
                        acc_type, acc_name, internal_type, 
                        end_dr, end_cr,
                        end_dr_2rd, end_cr_2rd,
                        fiscalyear_id, com_currency_id)
                    SELECT  %s, current_timestamp, %s, current_timestamp,
                        'view' as acc_type, 'Total Public' as coa_name, 'public' as internal_type, 
                        sum(end_dr), sum(end_cr), 
                        sum(end_dr_2rd), sum(end_cr_2rd), 
                        %s, %s
                    FROM account_fiscalyear_closing
                    WHERE fiscalyear_id = %s and acc_type is null and internal_type = 'public';
                    
                    Insert Into account_fiscalyear_closing (create_uid, create_date, write_uid, write_date,
                        acc_type, acc_name, internal_type, 
                        end_dr, end_cr,
                        end_dr_2rd, end_cr_2rd,
                        fiscalyear_id, com_currency_id)
                    SELECT  %s, current_timestamp, %s, current_timestamp,
                        'view' as acc_type, 'Total Internal' as coa_name, 'internal' as internal_type, 
                        sum(end_dr), sum(end_cr), 
                        sum(end_dr_2rd), sum(end_cr_2rd), 
                        %s, %s
                    FROM account_fiscalyear_closing
                    WHERE fiscalyear_id = %s and acc_type is null and internal_type = 'internal';
                    
                    Insert Into account_fiscalyear_closing (create_uid, create_date, write_uid, write_date,
                        acc_type, acc_name, internal_type, 
                        end_dr, end_cr,
                        end_dr_2rd, end_cr_2rd,
                        fiscalyear_id, com_currency_id)
                    SELECT  %s, current_timestamp, %s, current_timestamp,
                        'view' as acc_type, 'Total' as coa_name, 'view' as internal_type, 
                        sum(end_dr), sum(end_cr), 
                        sum(end_dr_2rd), sum(end_cr_2rd), 
                        %s, %s
                    FROM account_fiscalyear_closing
                    WHERE fiscalyear_id = %s and acc_type is null and internal_type in ('internal','public');
                ''')
            sql = sql%(uid, uid, fiscalyear.id, currency_id, fiscalyear.id,
                       uid, uid, fiscalyear.id, currency_id, fiscalyear.id,
                       uid, uid, fiscalyear.id, currency_id, fiscalyear.id)
            self.env.cr.execute(sql)
            
            full_accounts_dict = {}
            for line in fiscalyear.closing_balances:
                if line.acc_code:
                    full_accounts = account_obj.search_read([('id','!=',line.account_id.id), ('parent_id','parent_of',line.account_id.id), ('level','>=',2)],
                                                            ['code','type','name','level'], order='code,level')
                    for account in full_accounts:
                        if not full_accounts_dict.has_key(account['code']):
                            full_accounts_dict.update({account['code']: 
                                                       {'acc_code':account['code'], 'acc_name':account['name'], 'acc_type':account['type'], 'acc_level': account['level'],
                                                        'account_id':account['id'],
                                                        'end_dr': line.end_dr, 
                                                        'end_cr': line.end_cr, 
                                                        'end_dr_2rd': line.end_dr_2rd, 
                                                        'end_cr_2rd': line.end_cr_2rd, 
                                                        
                                                        'fiscalyear_id': fiscalyear.id, 'com_currency_id': line.com_currency_id.id, 
                                                        'internal_type': 'view',
                                                        }})
                        else:
                            full_accounts_dict.update({account['code']: 
                                                       {'acc_code':account['code'], 'acc_name':account['name'], 'acc_type':account['type'], 'acc_level': account['level'],
                                                        'account_id':account['id'],
                                                        'end_dr': full_accounts_dict[account['code']]['end_dr'] + line.end_dr, 
                                                        'end_cr': full_accounts_dict[account['code']]['end_cr'] + line.end_cr, 
                                                        'end_dr_2rd': full_accounts_dict[account['code']]['end_dr_2rd'] + line.end_dr_2rd, 
                                                        'end_cr_2rd': full_accounts_dict[account['code']]['end_cr_2rd'] + line.end_cr_2rd,
                                                        
                                                        'fiscalyear_id': fiscalyear.id, 'com_currency_id': line.com_currency_id.id,
                                                        'internal_type': 'view',
                                                        }})
                if line.account_id.type in ['receivable','payable']:
                    sql ='''
                            Insert Into account_fiscalyear_closing (create_uid, create_date, write_uid, write_date,
                                account_id, acc_code, acc_level, partner_id, internal_type,
                                end_dr, end_cr,
                                end_dr_2rd, end_cr_2rd,
                                fiscalyear_id, com_currency_id)
                                
                            SELECT  %s, current_timestamp, %s, current_timestamp,
                                %s, '%s', %s, partner_id, internal_type,
                                end_dr, end_cr, 
                                end_dr_2nd, end_cr_2nd,
                                %s, %s
                            FROM fi_tb_closing_partner_balance('%s','%s', %s, %s)
                            where (end_dr is not null and end_dr != 0.0) or (end_cr is not null and end_cr != 0.0)
                    '''%(uid, uid, line.account_id.id, line.account_id.code, line.account_id.level, fiscalyear.id, currency_id,
                        fiscalyear.date_start, fiscalyear.date_stop, line.account_id.id, company_id)
                    self.env.cr.execute(sql)
                    line.write({'acc_type': 'view',
                                'internal_type': 'view',})

            for key, vals in full_accounts_dict.items():
                closing_obj.create(vals)
        
    @api.one
    @api.constrains('date_start','date_stop')
    def _check_fiscalyear(self):
        if self.date_stop < self.date_start:
            raise ValidationError('The start date of a fiscal year must precede its end date.')
    
    @api.multi
    def action_reopen(self):
        for fiscalyear in self:
            for closing_entry_id in fiscalyear.closing_entry_ids:
                closing_entry_id.button_cancel()
                closing_entry_id.unlink()
        self.write({'state':'draft'})
        
    @api.multi
    def action_close(self):
        #THANH: New function to close a fiscal year
        if not self.next_fiscalyear_id:
            raise UserError(_('Please choose next fiscal year!'))
        open_periods = self.env['account.period'].search([('fiscalyear_id','=',self.id), ('state','=','draft')])
        if open_periods:
            raise UserError(_('You have to close all periods before closing this Fiscal Year!'))
        
        self.env.cr.execute('''
            select distinct internal_type
            from account_fiscalyear_closing
            where fiscalyear_id = %s and internal_type != 'view'
        '''%(self.id))
        journal_types = [x[0] for x in self.env.cr.fetchall()]
        
        if 'public' in journal_types:
            open_journal_public = self.env['account.journal'].search([('type','=','situation'), ('internal_type','=','public')], limit=1)
            if not open_journal_public:
                raise UserError(_('There is no Opening Journal Public. Please contact Administrator!'))
            if not open_journal_public.default_credit_account_id or not open_journal_public.default_debit_account_id:
                raise UserError(_('Please define default debit or creadit account on the journal public (%s)!')%(open_journal_public.name))
            opening_public_account_id = open_journal_public.default_debit_account_id.id
        if 'internal' in journal_types:
            open_journal_internal = self.env['account.journal'].search([('type','=','situation'), ('internal_type','=','internal')], limit=1)
            if not open_journal_internal:
                raise UserError(_('There is no Opening Journal Internal. Please contact Administrator!'))
            if not open_journal_internal.default_credit_account_id or not open_journal_internal.default_debit_account_id:
                raise UserError(_('Please define default debit or creadit account on the journal internal (%s)!')%(open_journal_internal.name))
            opening_internal_account_id = open_journal_internal.default_debit_account_id.id
        
        
        ctx = {}
        ctx['date'] = self.next_fiscalyear_id.date_start
        ctx['check_move_validity'] = False
        
        closing_entries = []
        for journal_type in journal_types:
            if journal_type == 'public':
                open_journal = open_journal_public
                opening_account_id = opening_public_account_id
            if journal_type == 'internal':
                open_journal = open_journal_internal
                opening_account_id = opening_internal_account_id
                
            move_vals = {
                            'name': '/',
                            'journal_id': open_journal.id,
                            'narration': 'Opening Entries at %s'%(self.next_fiscalyear_id.name),
                            'date': self.next_fiscalyear_id.date_start,
                            'doc_date': self.next_fiscalyear_id.date_start,
                        }
            move = self.env['account.move'].create(move_vals)
            move_line_obj = self.env['account.move.line']
            move_line = {
                    'journal_id': open_journal.id,
                    'name': 'Opening Balance at %s'%(self.next_fiscalyear_id.name),
                    'date': self.next_fiscalyear_id.date_start,
                    'move_id': move.id,
                    
                    'rate_type': self.company_id.second_currency_id and 'transaction_rate' or False,
                    'currency_id': self.company_id.second_currency_id and self.company_id.second_currency_id.id or False,
                }
             
            total_dr, total_cr, total_dr_2rd, total_cr_2rd = 0.0, 0.0, 0.0, 0.0
            for line in self.closing_balances:
                if line.acc_type == 'view':
                    continue
                if line.internal_type != journal_type:
                    continue
                
                balance = line.end_dr - line.end_cr
                total_dr += line.end_dr
                total_cr += line.end_cr
                
                move_line_vals = {
                    'account_id': line.account_id.id,
                    'partner_id': line.partner_id and line.partner_id.id or False,
                    'debit': balance > 0 and balance or 0.0,
                    'credit': balance < 0 and abs(balance) or 0.0,
                }
                balance_2rd = line.end_dr_2rd - line.end_cr_2rd
                if self.company_id.second_currency_id and balance_2rd and balance:
                    total_dr_2rd += line.end_dr_2rd
                    total_cr_2rd += line.end_cr_2rd
                    if abs(balance_2rd) > abs(balance):
                        currency_ex_rate = self.company_id.second_currency_id.round(balance_2rd / balance)
                    else:
                        currency_ex_rate = self.company_id.second_currency_id.round(balance / balance_2rd)
                    move_line_vals.update({
                        'currency_ex_rate': currency_ex_rate,
                        'amount_currency': balance_2rd,
                    })
                move_line_vals.update(move_line)
                move_line_obj.with_context(ctx).create(move_line_vals)
                
            if total_dr:
                move_line_vals = {
                    'account_id': opening_account_id,
                    'debit': 0.0,
                    'credit': total_dr,
                }
                if self.company_id.second_currency_id and total_dr_2rd and total_dr:
                    if total_dr_2rd > total_dr:
                        currency_ex_rate = self.company_id.second_currency_id.round(total_dr_2rd / total_dr)
                    else:
                        currency_ex_rate = self.company_id.second_currency_id.round(total_dr / total_dr_2rd)
                    move_line_vals.update({
                        'currency_ex_rate': currency_ex_rate,
                        'amount_currency': -1 * total_dr_2rd,
                    })
                move_line_vals.update(move_line)
                move_line_obj.with_context(ctx).create(move_line_vals)
            
            if total_cr:
                move_line_vals = {
                    'account_id': opening_account_id,
                    'debit': total_cr,
                    'credit': 0.0,
                }
                if self.company_id.second_currency_id and total_cr_2rd and total_cr:
                    if total_cr_2rd > total_cr:
                        currency_ex_rate = self.company_id.second_currency_id.round(total_cr_2rd / total_cr)
                    else:
                        currency_ex_rate = self.company_id.second_currency_id.round(total_cr / total_cr_2rd)
                    move_line_vals.update({
                        'currency_ex_rate': currency_ex_rate,
                        'amount_currency': total_cr_2rd,
                    })
                move_line_vals.update(move_line)
                move_line_obj.with_context(ctx).create(move_line_vals)
            
            move.post()
            closing_entries.append(move.id)
            
        self.closing_entry_ids = closing_entries
        self.state = 'done'
    
    @api.multi
    def create_period3(self):
        self.env.interval = 3
        return self.create_period()
    
    @api.multi
    def create_period(self):
        interval = hasattr(self.env, 'interval') and self.env.interval or 1
        period_obj = self.env['account.period']
        for fy in self:
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
            
            exist_period = period_obj.search([('date_start','=',ds), ('date_stop','=',ds)])
            if not exist_period:
                period_obj.create({
                        'name':  "%s %s" % (_('Opening Period'), ds.strftime('%Y')),
                        'code': '00/' + fy.name,
                        'date_start': ds,
                        'date_stop': ds,
                        'special': True,
                        'fiscalyear_id': fy.id,
                    })
            
            dem = 0
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')
                
                dem += 1
                code = '%%0%sd' % 2 % dem
                exist_period = period_obj.search([('date_start','=',ds.strftime('%Y-%m-%d')), ('date_stop','=',de.strftime('%Y-%m-%d'))])
                if exist_period:
                    ds = ds + relativedelta(months=interval)
                    continue
                period_obj.create({
                    'name': ds.strftime('%m/%Y'),
                    'code': code + '/' + fy.name,
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
        return True
    
    @api.multi
    def find(self, dt=None, exception=True):
        res = self.finds(dt, exception)
        return res and res[0] or False
    
    @api.multi
    def finds(self, dt=None, exception=True):
        context = self._context or {}
        if not dt:
            dt = fields.date.context_today()
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            company_id = context['company_id']
        else:
            company_id = self.env.user.company_id.id
        args.append(('company_id', '=', company_id))
        ids = self.search(args)
        if not ids:
            if exception:
                model, action_id = self.pool['ir.model.data'].get_object_reference('account', 'action_account_fiscalyear')
                msg = _('No accounting period is covering this date: %s.') % dt
                raise openerp.exceptions.RedirectWarning(msg, action_id, _(' Configure Fiscal Year Now'))
            else:
                return []
        return ids
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()

class account_period(models.Model):
    _name = "account.period"
    _description = "Account period"
    _order = "date_start, special desc"
    
    name = fields.Char('Period Name', required=True)
    code = fields.Char('Code')
    special = fields.Boolean('Opening/Closing Period',help="These periods can overlap.")
    date_start = fields.Date('Start of Period', required=True, states={'done':[('readonly',True)]})
    date_stop = fields.Date('End of Period', required=True, states={'done':[('readonly',True)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]}, select=True)
    state = fields.Selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True, copy=False, default = 'draft',
                              help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.')
    company_id = fields.Many2one('res.company', related='fiscalyear_id.company_id', string='Company', store=True, readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]
    
    @api.one
    @api.constrains('date_start','date_stop')
    def _check_period(self):
        #THANH: _check_duration
        if self.date_stop < self.date_start:
            raise ValidationError('The duration of the Period(s) is/are invalid.')
        
        #THANH: _check_year_limit
        if self.special:
            return

        if self.fiscalyear_id.date_stop < self.date_stop or \
           self.fiscalyear_id.date_stop < self.date_start or \
           self.fiscalyear_id.date_start > self.date_start or \
           self.fiscalyear_id.date_start > self.date_stop:
            raise ValidationError('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.')

        pids = self.search([('date_stop','>=',self.date_start),('date_start','<=',self.date_stop),('special','=',False),('id','<>',self.id)])
        for period in pids:
            if period.fiscalyear_id.company_id.id==self.fiscalyear_id.company_id.id:
                raise ValidationError('The period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.')
        
    @api.returns('self')
    def next(self, cr, uid, period, step, context=None):
        ids = self.search(cr, uid, [('date_start','>',period.date_start)])
        if len(ids)>=step:
            return ids[step-1]
        return False

    @api.returns('self')
    def find(self, cr, uid, dt=None, context=None):
        if context is None: context = {}
        if not dt:
            dt = fields.date.context_today(self, cr, uid, context=context)
        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
        if context.get('company_id', False):
            args.append(('company_id', '=', context['company_id']))
        else:
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            args.append(('company_id', '=', company_id))
        result = []
        if context.get('account_period_prefer_normal', True):
            # look for non-special periods first, and fallback to all if no result is found
            result = self.search(cr, uid, args + [('special', '=', False)], context=context)
        if not result:
            result = self.search(cr, uid, args, context=context)
        if not result:
            model, action_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'account', 'action_account_period')
            msg = _('No accounting period is covering this date: %s.') % dt
            raise openerp.exceptions.RedirectWarning(msg, action_id, _('Configure Periods Now'))
        return result
    
    @api.multi
    def action_draft(self):
        mode = 'draft'
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise UserError(_('You can not re-open a period which belongs to closed fiscal year'))
            self._cr.execute('update account_period set state=%s where id = %s', (mode, period.id,))
        return True
    
    @api.multi
    def action_close(self):
        account_move_obj = self.env['account.move']
        
        mode = 'done'
        for period in self:
            account_move_ids = account_move_obj.search([
                             ('date','>=',period.date_start),
                             ('date','<=',period.date_stop),('state', '=', "draft")])
            if account_move_ids:
                raise UserError(('In order to close a period, you must first post related journal entries.'))
            self._cr.execute('update account_period set state=%s where id = %s', (mode, period.id,))
        return True
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if args is None:
            args = []
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            domain = [('code', operator, name), ('name', operator, name)]
        else:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        recs = self.search(expression.AND([domain, args]), limit=limit)
        return recs.name_get()
    
    
    @api.multi
    def build_ctx_periods(self, period_from_id, period_to_id):
        if period_from_id == period_to_id:
            return [period_from_id]
        period_from = self.browse(period_from_id)
        period_date_start = period_from.date_start
        company1_id = period_from.company_id.id
        period_to = self.browse(period_to_id)
        period_date_stop = period_to.date_stop
        company2_id = period_to.company_id.id
        if company1_id != company2_id:
            raise UserError(_('You should choose the periods that belong to the same company.'))
        if period_date_start > period_date_stop:
            raise UserError(_('Start period should precede then end period.'))

        # /!\ We do not include a criterion on the company_id field below, to allow producing consolidated reports
        # on multiple companies. It will only work when start/end periods are selected and no fiscal year is chosen.

        #for period from = january, we want to exclude the opening period (but it has same date_from, so we have to check if period_from is special or not to include that clause or not in the search).
        if period_from.special:
            res_ids = [x.id for x in self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop)])]
            return res_ids
        res_ids = [x.id for x in self.search([('date_start', '>=', period_date_start), ('date_stop', '<=', period_date_stop), ('special', '=', False)])]
        return res_ids

class account_fiscalyear_closing(models.Model):
    _name = "account.fiscalyear.closing"
    _order = "acc_code,acc_level,id"
  
    fiscalyear_id = fields.Many2one('account.fiscalyear')
      
    
    acc_level = fields.Integer(string="Acc Level")
    acc_type = fields.Char(string="Acc Type")#THANH: store it view account
    acc_code = fields.Char(string="Acc Code")
    acc_name = fields.Char(string="Acc Name")
    account_id = fields.Many2one('account.account', string="Account")
    partner_id = fields.Many2one('res.partner', string="Partner")
    internal_type = fields.Selection([
            ('view', 'View'),
            ('public', 'Public'),
            ('internal', 'Internal'),
        ], string='Internal Type', default='public')
    
    begin_dr = fields.Monetary(string="Begin Dr", currency_field='com_currency_id')
    begin_cr = fields.Monetary(string="Begin Cr", currency_field='com_currency_id')
    period_dr = fields.Monetary(string="Period Dr", currency_field='com_currency_id')
    period_cr = fields.Monetary(string="Period Cr", currency_field='com_currency_id')
    end_dr = fields.Monetary(string="End Dr", currency_field='com_currency_id')
    end_cr = fields.Monetary(string="End Cr", currency_field='com_currency_id')
    com_currency_id = fields.Many2one('res.currency', string="Currency", readonly=True)
    
    begin_dr_2rd = fields.Monetary(string="Begin Dr", currency_field='second_currency_id')
    begin_cr_2rd = fields.Monetary(string="Begin Cr", currency_field='second_currency_id')
    period_dr_2rd = fields.Monetary(string="Period Dr", currency_field='second_currency_id')
    period_cr_2rd = fields.Monetary(string="Period Cr", currency_field='second_currency_id')
    end_dr_2rd = fields.Monetary(string="End Dr", currency_field='second_currency_id')
    end_cr_2rd = fields.Monetary(string="End Cr", currency_field='second_currency_id')
    second_currency_id = fields.Many2one('res.currency', string="2nd Currency", readonly=True)
    
    
        