# -*- encoding: utf-8 -*-
import  time
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import orm
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'
    
    tax_ids = fields.Many2many('account.tax', 'account_asset_category_tax', 'asset_category_id', 'tax_id',
        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
    recognition_expense_account_id= fields.Many2one('account.account', string="Recognition Expense Account")
    expense_account_id= fields.Many2one('account.account', string="Depreciation Expense Account", 
                                        domain=[('type','=','other'), ('deprecated', '=', False)])#New field
    
    _defaults = {
        'prorata':True,
        'open_asset': True,
    }

class AccountAssetAsset(models.Model):
    _inherit = 'account.asset.asset'
    _order = "id desc"
    
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=False)#, states={'draft':[('readonly',False)]})
    department_id = fields.Many2one('hr.department', string='Department', readonly=False)
    employee_id = fields.Many2one('hr.employee', string='Responsible', domain="[('department_id','=',department_id)]", readonly=False)
    
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account', readonly=True, states={'draft':[('readonly',False)]})
    account_income_recognition_id = fields.Many2one('account.account', string='Depr. Expense Account', 
                                                    domain=[('type','=','other'), ('deprecated', '=', False)], readonly=False)#New field
    
    component_lines = fields.One2many('account.asset.component', 'asset_id', string='Components')
    sale_invoice_id = fields.Many2one('account.invoice', string='Sale Invoice', readonly=False)
    #THANH: set this field to be stored due to loading huge asset records
    
    @api.one
    @api.depends('value', 'salvage_value', 'depreciation_line_ids','depreciation_line_ids.move_id','depreciation_line_ids.move_id.state')
    def _amount_residual(self):
        total_amount = 0.0
        for line in self.depreciation_line_ids:
            if line.move_check:
                total_amount += line.amount
        self.value_residual = self.value - total_amount - self.salvage_value
        
    value_residual = fields.Float(compute='_amount_residual', method=True, digits=0, string='Residual Value', store=True)
    
    #THANH: Histories of changing value and duration of an asset
    history_ids = fields.One2many('account.asset.history', 'asset_id', string='Histories', readonly=True)
    asset_upgrades_ids = fields.Many2many('account.invoice','asset_invoice_rel','asset_id', 'invoice_id', string='Asset Upgrades')
    maintenance_invoice_ids = fields.Many2many('account.invoice','asset_maintenance_invoice_rel','asset_id', 'invoice_id', string='Maintenance Invoices')
    
    dispose_move_id = fields.Many2one('account.move', string="Dispose Entry")
    
    @api.multi
    def create_dispose_move(self):
        #THANH: create reduce asset value 242
        asset = self
        depreciation_date =  fields.Date.context_today(self)
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        debit_amount2 = current_currency.compute(asset.value_residual, company_currency)
        credit_amount = current_currency.compute(asset.value, company_currency)
        debit_amount1 = credit_amount - debit_amount2
        asset_name = asset.name 
        reference = asset.code
        journal_id = asset.category_id.journal_id.id
        partner_id = asset.partner_id.id
        categ_type = asset.category_id.type
        
        sign = (categ_type == 'purchase' or categ_type == 'sale' and 1) or -1
        debit_account1 = asset.category_id.account_depreciation_id.id
        debit_account2 = asset.category_id.recognition_expense_account_id.id  
        credit_account = asset.category_id.account_asset_id.id
        
        account_analytic_id = asset.account_analytic_id or asset.category_id.account_analytic_id
        
        move_line_1 = {
            'name': asset_name,
            'account_id': debit_account1,
            'debit':  debit_amount1,
            'credit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and  (asset.value - asset.value_residual) or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'sale' else False,
            'date': depreciation_date,
        }
        move_line_2 = {
            'name': asset_name,
            'account_id': debit_account2,
            'debit': debit_amount2, 
            'credit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and asset.value_residual or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'purchase' else False,
            'date': depreciation_date,
        }
        move_line_3 = {
            'name': asset_name,
            'account_id': credit_account,
            'credit': credit_amount,
            'debit': 0.0,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'currency_id': company_currency != current_currency and current_currency.id or False,
            'amount_currency': company_currency != current_currency and (- 1) * asset.value or 0.0,
            'analytic_account_id': account_analytic_id.id if categ_type == 'purchase' else False,
            'date': depreciation_date,
        }
        move_vals = {
            'ref': reference,
            'date': depreciation_date or False,
            'journal_id': asset.category_id.journal_id.id,
            'line_ids': [(0, 0, move_line_2), (0, 0, move_line_1),(0, 0, move_line_3)],
            'asset_id': asset.id,
            }
        move = self.env['account.move'].create(move_vals)
        #THANH: auto post entries
        move.post()
        return move.id
    
    @api.multi
    def set_to_close(self):
        move_ids = []
        for asset in self:
            #THANH: Check customer invoice
#             if not asset.sale_invoice_id:
#                 raise UserError(_("You must create Sale Invoice firstly."))
#             if asset.sale_invoice_id and asset.sale_invoice_id.state not in ['open','paid']:
#                 raise UserError(_("You must validate the Sale Invoice number '%s' firstly.")%(asset.sale_invoice_id.reference))
            
            asset.dispose_move_id = self.create_dispose_move()
            
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: not x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(unposted_depreciation_line_ids) + 1
                today = datetime.today().strftime(DF)
                vals = {
                    'value': asset.value,#THANH: add original value
                    'amount': asset.value_residual,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': asset.value - asset.salvage_value,  # the asset is completely depreciated
                    'depreciation_date': today,
                }
                commands.append((0, False, vals))
                asset.with_context(pass_method_number=True).write({'depreciation_line_ids': commands, 'method_end': today, 'method_number': sequence})
                tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_end'])
                changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
                if changes:
                    asset.message_post(subject=_('Asset sold or disposed. Accounting entry awaiting for validation.'), tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move(post_move=False)
            
            #THANH: Show dispose moves
            asset.write({'state': 'close'})
            return asset.open_dispose_entries()
    
    @api.onchange('department_id')
    def onchange_department_id(self):
        self.employee_id = False
        
    def onchange_category_id_values(self, category_id):
        if category_id:
            category = self.env['account.asset.category'].browse(category_id)
            return {
                'value': {
                    'method': category.method,
                    'method_number': category.method_number,
                    'method_time': category.method_time,
                    'method_period': category.method_period,
                    'method_progress_factor': category.method_progress_factor,
                    'method_end': category.method_end,
                    'prorata': category.prorata,
                    #THANH: Add this field
                    'account_income_recognition_id': category.expense_account_id and category.expense_account_id.id or False
                }
            }
    
    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date):
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if self.prorata and self.category_id.type == 'purchase':
                    #THANH: This amount will be wrrong if we change duration again (VD: change from 72 to 60, the amount is incorrect)
#                     amount = amount_to_depr / self.method_number
                    if sequence == 1:
#                         days = (self.company_id.compute_fiscalyear_dates(depreciation_date)['date_to'] - depreciation_date).days + 1
#                         amount = (amount_to_depr / self.method_number) / total_days * days
                        #THANH" Tinh so tien khau hao lan dau tien (Dua tren so ngay trong thang
                        days_of_month = calendar.monthrange(depreciation_date.year,depreciation_date.month)[1]
                        days = days_of_month - depreciation_date.day + 1
                        amount = (amount_to_depr / self.method_number) / days_of_month * days
            elif self.method == 'degressive':
                #THANH: This amount will be wrrong if we change duration again (VD: change from 72 to 60, the amount is incorrect)
#                 amount = residual_amount * self.method_progress_factor
                if self.prorata:
                    if sequence == 1:
#                         days = (self.company_id.compute_fiscalyear_dates(depreciation_date)['date_to'] - depreciation_date).days + 1
#                         amount = (residual_amount * self.method_progress_factor) / total_days * days
                        #THANH" Tinh so tien khau hao lan dau tien (Dua tren so ngay trong thang
                        days_of_month = calendar.monthrange(depreciation_date.year,depreciation_date.month)[1]
                        days = days_of_month - depreciation_date.day + 1
                        amount = (residual_amount * self.method_progress_factor) / days_of_month * days
        return amount
    
    def _compute_board_undone_dotation_nb(self, depreciation_date, total_days):
        undone_dotation_number = self.method_number
        if self.method_time == 'end':
            end_date = datetime.strptime(self.method_end, DF).date()
            undone_dotation_number = 0
            while depreciation_date <= end_date:
                depreciation_date = date(depreciation_date.year, depreciation_date.month, depreciation_date.day) + relativedelta(months=+self.method_period)
#                 undone_dotation_number += 1
        #THANH: Remove plus 1 because when using duration 60, it will compute amount = value / 61
#         if self.prorata and self.category_id.type == 'purchase':
#             undone_dotation_number += 1
        return undone_dotation_number
    
    @api.multi
    def _get_last_depreciation_date(self):
        """
        @param id: ids of a account.asset.asset objects
        @return: Returns a dictionary of the effective dates of the last depreciation entry made for given asset ids. If there isn't any, return the purchase date of this asset
        """
        #THANH: prevent to get dispose_move_id
        where = ''
        if self.dispose_move_id:
            where += ' and m.id != %s '%(self.dispose_move_id.id)
        self.env.cr.execute("""
            SELECT a.id as id, COALESCE(MAX(m.date),a.date) AS date
            FROM account_asset_asset a
            LEFT JOIN account_move m ON (m.asset_id = a.id)
            WHERE a.id IN %s """+
            where +
            "GROUP BY a.id, a.date ", (tuple(self.ids),))
        result = dict(self.env.cr.fetchall())
        if not result:
            for id in self.ids:
                result.update({self.id: self.date})
        return result
    
    @api.multi
    def compute_depreciation_board(self):
        self.ensure_one()
        
        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(lambda x: not x.move_check)

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False) for line_id in unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual
            if self.prorata:
                depreciation_date = datetime.strptime(self._get_last_depreciation_date()[self.id], DF).date()
            else:
                # depreciation_date = 1st of January of purchase year
                asset_date = datetime.strptime(self.date[:4] + '-01-01', DF).date()
                # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if posted_depreciation_line_ids and posted_depreciation_line_ids[-1].depreciation_date:
                    last_depreciation_date = datetime.strptime(posted_depreciation_line_ids[-1].depreciation_date, DF).date()
                    depreciation_date = last_depreciation_date + relativedelta(months=+self.method_period)
                else:
                    depreciation_date = asset_date
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            undone_dotation_number = self._compute_board_undone_dotation_nb(depreciation_date, total_days)

            for x in range(len(posted_depreciation_line_ids), undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(sequence, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date)
                amount = self.currency_id.round(amount)
                residual_amount -= amount
                
                #THANH: sua lai de lan khau hao dau tien cuoi thang
                if sequence == 1:
                    depreciation_date = date(year, month, 1) + relativedelta(months=+self.method_period, days=-1)#Get last day of month: 30/09/2016
                else:
                    # Considering Depr. Period as months
                    depreciation_date = depreciation_date + relativedelta(days=+1)#Get first day of next month: 01/10/2016
                    depreciation_date = depreciation_date + relativedelta(months=+self.method_period, days=-1)
                
                #THANH: remove line 0
                if amount > 0:
                    vals = {
                        'value': self.value,
                        'amount': amount,
                        'asset_id': self.id,
                        'sequence': sequence,
                        'name': (self.code or '') + '/' + str(sequence),
                        'remaining_value': residual_amount,
                        'depreciated_value': self.value - (self.salvage_value + residual_amount),
                        'depreciation_date': depreciation_date.strftime(DF),
                    }
                    commands.append((0, False, vals))
#                 depreciation_date = date(year, month, day) + relativedelta(months=+self.method_period)
#                 day = depreciation_date.day
#                 month = depreciation_date.month
#                 year = depreciation_date.year
                    
        self.write({'depreciation_line_ids': commands})
        return True
    
    def unlink(self, cr, uid, ids, context=None):
        for asset in self.browse(cr, uid, ids):
            if asset.state != 'draft':
                raise UserError(_("You just can delete this asset in State 'Draft'"))
        return super(AccountAssetAsset, self).unlink(cr, uid, ids, context=context)
    
    @api.multi
    def btt_asset_upgrades(self):
        for invoice in self.asset_upgrades_ids:
            if invoice.state not in ['paid','open']:
                continue
            his = self.env['account.asset.history'].search([('invoice_id','=',invoice.id)])
            if not his:
                #THANH: convert invoice amount_untaxed to asset currency if difference
                value = self.value + invoice.amount_untaxed
                if self.currency_id != invoice.currency_id:
                    ctx = {'date': invoice.date_invoice}
                    value = self.value + invoice.currency_id.with_context(ctx).compute(invoice.amount_untaxed, self.currency_id)
                    
                self.value = value
                asset = self
                asset_vals = {
                    'invoice': invoice.name,
                }
                asset.write(asset_vals)
                asset.compute_depreciation_board()
                
                #THANH: Log changed values
                history_vals = {
                    'invoice_id':invoice.id,
                    'asset_id': asset.id,
                    'name': _("Nâng cấp tài sản dựa theo hóa đơn số %s")%(invoice.reference),
                    'value': value,
                    'method_time': asset.method_time,
                    'method_number': asset.method_number,
                    'method_period': asset.method_period,
                    'method_end': asset.method_end,
                    'user_id': self.env.user.id,
                    'date': time.strftime('%Y-%m-%d'),
                }
                self.env['account.asset.history'].create(history_vals)
    
    @api.one
    @api.constrains('method_number')
    def _check_modify_method_number(self):
        if self._context.get('pass_method_number', False):
            pass
        else:
            #THANH: Neu co thay doi field asset_upgrades_ids thi goi ham upgrade
            for asset in self:
                posted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check)
                if len(posted_depreciation_line_ids):
                    raise UserError(_("You have to cancel all depreciation entries and set asset to draft first."))
                asset.compute_depreciation_board()
        
    @api.one
    @api.constrains('asset_upgrades_ids')
    def _check_asset_upgrades(self):
        #THANH: Neu co thay doi field asset_upgrades_ids thi goi ham upgrade
        for asset in self:
            upgrade_invoice_ids = [x.id for x in asset.asset_upgrades_ids]
            histories = self.env['account.asset.history'].search([('asset_id','=',asset.id), ('invoice_id','!=',False)])
            for his in histories:
                if his.invoice_id.id not in upgrade_invoice_ids:
                    raise UserError(_("Invoice (%s) has been increase this Asset Value. You can not delete this invoice.")%(his.invoice_id.reference))
        self.btt_asset_upgrades()

    @api.one
    @api.constrains('asset_upgrades_ids','maintenance_invoice_ids', 'invoice_id','sale_invoice_id')
    def _check_related_invoices(self):
        for asset in self:
            #THANH: rm all relation firstly
            sql = '''
                DELETE FROM account_invoice_asset_rel WHERE asset_id = %s;
            '''%(asset.id)
            self._cr.execute(sql)
            
            #THANH: add again
            sql = ''
            if asset.invoice_id:
                sql += '''
                INSERT INTO account_invoice_asset_rel(asset_id, invoice_id)
                VALUES (%s,%s);
                
                '''%(asset.id, asset.invoice_id.id)
            if asset.sale_invoice_id:
                sql += '''
                INSERT INTO account_invoice_asset_rel(asset_id, invoice_id)
                VALUES (%s,%s);
                '''%(asset.id, asset.sale_invoice_id.id)
            for invoice in asset.asset_upgrades_ids:
                sql += '''
                INSERT INTO account_invoice_asset_rel(asset_id, invoice_id)
                VALUES (%s,%s);
                '''%(asset.id, invoice.id)
            for invoice in asset.maintenance_invoice_ids:
                sql += '''
                INSERT INTO account_invoice_asset_rel(asset_id, invoice_id)
                VALUES (%s,%s);
                '''%(asset.id, invoice.id)
            if len(sql):
                self._cr.execute(sql)
                
    @api.multi
    def write(self, vals):
        #THANH: No need to compute asset again
        return super(models.Model, self).write(vals)
    
    @api.multi
    def validate(self):
        #THANH: check field code exist
        if not self.code:
            raise UserError(_('Asset Code is empty. Please set it firstly.'))
        #THANH: check field code exist
        super(AccountAssetAsset, self).validate()
    
    @api.multi
    @api.depends('account_move_ids', 'invoice_id', 'sale_invoice_id', 'asset_upgrades_ids', 'maintenance_invoice_ids')
    def _entry_count(self):
        for asset in self:
            asset.entry_count = self.env['account.move'].search_count([('asset_id', '=', asset.id)])
            
            #THANH: also count other invoices
            if self.invoice_id and self.invoice_id.move_id:
                asset.entry_count += 1
            if self.sale_invoice_id and self.sale_invoice_id.move_id:
                asset.entry_count += 1
            if self.asset_upgrades_ids:
                for inv in self.asset_upgrades_ids:
                    if inv.move_id:
                        asset.entry_count += 1
            if self.maintenance_invoice_ids:
                for inv in self.maintenance_invoice_ids:
                    if inv.move_id:
                        asset.entry_count += 1
                        
    @api.multi
    def open_entries(self):
        #THANH: filter all entry items, not journal entries
        self.env.cr.execute('''
        select aml.id
        from account_move_line aml
            join account_move am on aml.move_id=am.id
        where am.asset_id = %s
        '''%(self.id))
        line_ids = [x[0] for x in self.env.cr.fetchall()]
        if self.invoice_id and self.invoice_id.move_id:
            for line in self.invoice_id.move_id.line_ids:
                line_ids.append(line.id)
        if self.sale_invoice_id and self.sale_invoice_id.move_id:
            for line in self.sale_invoice_id.move_id.line_ids:
                line_ids.append(line.id)
        if self.asset_upgrades_ids:
            for inv in self.asset_upgrades_ids:
                if inv.move_id:
                    for line in inv.move_id.line_ids:
                        line_ids.append(line.id)
        if self.maintenance_invoice_ids:
            for inv in self.maintenance_invoice_ids:
                if inv.move_id:
                    for line in inv.move_id.line_ids:
                        line_ids.append(line.id)
                
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', line_ids)],
        }
    
    @api.multi
    def open_dispose_entries(self):
        line_ids = []
        if self.sale_invoice_id and self.sale_invoice_id.move_id:
            for line in self.sale_invoice_id.move_id.line_ids:
                line_ids.append(line.id)
        if self.dispose_move_id:
            for line in self.dispose_move_id.line_ids:
                line_ids.append(line.id)
                
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', line_ids)],
        }
class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'
    _description = 'Asset depreciation line'

    warehouse_id = fields.Many2one(related='asset_id.warehouse_id', string='Warehouse', 
                                   readonly=True, store=True)
    company_id = fields.Many2one(related='asset_id.company_id', string='Company', 
                                 readonly=True, store=True)
    value = fields.Float(string='Gross Value', required=False, digits=0)
    
    @api.multi
    def cancel(self):
        for asset in self:
            if asset.move_id:
                asset.move_id.button_cancel()
                asset.move_id.unlink()
            asset.write({'move_check': False})
            
    @api.multi
    def create_move(self, post_move=True):
        created_moves = self.env['account.move']
        for line in self:
            depreciation_date = self.env.context.get('depreciation_date') or line.depreciation_date or fields.Date.context_today(self)
            company_currency = line.asset_id.company_id.currency_id
            current_currency = line.asset_id.currency_id
            amount = current_currency.compute(line.amount, company_currency)
#             sign = (line.asset_id.category_id.journal_id.type == 'purchase' or line.asset_id.category_id.journal_id.type == 'sale' and 1) or -1
            asset_name = line.asset_id.name + ' (%s/%s)' % (line.sequence, line.asset_id.method_number)
            reference = line.asset_id.code
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            categ_type = line.asset_id.category_id.type
            journal_code = line.asset_id.category_id.journal_id.code
            if journal_code == 'CPTT':
                asset_name = u'Phân bổ ' + asset_name
            else:
                asset_name = u'Khấu hao ' + asset_name
            
            #THANH: get sign from categ type
            sign = (categ_type == 'purchase' or categ_type == 'sale' and 1) or -1
            #THANH: if asset is purchase, so Debit is account_income_recognition_id (expenses account) and Credit is account_depreciation_id
            #THANH: else is sale, Debit is account_depreciation_id and Credit is account_income_recognition_id (expenses account)
            if categ_type == 'purchase':
                debit_account = line.asset_id.account_income_recognition_id.id
                credit_account = line.asset_id.category_id.account_depreciation_id.id
            else:
                debit_account = line.asset_id.category_id.account_depreciation_id.id
                credit_account = line.asset_id.account_income_recognition_id.id
            account_analytic_id = line.asset_id.account_analytic_id or line.asset_id.category_id.account_analytic_id
            
            move_line_1 = {
                'name': asset_name,
                'account_id': credit_account,
                'debit': 0.0,
                'credit': amount,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                'analytic_account_id': account_analytic_id.id if categ_type == 'sale' else False,
                'date': depreciation_date,
            }
            move_line_2 = {
                'name': asset_name,
                'account_id': debit_account,
                'credit': 0.0,
                'debit': amount,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and current_currency.id or False,
                'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                'analytic_account_id': account_analytic_id.id if categ_type == 'purchase' else False,
                'date': depreciation_date,
            }
            move_vals = {
                'ref': reference,
                'date': depreciation_date or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                'asset_id': line.asset_id.id,
                }
            move = self.env['account.move'].create(move_vals)
            line.write({'move_id': move.id, 'move_check': True})
            created_moves |= move
            
        if post_move and created_moves:
            created_moves.filtered(lambda r: r.asset_id and r.asset_id.category_id and r.asset_id.category_id.open_asset).post()
        return [x.id for x in created_moves]
    
class AccountAssetComponent(models.Model):
    _name = 'account.asset.component'
    
    asset_id = fields.Many2one('account.asset.asset', string='Asset', ondelete='cascade', index=True)
    name = fields.Char('Component Name', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    description = fields.Text('Description')
    currency_id = fields.Many2one('res.currency', related='asset_id.currency_id', store=True)
    value = fields.Monetary(string='Value', required=False, currency_field='currency_id')
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        self.department_id = self.employee_id.department_id and self.employee_id.department_id.id or False

class account_asset_history(models.Model):
    _name = 'account.asset.history'
    _description = 'Asset history'
    _order = 'date desc, id desc'
    
    name = fields.Char(string='History name')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    asset_id = fields.Many2one('account.asset.asset', string='Asset', required=True, ondelete='cascade')
    
    method_time = fields.Selection([('number', 'Number of Depreciations'), ('end', 'Ending Date')], string='Time Method', required=True)
    method_number = fields.Integer(string='Number of Depreciations', help="The number of depreciations needed to depreciate your asset")
    method_period = fields.Integer(string='Number of Months in a Period', help="The amount of time between two depreciations, in months")
    method_end = fields.Date(string='Ending Date')
    invoice_id = fields.Many2one('account.invoice', string='Account invoice', required=False, ondelete='cascade')
    value = fields.Float(string='Gross Value', required=True, digits=0)
    
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    #THANH: Show related Asset on Invoices
    asset_ids = fields.Many2many('account.asset.asset', 'account_invoice_asset_rel', 'invoice_id', 'asset_id', string='Assets', readonly=True)
    
    @api.model
    def default_get(self, fields): 
        rec = super(AccountInvoice, self).default_get(fields)
        asset_id = self._context.get('asset_id')
        if asset_id:
            asset = self.env['account.asset.asset'].browse(asset_id)
            rec['journal_id'] = asset.category_id.journal_id.id
            rec['currency_id'] = asset.currency_id.id
            
            if self._context.get('sell_asset'):
                if not asset.category_id.account_income_recognition_id:
                    raise UserError(_("You must define account Recognition Income Account in Asset Type '%s'.") % (_(asset.category_id.name)))
                
                rec['invoice_line_ids'] = [(0, 0, {'name': _("Thanh lý ") + _(asset.category_id.name) + _(' [') + _(asset.code) + _('] ') + _(asset.name),
                                                   'account_id': asset.category_id.account_income_recognition_id.id,
                                                   'price_unit': asset.value_residual,
                                                   'quantity': 1.0,
                                                   'invoice_line_tax_ids': asset.category_id.tax_ids and [(6, 0, [x.id for x in asset.category_id.tax_ids])] or False})]
        return rec
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = args or []
        context = self._context or {}
        #THANH: help to filter exact invoices
        if context.get('no_search_maintenance_invoice_ids') and len(context.get('no_search_maintenance_invoice_ids',[])):
            maintenance_invoice_ids = context['no_search_maintenance_invoice_ids'][0][2]
            args.append(('id','not in', maintenance_invoice_ids))
        if context.get('no_search_asset_upgrades_ids') and len(context.get('no_search_asset_upgrades_ids',[])):
            asset_upgrades_ids = context['no_search_asset_upgrades_ids'][0][2]
            args.append(('id','not in', asset_upgrades_ids))
        
        #THANH: filter invoices which have the same journal_id with asset
        asset_id = context.get('asset_id')
        if asset_id and context.get('search_invoice_by_asset_journal',False):
            asset = self.env['account.asset.asset'].browse(asset_id)
            args.append(('journal_id','=', asset.category_id.journal_id.id))
        return super(AccountInvoice, self).search(args, offset, limit, order, count=count)
    
    @api.multi
    def action_cancel(self):
        for inv in self:
            assets = self.env['account.asset.asset'].search([('invoice_id','=',inv.id)])
            for asset in assets:
                posted_depreciation_line_ids = asset.depreciation_line_ids.filtered(lambda x: x.move_check)
                if len(posted_depreciation_line_ids):
                    raise UserError(_("Asset %s already running and depreciated %s months. You are not able cancel this invoice.\nYou have to cancel all depreciation entries and set asset to draft first.") % (asset.code,len(posted_depreciation_line_ids)))
        return super(AccountInvoice,self).action_cancel()
    
    @api.multi
    def action_view_assets(self):
        action = self.env.ref('account_asset.action_account_asset_asset_form')
        result = action.read()[0]
        result['context'] = {}
        asset_ids = [x.id for x in self.asset_ids]
        if len(asset_ids):
            result['domain'] = "[('id','in',[" + ','.join(map(str, asset_ids)) + "])]"
            return result
        return True
    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.onchange('asset_category_id')
    def onchange_asset_category_id(self):
        if not self.asset_category_id:
            self.account_id = self.get_invoice_line_account(self.invoice_id.type, self.product_id, self.invoice_id.fiscal_position_id, self.invoice_id.company_id)
        if self.invoice_id.type == 'out_invoice' and self.asset_category_id:
            self.account_id = self.asset_category_id.account_asset_id.id
        elif self.invoice_id.type == 'in_invoice' and self.asset_category_id:
#             self.account_id = self.asset_category_id.account_depreciation_id.id
            #THANH: get asset account instead of account_depreciation_id
            self.account_id = self.asset_category_id.account_asset_id.id
        
    @api.onchange('account_id')
    def _onchange_account_id(self):
        super(AccountInvoiceLine, self)._onchange_account_id()
        #THANH: auto get asset taxes
        if self.asset_category_id.tax_ids:
            self.invoice_line_tax_ids = self.asset_category_id.tax_ids#[x.id for x in self.asset_category_id.tax_ids]
    
    @api.one
    def asset_create(self):
        if self.asset_category_id and self.asset_category_id.method_number > 1:
            vals = {
                'name': self.name,
                'code': self.invoice_id.number or False,
                'category_id': self.asset_category_id.id,
                'value': self.price_subtotal,
                'partner_id': self.invoice_id.partner_id.id,
                'company_id': self.invoice_id.company_id.id,
                'currency_id': self.invoice_id.currency_id.id,
                'date': self.asset_start_date or self.invoice_id.date_invoice,
                'invoice_id': self.invoice_id.id,
                
                #THANH: add more fields
                'warehouse_id': hasattr(self.invoice_id, 'warehouse_id') and self.invoice_id.warehouse_id.id or False,
            }
            if hasattr(self.invoice_id, 'warehouse_id'):
                if self.invoice_id.warehouse_id and self.invoice_id.warehouse_id.account_analytic_id:
                    vals.update({'account_analytic_id': self.invoice_id.warehouse_id.account_analytic_id.id})
                
            changed_vals = self.env['account.asset.asset'].onchange_category_id_values(vals['category_id'])
            vals.update(changed_vals['value'])
            asset = self.env['account.asset.asset'].create(vals)
            
            #THANH: no need auto confirm asset, accountant will check and change depreciation duration
#             if self.asset_category_id.open_asset:
#                 asset.validate()
        return True
    
class Employee(models.Model):
    _inherit = 'hr.employee'
    
    asset_ids = fields.One2many('account.asset.asset', 'employee_id', string='Assets', readonly=True)
    asset_component_ids = fields.One2many('account.asset.component', 'employee_id', string='Components', readonly=True)
