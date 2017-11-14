# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import modules


class AccountRegularization(models.Model):
    _inherit = 'account.regularization'
    _description = 'Account Regularization'
    
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
                if not journal_ids:
                    raise UserError(_("Journals are missing in model '%s'.") % (i.name,))

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
    
    