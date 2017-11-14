# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class StockMove(models.Model):
    _inherit = "stock.move"
    
    allocate_invoiced = fields.Boolean(string='Allocate Invoiced', default=False)

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    entries_cogs_id = fields.Many2one('account.move','Entries COGS')
    
class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"
    
    allocated = fields.Boolean(string='Allocated', default=False)
    allocated_to_invoiced = fields.One2many('invoice.allocation', 'from_move_id', string='Allocated To Moves')
    split_from_invoiced = fields.One2many('invoice.allocation', 'invoice_line_id', string='Split From Moves')
    
    
class InvoiceAllocation(models.Model):
    _name = "invoice.allocation"
    _order = 'id desc'
    
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    com_currency_id = fields.Many2one('res.currency', related='company_id.currency_id',string="Currency", readonly=True)
    #Kiet: Update lai ty gia khi thay doi cờ
    type = fields.Selection([('fifo', 'FIFO'), ('lifo', 'LIFO')], string='Type', default='fifo', readonly=True) 
    #From move  
    from_move_id = fields.Many2one('stock.move',string="From Move")
    in_date = fields.Datetime(related='from_move_id.date', string="Incoming Date", readonly=True, store=True)
    picking_id = fields.Many2one(related='from_move_id.picking_id',
                 string="From Picking",relation='stock.picking',store=True)
    invoice_line_id = fields.Many2one('account.invoice.line',string="Invoice")
    invoice_id = fields.Many2one(type='account.invoice',related='invoice_line_id.invoice_id', string="Invoice", readonly=True, store=True)
    allocated_date = fields.Date(related='invoice_id.date_invoice', string="Allocated Date",  store=True)
    product_id = fields.Many2one(related='from_move_id.product_id', string='Product', readonly=True,store=True)
    uom_id = fields.Many2one(related='from_move_id.primary_uom_id', string='Primary UoM', readonly=True)
    allocated_qty = fields.Float(string='Allocated Qty', readonly=True,digits=(12, 0))
    allocated_value = fields.Monetary(string='Allocated Value', readonly=True, currency_field='com_currency_id')
    entries_cogs= fields.Boolean(string='Entries Cogs', default=False)
    
    @api.model
    def cron_invoice_fifo(self,ids=None):
        out_qty = 0.0
        company_currency_id = self.env['res.users'].browse(self.env.uid).company_id.currency_id
        second_currency_id = self.env['res.users'].browse(self.env.uid).company_id.second_currency_id
        
        #Kiet: Query nghệp vụ các hoá đơn
        sql ='''
            SELECT ail.id,quantity product_qty,ail.product_id,ail.uom_id
                FROM account_invoice_line ail join  account_invoice ai on ail.invoice_id =ai.id
                WHERE type in ('out_invoice') 
                    AND state in('done','open')
                    AND (ail.allocated = false or ail.allocated is null)
                ORDER BY ai.date_invoice,ail.id
        '''
        self.env.cr.execute(sql)
        for invoice in self.env.cr.dictfetchall():
#             sql = '''
#                 DELETE FROM invoice_allocation WHERE invoice_line_id = %s                
#             '''%(invoice['id'])
#             self.env.cr.execute(sql)
            #Kiệt lấy số lượng chưa phân bổ của stock_move Với bảng đã phân bổ
            out_qty = invoice['product_qty'] or 0.0
            while out_qty !=0:
                flag = False
                #Kiệt: Query nghiệp vụ nhập kho chưa phân bổ theo product
                sql ='''
                    SELECT sm.id, sm.price_unit,sm.price_currency,sm.date
                    FROM stock_move sm  
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.usage not in ('internal')
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage in ('internal')
                    WHERE 
                        product_id = %s
                        and (sm.allocate_invoiced != true  or sm.allocate_invoiced is null)
                        and sm.state ='done'
                    order by sm.date 
                '''%(invoice['product_id'])
                self.env.cr.execute(sql)
                for incoming in self.env.cr.dictfetchall():
                    allocated_qty =0.0
                    flag = True
                    if out_qty == 0:
                        break;
                    #Kiệt: Kiểm tra tổng số lượng phân bổ của Stock Move
                    sql ='''
                        SELECT sum(allocated_qty) allocated_qty 
                        FROM (
                            SELECT sum(allocated_qty) *(-1) as allocated_qty
                            FROM  invoice_allocation 
                            WHERE 
                                from_move_id = %s
                            union all 
                            SELECT product_qty as allocated_qty
                            FROM stock_move sm
                            where 
                                id = %s
                        )x
                    '''%(incoming['id'],incoming['id'])
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        allocated_qty = i['allocated_qty'] or 0.0
                        
                    val ={
                          'from_move_id':incoming['id'],
                          'invoice_line_id':invoice['id']
                    }
                    if out_qty >= allocated_qty:
                        allocated_value = False
                        out_qty = out_qty - allocated_qty
                        price_unit = incoming['price_currency']
                        allocated_value = second_currency_id.with_context(date=incoming['date']).compute(price_unit * allocated_qty, 
                                                                                    company_currency_id)
                        val.update({'allocated_qty': allocated_qty,
                                        'allocated_value':allocated_value})
                        sql ='''
                            UPDATE stock_move 
                            SET allocate_invoiced = true 
                            WHERE id  = %s;                           
                        '''%(incoming['id'])
                        self.env.cr.execute(sql)
                    else:
                        allocated_value = False
                        price_unit = incoming['price_currency'] or 0.0
                        allocated_value = second_currency_id.with_context(date=incoming['date']).compute(price_unit * out_qty, 
                                                                                   company_currency_id)
                        val.update({'allocated_qty': out_qty,
                                        'allocated_value': allocated_value})
                        out_qty = 0
                    if out_qty == 0:
                        sql ='''
                            UPDATE account_invoice_line 
                            SET allocated = true
                            WHERE id = %s;
                        '''%(invoice['id'])
                        self.env.cr.execute(sql)
                    self.env['invoice.allocation'].create(val)
                if not flag:
                    break
        return  
    
    
    def _get_accounting_data(self, line,invoice):
        product_obj = self.env['product.template']
        journal_id = self.env['account.journal'].search([('code','=','INV')])
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        if invoice.trans_type =='export':
            acc_dest = accounts['cogs_export']
        else:
            acc_dest = accounts['cogs_local']
        acc_src = accounts['stock_output'].id
        return journal_id, acc_src, acc_dest
    def _prepare_account_move_line(self,line,invoice, credit_account_id, debit_account_id):
        second_ex_rate = 0.0
        company_currency_id = self.env['res.users'].browse(self.env.uid).company_id.currency_id
        second_currency_id = self.env['res.users'].browse(self.env.uid).company_id.second_currency_id
        sql ='''
            SELECT rate
            FROM res_currency_rate
            where currency_id = %s
            and date(timezone('UTC', name::timestamp)) =  date(timezone('UTC', '%s'::timestamp))
        '''%(self.env.user.company_id.second_currency_id.id,line.in_date)
        self.env.cr.execute(sql)
        for records in self.env.cr.dictfetchall():
            second_ex_rate = records['rate']
        
        debit = credit = line.allocated_value
        amount_currency = company_currency_id.with_context(date=line.in_date).compute(debit, second_currency_id)
        partner_id = (line.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(line.invoice_id.partner_id).id) or False
        debit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': line.allocated_qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit':  0.0,
            'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency':amount_currency,
            'account_id': debit_account_id,
            'currency_id': second_currency_id.id,
            'partner_id':invoice.partner_id.id
        }
        credit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': line.allocated_qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': 0.0,  
            'credit': credit or 0.0,
            'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency': (-1) * amount_currency,
            'account_id': credit_account_id,
            'currency_id': second_currency_id.id,
            'partner_id':invoice.partner_id.id
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    @api.model
    def cron_entries_cogs_fifo(self,ids=None):
        move_obj = self.env['account.move']
        #Kiet: Query nghệp vụ các hoá đơn
        sql ='''
        
            SELECT ai.id invoice_id,ial.id allocation_id
                FROM account_invoice ai 
                JOIN invoice_allocation ial on ai.id = ial.invoice_id
                WHERE ai.type in ('out_invoice') 
                    AND state in('done','open')
                    AND (entries_cogs is null or entries_cogs = False)
                ORDER BY ai.date_invoice, ai.id
                
        '''
        self.env.cr.execute(sql)
        for invoice in self.env.cr.dictfetchall():
            invoice_allocation = self.env['invoice.allocation'].browse(invoice['allocation_id'])
            invoice = self.env['account.invoice'].browse(invoice['invoice_id'])
            journal_id, acc_src, acc_dest = self._get_accounting_data(invoice_allocation,invoice)
            move_lines = self._prepare_account_move_line(invoice_allocation,invoice, acc_src, acc_dest)
            if move_lines:
                if not invoice.entries_cogs_id:
                    date = invoice_allocation.from_move_id.date
                    new_move_id = move_obj.create({
                                          'partner_id': invoice.partner_id.id, 
                                          'journal_id': journal_id.id,
                                          'line_ids': move_lines,
                                          'date': date,
                                          'ref': journal_id.name,
                                          'narration':''})
                    new_move_id.post()
                    invoice.entries_cogs_id = new_move_id.id
                    
                else:
                    invoice.entries_cogs_id.write({'line_ids':move_lines})
                
                invoice_allocation.entries_cogs = True
            
            
    