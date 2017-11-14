# -*- coding: utf-8 -*-
import openerp
from openerp import tools, api
from openerp.osv.expression import get_unaccent_wrapper
from openerp.tools.translate import _
from openerp.exceptions import UserError
import time
from datetime import datetime
from openerp.tools import float_round, float_is_zero, float_compare

from openerp import models, fields
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class ResCompany(models.Model):
    _inherit = "res.company"

    second_currency_id = fields.Many2one('res.currency', string='Second Currency')
    incomce_from_advance_payment_id = fields.Many2one('account.account', string='Income From Advance Payment')
    interest_income_shipment_id = fields.Many2one('account.account', string='Interest income shipment')

class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"
    
    #THANH: when user change rate manually, this field will be updated to False and these is a cron to update rate to Account Move Line
    update_rate =fields.Boolean(string="Update", default = False)
    
    @api.multi
    def write(self, vals):
        vals.update({'update_rate':False})
        return super(ResCurrencyRate, self).write(vals)
    
    @api.multi
    def update_account_move_line(self, date=False, currency_id=False):
        date = self.name or date
        currency = self.currency_id or self.env['res.currency'].browse(currency_id)
        if not date or not currency:
            return
        
        self.env.cr.execute('''SELECT name, state
                                FROM account_period
                                WHERE company_id = %(company_id)s 
                                    and date(timezone('UTC', '%(date_rate)s'::timestamp)) between date_start and date_stop
                            '''
                            %({
                                  'date_rate': date,
                                  'company_id': self.env.user.company_id.id
                            }))
        for period in self.env.cr.dictfetchall():
            if period['state'] == 'done':
                raise UserError(_("Period %s has been closed"%(period['name'])))
        
        ctx = {'allow_update':True, 'check_move_validity': False}
        move_line_obj = self.env['account.move.line']
        company_currency = self.env.user.company_id.currency_id
        second_currency = self.env.user.company_id.second_currency_id
        if not second_currency:
            second_currency_id = 'null'
        else:
            second_currency_id = second_currency.id
            
        currency.currency_type 
        self.env.cr.execute('''SELECT coalesce((select name from res_currency_rate 
                                    where currency_id = %(currency_id)s and name < date(timezone('UTC', '%(date_rate)s'::timestamp))
                                    order by name desc limit 1), '2000-01-01') from_date,
                                    date(timezone('UTC', '%(date_rate)s'::timestamp)) end_date
                            '''
                            %({
                                  'date_rate': date,
                                  'currency_id': currency.currency_type == 'basic' and company_currency.id or currency.id,
                            }))
        res_date = self.env.cr.fetchone()
        from_date = res_date[0]
        end_date = res_date[1]
            
        sql = ''
        ex_currency_rate, currency_rate = currency.with_context({'date':date})._get_conversion_rate(currency, company_currency)
        if currency == second_currency:
            #THANH: 
            #TH1: Cap nhat lai ty gia theo ngay cho field 2nd currency va currency_id == second currency
            #TH2: TH2: Cap nhat ty gia cho debit va credit neu rate thay doi va currency_id == 2nd currency (tien te giao dich = 2nd currency)
            #TH3: Cap nhat ty gia va tinh 2nd amount currency dua tren debit va credit cho 2nd currency neu currency_id != 2nd currency
            ex_second_rate, second_rate = currency.with_context({'date':date})._get_conversion_rate(company_currency, second_currency)
            ex_2nd_company_rate, second_company_rate = currency.with_context({'date':date})._get_conversion_rate(second_currency, company_currency)
            if second_rate != 1:
                #THANH: need to use orm method to update some function fields like (balance, residual)
                #TH2: Cap nhat ty gia cho debit va credit neu rate thay doi va currency_id == 2nd currency (tien te giao dich = 2nd currency)
                lines = move_line_obj.search([('date','>',from_date), 
                                              ('date','<=',end_date),
                                              ('rate_type','=','average_rate'),
                                              ('currency_id','!=',False),
                                              ('amount_currency','!=',False),
                                              ('currency_id','=',second_currency.id)])
                for line in lines:
                    debit_credit = company_currency.round(abs(line.amount_currency * ex_2nd_company_rate))
                    if line.amount_currency > 0:
                        line.with_context(ctx).write({'debit': debit_credit})
                    else:
                        line.with_context(ctx).write({'credit': debit_credit})
                        
                sql += ''' 
                        --TH1: Cap nhat lai ty gia theo ngay cho field 2nd currency va currency_id == second currency
                            UPDATE account_move_line
                                SET second_amount = amount_currency, 
                                    second_ex_rate = %(second_rate)s,
                                    currency_ex_rate = %(second_rate)s,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND aml.rate_type = 'average_rate'
                                            AND aml.currency_id is not null AND aml.amount_currency != 0
                                            AND aml.currency_id = %(second_currency_id)s
                                        );
                                
                        --TH3: Cap nhat ty gia va tinh 2nd amount currency dua tren debit va credit cho 2nd currency neu currency_id != 2nd currency
                             UPDATE account_move_line
                                SET second_amount = (debit - credit) * %(ex_second_rate)s, 
                                    second_ex_rate = %(second_rate)s,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND aml.rate_type = 'average_rate'
                                            AND ((aml.currency_id is not null  AND aml.amount_currency != 0 
                                            AND aml.currency_id != %(second_currency_id)s) or aml.currency_id is null)
                                        );
                    '''
                sql = sql%({
                      'from_date': from_date,
                      'end_date': end_date,
                      'ex_second_rate': ex_second_rate,
                      'second_currency_id': second_currency_id,
                      'second_rate': second_rate,
                      'ex_2nd_company_rate': ex_2nd_company_rate,
                      'company_currency_id': company_currency.id,
                      })
            
            #THANH: in case currency_id = second_currency_id, this sql will update again rate
            extend_sql = _('''
               UPDATE account_move_line
                    SET 
                        second_amount = (debit - credit) * %(ex_second_rate)s, 
                        second_ex_rate = %(second_rate)s,
                        second_currency_id = %(second_currency_id)s
                WHERE 
                    id in (select aml.id 
                            from account_move_line aml
                                join account_move am on aml.move_id = am.id
                            where am.state = 'posted'
                                AND aml.date > '%(from_date)s'
                                AND aml.date <= '%(end_date)s'
                                AND aml.rate_type = 'transaction_rate'
                                AND aml.currency_id is not null AND aml.currency_id != %(second_currency_id)s
                            );
                
                UPDATE account_move_line
                    SET 
                        second_amount = amount_currency, 
                        second_ex_rate = currency_ex_rate,
                        second_currency_id = %(second_currency_id)s
                WHERE 
                    id in (select aml.id 
                            from account_move_line aml
                                join account_move am on aml.move_id = am.id
                            where am.state = 'posted'
                                AND aml.date > '%(from_date)s'
                                AND aml.date <= '%(end_date)s'
                                AND aml.rate_type = 'transaction_rate'
                                AND aml.currency_id is not null AND aml.currency_id = %(second_currency_id)s
                            );
            ''')
            extend_sql = extend_sql%({
                'from_date': from_date,
                'end_date': end_date,
                'ex_second_rate': ex_second_rate,
                'second_currency_id': second_currency_id,
                'second_rate': second_rate,
                'ex_2nd_company_rate': ex_2nd_company_rate,
                'company_currency_id': company_currency.id,
            })
            sql += extend_sql
            
        if currency == company_currency:
            #THANH: Cap nhat ty gia cho field 2nd currency va currency_id == second currency
            if second_currency:
                ex_second_rate, second_rate = currency.with_context({'date':date})._get_conversion_rate(currency, second_currency)
                ex_2nd_company_rate, second_company_rate = currency.with_context({'date':date})._get_conversion_rate(second_currency, company_currency)
                if second_rate != 1:
                    #THANH: need to use orm method to update some function fields like (balance, residual)
                    #TH2: if currency_id = 2nd_currency => update debit, credit, exchange rate va 2nd currency
                    lines = move_line_obj.search([('date','>',from_date), 
                                                  ('date','<=',end_date),
                                                  ('rate_type','=','average_rate'),
                                                  ('currency_id','!=',False),
                                                  ('amount_currency','!=',False),
                                                  ('currency_id','=',second_currency.id)])
                    for line in lines:
                        debit_credit = company_currency.round(abs(line.amount_currency * ex_2nd_company_rate))
                        if line.amount_currency > 0:
                            line.with_context(ctx).write({'debit': debit_credit,
                                        'currency_ex_rate': second_rate,
                                        'second_amount': abs(line.amount_currency),
                                        'second_ex_rate': second_rate,
                                        'second_currency_id': second_currency_id})
                        else:
                            line.with_context(ctx).write({'credit': debit_credit,
                                        'currency_ex_rate': second_rate,
                                        'second_amount': line.amount_currency,
                                        'second_ex_rate': second_rate,
                                        'second_currency_id': second_currency_id})
                            
                    sql += ''' 
                        --TH1: Cap nhat gia tri va ty gia cho tien te thu 2 dua tren debit va credit va currency_id != 2nd currency
                             UPDATE account_move_line
                                SET second_amount = (debit * %(ex_second_rate)s), 
                                    second_ex_rate = %(second_rate)s,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND aml.rate_type = 'average_rate'
                                            AND ((aml.currency_id is not null AND aml.amount_currency != 0 and aml.currency_id != %(second_currency_id)s) or aml.currency_id is null)
                                            AND aml.debit > 0
                                        );
                                        
                                
                            UPDATE account_move_line
                                SET second_amount = (-1) * (credit * %(ex_second_rate)s), 
                                    second_ex_rate = %(second_rate)s,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND aml.rate_type = 'average_rate'
                                            AND ((aml.currency_id is not null AND aml.amount_currency != 0 and aml.currency_id != %(second_currency_id)s) or aml.currency_id is null)
                                            AND aml.credit > 0
                                        );
                                        
                                
                        --THANH: update 2nd value when rate_type = 'transaction_rate' and aml.currency_id != second_currency_id
                            UPDATE account_move_line
                                SET second_amount = (debit - credit) * %(ex_second_rate)s, 
                                    second_ex_rate = %(second_rate)s,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND aml.currency_id is not null AND aml.currency_id != %(second_currency_id)s
                                            AND aml.rate_type = 'transaction_rate'
                                        );
                                        
                            --THANH: update 2nd value when rate_type = 'transaction_rate' and aml.currency_id = second_currency_id
                            UPDATE account_move_line
                                SET second_amount = amount_currency, 
                                    second_ex_rate = currency_ex_rate,
                                    second_currency_id = %(second_currency_id)s
                            WHERE 
                                id in (select aml.id 
                                        from account_move_line aml
                                            join account_move am on aml.move_id = am.id
                                        where am.state = 'posted'
                                            AND aml.date > '%(from_date)s'
                                            AND aml.date <= '%(end_date)s'
                                            AND ((aml.currency_id is not null AND aml.currency_id = %(second_currency_id)s)
                                                    or aml.currency_id is null)
                                            AND aml.rate_type = 'transaction_rate'
                                        );
                    '''
                    sql = sql%({
                          'from_date': from_date,
                          'end_date': end_date,
                          'ex_2nd_company_rate': ex_2nd_company_rate,
                          'ex_second_rate': ex_second_rate,
                          'second_currency_id': second_currency_id,
                          'second_rate': second_rate,
                          'ex_currency_rate': ex_currency_rate,
                          'currency_rate': currency_rate,
                          'company_currency_id': company_currency.id,
                          })
                    
        if currency != company_currency and (second_currency and currency != second_currency):
            #THANH: need to use orm method to update some function fields like (balance, residual)
            
            ex_second_rate, second_rate = currency.with_context({'date':date})._get_conversion_rate(currency, second_currency)
            ex_2nd_company_rate, second_company_rate = currency.with_context({'date':date})._get_conversion_rate(currency, company_currency)
            if second_rate != 1:
                lines = move_line_obj.search([('date','>',from_date), 
                                              ('date','<=',end_date),
                                              ('rate_type','<=','average_rate'),
                                              ('currency_id','!=',False),
                                              ('amount_currency','!=',False),
                                              ('currency_id','=',currency.id)])
                for line in lines:
                    debit_credit = company_currency.round(abs(line.amount_currency * ex_2nd_company_rate))
                    if line.amount_currency > 0:
                        line.with_context(ctx).write({'debit': debit_credit,
                                    'currency_ex_rate': currency_rate,
                                    'second_amount': abs(line.amount_currency * ex_currency_rate * ex_second_rate),
                                    'second_ex_rate': second_rate,
                                    'second_currency_id': second_currency_id})
                    else:
                        line.with_context(ctx).write({'credit': debit_credit,
                                    'currency_ex_rate': currency_rate,
                                    'second_amount': line.amount_currency * ex_currency_rate * ex_second_rate,
                                    'second_ex_rate': second_rate,
                                    'second_currency_id': second_currency_id})
                        
                sql += _('''
                    --THANH: update 2nd value when amount_currency == 0 and currency_id is not null due to currency revaluation
                        UPDATE account_move_line
                            SET second_amount = abs(debit - credit) / %(ex_currency_rate)s,
                                second_ex_rate = %(second_rate)s,
                                second_currency_id = %(second_currency_id)s
                        WHERE 
                            id in (select aml.id 
                                    from account_move_line aml
                                        join account_move am on aml.move_id = am.id
                                    where am.state = 'posted'
                                        AND aml.date > '%(from_date)s'
                                        AND aml.date <= '%(end_date)s'
                                        AND aml.currency_id is not null AND aml.amount_currency = 0 AND aml.currency_id = %(currency_id)s
                                    );
                ''')
                sql = sql%({
                          'from_date': from_date,
                          'end_date': end_date,
                          'ex_currency_rate': ex_currency_rate,
                          'second_currency_id': second_currency_id,
                          'second_rate': second_rate,
                        })
                
            extend_sql = ''
            if second_currency:
                #THANH: in case currency_id = second_currency_id, this sql will update again rate
                extend_sql = _('''
                    --THANH: get the same value if currency_id = 2nd currency
                    UPDATE account_move_line
                        SET second_amount = amount_currency, 
                            second_ex_rate = currency_ex_rate,
                            second_currency_id = %(second_currency_id)s
                    WHERE 
                        id in (select aml.id 
                                from account_move_line aml
                                    join account_move am on aml.move_id = am.id
                                where am.state = 'posted'
                                    AND aml.date > '%(from_date)s'
                                    AND aml.date <= '%(end_date)s'
                                    AND aml.currency_id is not null AND aml.amount_currency != 0 
                                    AND aml.currency_id = %(second_currency_id)s;
                                );
                    ''')
                extend_sql = extend_sql%({
                    'from_date': from_date,
                    'end_date': end_date,
                    'second_currency_id': second_currency_id,
                    'company_currency_id': company_currency.id,
                  })
            
            sql = sql%({
                  'from_date': from_date,
                  'end_date': end_date,
                  'currency_id': currency.id,
                  'ex_currency_rate': ex_currency_rate,
                  'currency_rate': currency_rate,
                  
                  'ex_second_rate': ex_second_rate,
                  'second_currency_id': second_currency_id,
                  'second_rate': second_rate,
                  'company_currency_id': company_currency.id,
                  })
            sql += extend_sql
        if len(sql):
            self.env.cr.execute(sql)
            #THANH: Update this rate into True
            self.env.cr.execute('''
                UPDATE res_currency_rate
                    SET update_rate = true
                WHERE name='%s' and currency_id=%s
            '''%(date, currency.id))
        
class ResCurrency(models.Model):
    _inherit = "res.currency"
    
    round_decimal_places = fields.Integer(string='Rouding Decimal Places', default=2)
    company_id = fields.Many2one("res.company", string="Company")
    
    @api.multi
    def update_account_move_line(self):
        sql = '''
            SELECT rcr.id
            FROM res_currency_rate rcr
            WHERE EXISTS (select id from account_period ap where ap.state = 'draft' 
                            and date(timezone('UTC', rcr.name::timestamp)) between ap.date_start 
                                and ap.date_stop)
            ORDER BY rcr.name desc
        '''
        self.env.cr.execute(sql)
        rate_ids = [x[0] for x in self.env.cr.fetchall()]
        for rate in self.env['res.currency.rate'].browse(rate_ids):
            rate.update_account_move_line()
            
    @api.model
    def cron_create_rate_currency(self, ids=None):
        for currency in self.search([]):
            sql ='''
                select id, name
                FROM 
                    res_currency_rate
                where currency_id = %s
                    order by  name  desc
                limit 1
            '''%(currency.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                date = datetime.strptime(line['name'], DATETIME_FORMAT)
                date = date.strftime('%Y-%m-%d')
                current_date = time.strftime(DATE_FORMAT)
                while date < current_date:
                    sql ='''
                        SELECT '%s'::date +1 as date_name
                    '''%(date)
                    self.env.cr.execute(sql)
                    for day in self.env.cr.dictfetchall():
                        date = day['date_name']
                    rate_id = self.env['res.currency.rate'].browse(line['id'])
                    rate_id.copy({'name':date,'update_rate':False})
                    
    @api.model
    def cron_update_rate_acccount_currency(self, ids=None):
        currency_rate_obj = self.env['res.currency.rate']
        sql ='''
            SELECT id, name, rate, currency_id
            FROM res_currency_rate
            WHERE update_rate != true
        '''
        self.env.cr.execute(sql)
        for rate in self.env.cr.dictfetchall():
            currency_rate = currency_rate_obj.browse(rate['id'])
            currency_rate.update_account_move_line()
        
        #THANH: update account move line where current_rate = 0.0 and currency_id exist
        sql ='''
            SELECT distinct aml.currency_id
            FROM account_move_line aml
                join account_move am on am.id=aml.move_id
            WHERE am.state='posted' 
                AND (
                        (aml.currency_ex_rate = 0.0 or aml.currency_ex_rate is null)
                        and aml.currency_id is not null
                        and aml.amount_currency != 0
                    )
                AND aml.rate_type = 'average_rate'
                AND EXISTS (select id from account_period ap where ap.state = 'draft' and aml.date between ap.date_start and ap.date_stop)
            LIMIT 5
        '''
        self.env.cr.execute(sql)
        for currency in self.env.cr.fetchall():
            sql ='''
                SELECT distinct aml.date, aml.currency_id
        
                FROM account_move_line aml
                    join account_move am on am.id=aml.move_id
                WHERE am.state='posted' 
                    AND (
                            (aml.currency_ex_rate = 0.0 or aml.currency_ex_rate is null)
                            and aml.currency_id = %s
                            and aml.amount_currency != 0
                        )
                    AND aml.rate_type = 'average_rate'
                    AND EXISTS (select id from account_period ap where ap.state = 'draft' and aml.date between ap.date_start and ap.date_stop)
                ORDER BY aml.date desc
                LIMIT 50
            '''%(currency[0])
            self.env.cr.execute(sql)
            res = self.env.cr.fetchall()
            if len(res):
                sql ='''
                    SELECT distinct date(timezone('UTC', name::timestamp)), currency_id
                    FROM res_currency_rate
                    WHERE date(timezone('UTC', name::timestamp)) between '%s' and '%s' and currency_id=%s
                '''%(res[len(res) - 1][0], res[0][0], res[0][1])
                self.env.cr.execute(sql)
                res += [x for x in self.env.cr.fetchall() if x[0] not in res]
                for line in res:
                    currency_rate_obj.update_account_move_line(line[0], line[1])
        
        if self.env.user.company_id.second_currency_id:
            #THANH: update account move line where second_rate = 0.0 and (second_currency_id exist or not)
            sql ='''
                SELECT distinct aml.date, coalesce(aml.second_currency_id,%s)
                FROM account_move_line aml
                    join account_move am on am.id=aml.move_id
                WHERE (aml.debit <> 0 or aml.credit <> 0 or aml.amount_currency <> 0) 
                    and am.state='posted' 
                    and (aml.second_ex_rate = 0.0 or aml.second_ex_rate is null or aml.second_currency_id is null)
                    and (
                         (aml.rate_type = 'average_rate')
                            or
                         (aml.rate_type = 'transaction_rate' and aml.amount_currency <> 0 and aml.second_amount = 0.0)
                        )
                    AND EXISTS (select id from account_period ap where ap.state = 'draft' and aml.date between ap.date_start and ap.date_stop)
                ORDER BY aml.date desc
                LIMIT 50
            '''%(self.env.user.company_id.second_currency_id.id)
            self.env.cr.execute(sql)
            res = self.env.cr.fetchall()
            if len(res):
                sql ='''
                    SELECT distinct date(timezone('UTC', name::timestamp)), currency_id
                    FROM res_currency_rate
                    WHERE date(timezone('UTC', name::timestamp)) between '%s' and '%s' and currency_id=%s
                '''%(res[len(res) - 1][0], res[0][0], res[0][1])
                self.env.cr.execute(sql)
                res += [x for x in self.env.cr.fetchall() if x[0] not in res]
                for line in res:
                    currency_rate_obj.update_account_move_line(line[0], line[1])
                
                