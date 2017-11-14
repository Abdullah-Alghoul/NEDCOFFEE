# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.tools import float_is_zero
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp

from datetime import datetime
import copy
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}

class AccountTax(models.Model):
    _inherit = 'account.tax'
        
    @api.v8
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):

        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        
        #KIET: use field round_decimal_places instead of orginal field decimal_places from currency
        prec = currency.round_decimal_places
    
        # In some cases, it is necessary to force/prevent the rounding of the tax and the total
        # amounts. For example, in SO/PO line, we don't want to round the price unit at the
        # precision of the currency.
        # The context key 'round' allows to force the standard behavior.
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])
    
        if not round_tax:
            prec += 5
    
        base_values = self.env.context.get('base_values')
        if not base_values:
            total_excluded = total_included = base = round(price_unit * quantity, prec)
        else:
            total_excluded, total_included, base = base_values
    
        # Sorting key is mandatory in this case. When no key is provided, sorted() will perform a
        # search. However, the search method is overridden in account.tax in order to add a domain
        # depending on the context. This domain might filter out some taxes from self, e.g. in the
        # case of group taxes.
        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                children = tax.children_tax_ids.with_context(base_values=(total_excluded, total_included, base))
                ret = children.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base'] if tax.include_base_amount else base
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue
    
            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)
    
            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount
    
            # Keep base amount used for the current tax
            tax_base = base
    
            if tax.include_base_amount:
                base += tax_amount
    
            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'base': tax_base,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
            })
    
        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': currency.round(total_excluded) if round_total else total_excluded,
            'total_included': currency.round(total_included) if round_total else total_included,
            'base': base,
        }
        
class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.one
    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'currency_id', 'company_id', 'date_invoice', 'currency_rate')
    def _compute_amount_company(self):
        amount_untaxed = sum(line.price_subtotal for line in self.invoice_line_ids)
        amount_tax = sum(line.amount for line in self.tax_line_ids)
        amount_total = self.amount_untaxed + self.amount_tax
        
        #THANH: Default amount in company
        date = self.date_invoice
        self.amount_untaxed_company = amount_untaxed
        self.amount_tax_company = amount_tax
        self.amount_total_company = amount_total
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            #THANH: convert these field into company amount
            self.amount_untaxed_company = self.currency_id.with_context(date=date).compute(self.amount_untaxed, self.company_id.currency_id)
            self.amount_tax_company = self.currency_id.with_context(date=date).compute(self.amount_tax, self.company_id.currency_id)
            self.amount_total_company = self.currency_id.with_context(date=date).compute(self.amount_total, self.company_id.currency_id)
        
    def _get_currency_rate(self):
        for invoice in self:
            date = invoice.date_invoice
            
            context = dict(self._context or {})
            context.update({'date':date})
            rate = invoice.currency_id._get_date_rate()
            invoice.currency_rate = rate
                    
#                 if invoice.picking_ids:
#                     for invoice_line in invoice.invoice_line_ids:
#                         for pick in invoice.picking_ids:
#                             for line in pick.move_lines:
#                                 if line.product_id == invoice_line.product_id:
#                                     sql ='''
#                                         UPDATE stock_move
#                                         SET exchange_rate= %s,price_unit = %s
#                                         WHERE id = %s
#                                         and product_id = %s
#                                     '''%(invoice.currency_rate, invoice_line.price_unit * invoice.currency_rate, line.id, invoice_line.product_id.id)
#                                     self._cr.execute(sql)
    
    @api.depends('currency_id', 'company_id')
    def _check_diff_currency(self):
        for invoice in self:
            self.diff_currency = invoice.currency_id != invoice.company_currency_id
    
    #THANH: new field to hide tab company currency
    diff_currency = fields.Boolean(string='Diff Currency', readonly=True, compute='_check_diff_currency')
    
    trans_type = fields.Selection([('local', 'Local'), ('export', 'Fxport')], string='Trans Type', default='local', readonly=True) 
    supplier_inv_date=fields.Date('Vendor Invoice Date', readonly=True, states={'draft':[('readonly',False)]}, copy=False)
    currency_rate = fields.Float(compute='_get_currency_rate', string='Currency Rate', store=False)
    
    #THANH: Convert into company currency
    currency_invoice_line_ids = fields.One2many('account.invoice.line', 'invoice_id', string='Invoice Lines',
        readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    amount_untaxed_company = fields.Monetary(string='Untaxed Amount', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount_company', track_visibility='always')
    amount_tax_company = fields.Monetary(string='Tax', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount_company')
    amount_total_company = fields.Monetary(string='Total', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount_company')
    
    #THANH: Change Vendor Reference into Invoice Number
    reference = fields.Char(string='Invoice Number',
        help="The partner reference of this invoice.", readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    
    #THANH: Allow change due date before paid state
    date_due = fields.Date(string='Due Date',
        readonly=True, states={'draft': [('readonly', False)], 'open': [('readonly', False)]}, index=True, copy=False,
        help="If you use payment terms, the due date will be computed automatically at the generation "
             "of accounting entries. The payment term may compute several due dates, for example 50% "
             "now and 50% in one month, but if you want to force a due date, make sure that the payment "
             "term is not set on the invoice. If you keep the payment term and the due date empty, it "
             "means direct payment.")
    
    #THANH: Show journal for TSCD, CPTT, CCDC
    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ]
        
        #THANH: get other journal
        if self._context.get('other_journal_type', False):
            domain = [
                ('type', 'in', ['general']),
                ('company_id', '=', company_id),
            ]
        return self.env['account.journal'].search(domain, limit=1)
    
    journal_id = fields.Many2one('account.journal', string='Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=_default_journal,
        domain="[('type', 'in', context.get('other_journal_type', {'out_invoice': ['sale'], 'out_refund': ['sale'], 'in_refund': ['purchase'], 'in_invoice': ['purchase'], 'general': ['general']}.get(type, []))), ('company_id', '=', company_id)]")
    
    @api.multi
    def action_view_move_line(self):
        #THANH: View Invoice Move Lines
        move_ids = []
        for inv in self:
            for line in inv.move_id.line_ids:
                move_ids.append(line.id)
        
            #THANH: select move_line id from payment
            self.env.cr.execute('''select id from account_move_line
                where payment_id in (select payment_id from account_invoice_payment_rel where invoice_id=%s)
                '''%(inv.id))
            move_ids += [x[0] for x in self.env.cr.fetchall()]
            
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }
        
    @api.multi
    def action_view_payment(self):
        if self.type in ['in_invoice', 'in_refund']:
            action = self.env.ref('account.action_account_payments_payable')
        else:
            action = self.env.ref('account.action_account_payments')
        result = action.read()[0]
        result['context'] = {}
        inv_ids = [inv.id for inv in self]
        self.env.cr.execute('select payment_id from account_invoice_payment_rel where invoice_id in (%s)'%(','.join(map(str, inv_ids))))
        payment_ids = [x[0] for x in self.env.cr.fetchall()]
        if len(payment_ids):
            if len(payment_ids) > 1:
                result['domain'] = "[('id','in',[" + ','.join(map(str, payment_ids)) + "])]"
            elif len(payment_ids) == 1:
                res = self.env.ref('account.view_account_payment_form', False)
                result['views'] = [(res and res.id or False, 'form')]
                result['res_id'] = payment_ids and payment_ids[0] or False
            return result
        return True
    
    def inv_line_characteristic_hashcode(self, invoice_line):
        """Overridable hashcode generation for invoice lines. Lines having the same hashcode
        will be grouped together if the journal has the 'group line' option. Of course a module
        can add fields to invoice lines that would need to be tested too before merging lines
        or not."""
        return "%s-%s-%s-%s-%s" % (
            invoice_line['account_id'],
            invoice_line.get('tax_line_id', 'False'),
            #THANH: Group only for account, no group for product_id 
#             invoice_line.get('product_id', 'False'),
            False,
            #THANH: Group only for account, no group for product_id 
            invoice_line.get('analytic_account_id', 'False'),
            invoice_line.get('date_maturity', 'False'),
        )
    def group_lines(self, iml, line):
        """Merge account move lines (and hence analytic lines) if invoice line hashcodes are equals"""
        if self.journal_id.group_invoice_lines:
            line2 = {}
            
            #THANH: Change name of entry item when group by product
            key_group_product = {}
            
            for x, y, l in line:
                tmp = self.inv_line_characteristic_hashcode(l)
                #THANH: Change name of entry item when group by product
                if l.get('product_id', 'False'):
                    key_group_product[tmp] = self.name
                    
                if tmp in line2:
                    am = line2[tmp]['debit'] - line2[tmp]['credit'] + (l['debit'] - l['credit'])
                    line2[tmp]['debit'] = (am > 0) and am or 0.0
                    line2[tmp]['credit'] = (am < 0) and -am or 0.0
                    line2[tmp]['amount_currency'] += l['amount_currency']
                    line2[tmp]['analytic_line_ids'] += l['analytic_line_ids']
                    qty = l.get('quantity')
                    if qty:
                        line2[tmp]['quantity'] = line2[tmp].get('quantity', 0.0) + qty
                else:
                    line2[tmp] = l
            
            line = []
            for key, val in line2.items():
                #THANH: Update label for grouped lines
                if key_group_product != {} and key_group_product.has_key(str(key)):
                    val['name'] = key_group_product[str(key)]
                #THANH: Update label for grouped lines
            
                line.append((0, 0, val))
        return line
    
    @api.multi
    def name_get(self):
        TYPES = {
            'out_invoice': _('Invoice'),
            'in_invoice': _('Vendor Bill'),
            'out_refund': _('Refund'),
            'in_refund': _('Vendor Refund'),
        }
        result = []
        for inv in self:
            #THANH: Show Invoice Number and reference, no need to show Description, show partner
#             result.append((inv.id, "[%s] %s" % (inv.reference or inv.number or TYPES[inv.type], inv.name or '')))
            result.append((inv.id, "[%s] %s" % (inv.reference or inv.number or TYPES[inv.type], _(inv.partner_id.shortname or inv.partner_id.name))))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            #THANH: Search by reference firstly
            recs = self.search([('reference', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('number', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    #THANH: Do not duplicate invoice (check Partner, Inv Number and Inv Date)
    def check_invoice_duplication(self, cr, uid, ids, context=None):
        for invoice in self.browse(cr, uid, ids):
            where = 'WHERE ai.id != %s'%(invoice.id)
            if invoice.partner_id:
                where += ' AND ai.partner_id = %s'%(invoice.partner_id.id)
            if invoice.type in ['out_invoice', 'out_refund', 'in_refund'] and invoice.date_invoice:
                date = invoice.date_invoice
                where += " AND ai.date_invoice = '%s'"%(date)
#                 invoice_date = datetime.strptime(date, DATE_FORMAT)
#                 y = invoice_date.strftime('%Y')
#                 where += " AND EXTRACT(YEAR FROM ai.date_invoice)::text = '%s'"%(y)
            if invoice.type in ['in_invoice'] and invoice.supplier_inv_date:
                date = invoice.supplier_inv_date
                where += " AND ai.supplier_inv_date = '%s'"%(date)
#                 invoice_date = datetime.strptime(date, DATE_FORMAT)
#                 y = invoice_date.strftime('%Y')
#                 where += " AND EXTRACT(YEAR FROM ai.supplier_inv_date)::text = '%s'"%(y)
            
            if invoice.reference:
                where += " AND ai.reference = '%s'"%(invoice.reference)
                sql = "SELECT ai.reference FROM account_invoice ai " + where
                cr.execute(sql)
                res = cr.fetchall()
                if len(res) > 0:
                    reference = res[0][0] or ''
                    raise UserError(_("Invoice Number (%s) already exist!") % (reference))
        return True
    
    _constraints = [(check_invoice_duplication, '', [])]
    
#     def _total_qty(self):
#         for order in self:
#             total_qty = 0
#             for line in order.invoice_line_ids:
#                 total_qty +=line.quantity
#             order.total_qty = total_qty
#             
#     total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty', store=True)
    
    @api.multi
    def action_move_create(self):
        #THANH: Check invoice number when validate it (!= '/')
        for inv in self:
            if not inv.date_invoice:
                raise UserError(_("Entry Date (Ngày hạch toán) is empty!"))
            if inv.type not in ('out_invoice','out_refund'):
                if inv.supplier_inv_date and inv.date_invoice and inv.supplier_inv_date > inv.date_invoice:
                    raise UserError(_("Vendor Invoice Date must be smaller than Invoice Date (Ngày hóa đơn phải nhỏ hơn ngày hách toán)!"))
            if inv.type in ['in_invoice'] and not inv.supplier_inv_date:
                raise UserError(_("Vendor Invoice Date (Ngày xuất hóa đơn) is empty!"))
            if not inv.name:
                raise UserError(_("Reference/Description (Diễn giải hóa đơn) is empty!"))
            if inv.amount_total == 0:
                raise UserError(_("Invoice Amount (Giá trị hóa đơn) must be bigger than 0!"))
            #THANH: Update tax description before journal entry generated (Mo ta tax - mo ta hoa don) -> de sau nay in so cai
            for line in inv.tax_line_ids:
                line.write({'name': _(line.tax_id.description) + _(' - ') + _(inv.name)})
            
        super(AccountInvoice, self).action_move_create()
        
        #THANH: Update journal entry after it generated
        for inv in self:
            if inv.move_id:
                inv.move_id.write({'doc_date': inv.supplier_inv_date or inv.date_invoice,
                                   'narration': inv.name})
        
    @api.model
    def create(self, vals):
        #THANH: Get date_invoice same with supplier invoice date
        if vals.has_key('supplier_inv_date') and vals.get('supplier_inv_date',False):
            vals.update({'supplier_inv_date': vals['supplier_inv_date']})
        elif vals.has_key('date_invoice') and vals.get('date_invoice',False):
            vals.update({'supplier_inv_date': vals['date_invoice']})
#         if vals.get('name', False) and vals.get('type'):
#             partner = self.env['res.partner'].browse(vals['partner_id'])
#             if vals.get('type') == 'out_invoice':
#                 vals.update({'name': _("Xuất bán hàng cho khách hàng ") + _(partner.name)})
#             if vals.get('type') == 'in_invoice':
#                 vals.update({'name': _("Nhập hàng hóa của nhà cung cấp ") + _(partner.name)})
        return super(AccountInvoice,self).create(vals)
    
    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an invoice which is not draft or cancelled. You should refund it instead.'))
            #THANH: No need to check this
#             elif invoice.move_name:
#                 raise UserError(_('You cannot delete an invoice after it has been validated (and received a number). You can set it back to "Draft" state and modify its content, then re-confirm it.'))
        return super(models.Model, self).unlink()
    
    @api.multi
    def action_cancel(self):
        moves = self.env['account.move']
        for inv in self:
            if inv.move_id:
                moves += inv.move_id
            if inv.payment_move_line_ids:
                raise UserError(_('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

        # First, set the invoices as cancelled and detach the move ids
        self.write({'state': 'cancel', 'move_id': False})
        if moves:
            # second, invalidate the move(s)
            #THANH: pass context to pass check cancel
            moves.with_context(invoice_force_cancel=True).button_cancel()
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
            moves.unlink()
        return True
    
AccountInvoice()

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
#     def _price_unit_include(self):
#         partner_id = False
#         currency_price_subtotal =0.0
#         price_unit_include =0.0
#         tax_obj = self.pool.get('account.tax')
#         tax_nxk_ids = []
#         cr = self.env.cr
#         uid = self.env.user.id
#         
#         for line in self:
#             partner_id = line.invoice_id.partner_id
#             for tax_nxk in line.invoice_line_tax_ids:
#                 if tax_nxk.transaction_type in ('import','export'):
#                     tax_nxk_ids.append(tax_nxk.id)
#         if tax_nxk_ids:  
#             tax_nxk_ids = self.pool.get('account.tax').browse(cr, uid, tax_nxk_ids)
#                 
#         for line in self:
#             price = line.price_unit 
#             if tax_nxk_ids:
#                 taxes = tax_obj.compute_all(cr, uid, tax_nxk_ids, price, line.quantity, line.product_id, partner_id)
#                 price_unit_include = 0.0
#                 for tax in taxes['taxes']:
#                     price_unit_include += tax['amount']
#                 if line.invoice_id and line.invoice_id.currency_id:
#                     price_unit_include =  (line.price_unit_include/line.product_qty) + line.price_unit
#                     currency_price_subtotal = line.currency_id.compute(price_unit_include,line.company_id.currency_id)
#                     line.price_unit_include = price_unit_include
#                     line.currency_price_unit_include = currency_price_subtotal
#             else:
#                 line.price_unit_include = line.price_unit
#                 line.currency_price_unit_include = line.currency_id.compute(line.price_unit,line.company_id.currency_id,False)
#         return True
                
        
    def _currency_price_all(self):
        for line in self:
            date = line.invoice_id.date_invoice
            
            taxes = line.invoice_line_tax_ids.compute_all(line.price_unit, line.invoice_id.currency_id, line.quantity, line.product_id, line.invoice_id.partner_id)
            line.currency_price_unit = line.invoice_id.currency_id.with_context(date=date).compute(line.price_unit, line.company_id.currency_id)
            line.currency_price_subtotal =  line.invoice_id.currency_id.with_context(date=date).compute(taxes['total_included'], line.company_id.currency_id)
    
    is_promotion = fields.Boolean('Is Promotion', copy=False, default=False)
    currency_price_subtotal = fields.Monetary(compute='_currency_price_all', string='Amount')
    currency_price_unit = fields.Monetary(compute='_currency_price_all', string='Price Unit')
    
#     price_unit_include= fields.Monetary(compute='_price_unit_include', string='Price Include')
#     currency_price_unit_include = fields.Monetary(compute='_price_unit_include', string='Currency Price Include')
