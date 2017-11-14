# -*- coding: utf-8 -*-
##############################################################################
#
#    Account reversal module for OpenERP
#    Copyright (C) 2011 Akretion (http://www.akretion.com). All Rights Reserved
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#    with the kind advice of Nicolas Bessi from Camptocamp
#    Copyright (C) 2012-2013 Camptocamp SA (http://www.camptocamp.com)
#    @author Guewen Baconnier <guewen.baconnier@camptocamp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import fields, models, api, _
DATE_FORMAT = "%Y-%m-%d"
from datetime import datetime
import time
from openerp.exceptions import RedirectWarning, UserError

class ResCompany(models.Model):
    _inherit = "res.company"

    reverse_journal_id = fields.Many2one('account.journal', string='Reverse Journal')


class AccountMove(models.Model):
    _inherit = "account.move"

    to_be_reversed = fields.Boolean(
        'To Be Reversed',
        help='Check this box if your entry has to be'
        'reversed at the end of period.')
    reversal_id = fields.Many2one(
        'account.move',
        'Reversal Entry',
        ondelete='set null',
        readonly=True)
    
    date_reversed = fields.Date(string = "Date Reversed")
    reversal_from_ids = fields.One2many('account.move','reversal_id',string="Reversal From",ondelete='set null',readonly=True)
    
    @api.model
    def cron_reversed_for_account_move(self,ids=None):
        company_id =self.env['res.company'].browse(1)
        reversal_journal_id = company_id.reverse_journal_id
        sql ='''
            SELECT id
            FROM account_move
            WHERE to_be_reversed = true
                and reversal_id is null
                and date_reversed  <= '%s'
        '''%(time.strftime(DATE_FORMAT))
        self.env.cr.execute(sql)
        for line in self.env.cr.dictfetchall():
            move = self.env['account.move'].browse(line['id'])
            move._move_reversal(time.strftime(DATE_FORMAT),
                         reversal_journal_id=reversal_journal_id.id,
                         move_prefix=False, move_line_prefix=False)
        
        
    
    @api.multi
    def button_cancel(self):
        for move in self:
            if move.reversal_id:
                #move.reversal_id.button_cancel()
                #move.reversal_id.unlink()
                sql ='''
                    DELETE from account_move_line where move_id = %s;
                    DELETE from account_move where id = %s;
                '''%(move.reversal_id.id,move.reversal_id.id)
                self.env.cr.execute(sql)
                
        return super(AccountMove, self).button_cancel()
    

    @api.multi
    def _move_reversal(self, reversal_date,
                       reversal_journal_id=False,
                       move_prefix=False, move_line_prefix=False):
        """
        Create the reversal of a move

        :param move: browse instance of the move to reverse
        :param reversal_date: when the reversal must be input
        :param reversal_period_id: facultative period to write on the move
                                   (use the period of the date if empty
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names

        :return: Returns the id of the created reversal move
        """
        self.ensure_one()

#         if reversal_period_id:
#             reversal_period = period_obj.browse([reversal_period_id])[0]
#         else:
#             reversal_period = period_obj.with_context(
#                 company_id=self.company_id.id,
#                 account_period_prefer_normal=True).find(reversal_date)[0]
        if not reversal_journal_id:
            reversal_journal_id = self.journal_id.id

        if self.env['account.journal'].browse([
                reversal_journal_id]).company_id != self.company_id:
            raise Warning(_('Wrong company Journal is %s but we have %s') % (
                reversal_journal_id.company_id.name, self.company_id.name))
#         if reversal_period.company_id != self.company_id:
#             raise Warning(_('Wrong company Period is %s but we have %s') % (
#                 reversal_journal_id.company_id.name, self.company_id.name))

        reversal_ref = ''.join([x for x in [move_prefix, self.ref] if x])
        reversal_move = self.copy(default={
            'company_id': self.company_id.id,
            'date': reversal_date,
            'ref': reversal_ref,
            'journal_id': reversal_journal_id,
            'to_be_reversed': False,
        })

        self.with_context(novalidate=True).write({
            'reversal_id': reversal_move.id,
            'to_be_reversed': False,
        })
        acc_debit_id = False
        acc_credit_id = False
        for reversal_move_line in reversal_move.line_ids:
            if reversal_move_line.debit:
                acc_debit_id = reversal_move_line.account_id.id
            else:
                acc_credit_id = reversal_move_line.account_id.id
        
        for reversal_move_line in reversal_move.line_ids:
            reversal_ml_name = ' '.join(
                [x for x in [move_line_prefix, reversal_move_line.name] if x]
            )
            if reversal_move_line.debit:
                if reversal_move_line.currency_id:
                    val ={
                            'account_id': acc_credit_id,
                            'amount_currency': reversal_move_line.amount_currency ,
                            'name': reversal_ml_name
                          }
                else:
                    val ={
                            'account_id': acc_credit_id,
                            'name': reversal_ml_name
                          }
                reversal_move_line.write(val)
            else:
                if reversal_move_line.currency_id:
                    val ={
                            'account_id': acc_debit_id,
                            'amount_currency': reversal_move_line.amount_currency,
                            'name': reversal_ml_name
                          }
                else:
                    val ={
                            'account_id': acc_debit_id,
                            'name': reversal_ml_name
                          }
                reversal_move_line.write(val)

        reversal_move.post()
        return reversal_move.id

    @api.multi
    def create_reversals(self, reversal_date, 
                         reversal_journal_id=False,
                         move_prefix=False, move_line_prefix=False):
        """
        Create the reversal of one or multiple moves
 
        :param reversal_date: when the reversal must be input
        :param reversal_period_id: facultative period to write on the move
                                   (use the period of the date if empty
        :param reversal_journal_id: facultative journal on which create
                                    the move
        :param move_prefix: prefix for the move's name
        :param move_line_prefix: prefix for the move line's names
 
        :return: Returns a list of ids of the created reversal moves
        """
        return [
            move._move_reversal(
                reversal_date,
                reversal_journal_id=reversal_journal_id,
                move_prefix=move_prefix,
                move_line_prefix=move_line_prefix
            )
            for move in self
            if not move.reversal_id
        ]
