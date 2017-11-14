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


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = 'id desc'
    
    @api.model
    def cron_create_stock_kcs(self,ids=None):
        return True
#         for line in self.env['request.kcs.line'].search([]):
#             line.mc_degree = line.mc_degree * 100
#             line.fm_gram = line.mc_degree * 100
#             line.black_gram = line.black_gram
#             line.Broken Gram = line.Broken_gram
            
#         picking_ids = self.env['stock.picking'].search([('state','=','draft')], limit=30)
#         for picking in picking_ids:
#             try:
#                 picking.action_confirm()
#                 picking.btt_approved()
#             except Exception, e:
#                 print picking.name
    
#     @api.multi
#     def action_revert_done(self):
#         for pick in self:
#             #Kiệt: Query nghiệp vụ nhập kho chưa phân bổ theo product
#             for move in pick.move_lines:
#                 sql ='''
#                 UPDATE stock_move SET allocated = false ,allocate_invoiced = false
#                 WHERE
#                     id in (
#                         SELECT sm.id
#                         FROM stock_move sm  
#                         WHERE 
#                             product_id = %s
#                             and sm.state = 'done'
#                             and sm.date >= '%s'
#                         ORDER BY date )
#                 '''%(move.product_id.id,move.date)
#                 self.env.cr.execute(sql)
#                 
#                 sql ='''
#                     DELETE FROM stock_move_allocation
#                     WHERE
#                         in_date >= '%s'
#                         and product_id = %s;
#                     
#                     DELETE FROM invoice_allocation
#                     WHERE
#                         in_date >= '%s'
#                         and product_id = %s;
#                 '''%(move.date,move.product_id.id,move.date,move.product_id.id)
#                 self.env.cr.execute(sql)
#         super(StockPicking,self).action_revert_done()

class StockMoveAllocation(models.Model):
    _name = "stock.move.allocation"
    _order = 'in_date,allocated_date'
    
    #Kiet: Update lai ty gia khi thay doi cờ
    type = fields.Selection([('fifo', 'FIFO'), ('lifo', 'LIFO')], string='Type', default='fifo', readonly=True) 
    #From move  
    from_move_id = fields.Many2one('stock.move',string="From Move")
    in_date = fields.Datetime(related='from_move_id.date', string="Incoming Date", readonly=True, store=True)
    from_origin = fields.Char(related='from_move_id.picking_id.origin', string="Origin", readonly=True, store=True)
    picking_id = fields.Many2one(related='from_move_id.picking_id',
                 string="From Picking",relation='stock.picking',store=True)
    to_move_id = fields.Many2one('stock.move',string="To Move")
    #allocated_date = fields.Datetime(related='to_move_id.date', string="Allocated Date", readonly=True, store=True)
    allocated_date = fields.Date(string="Allocated Date", readonly=True)
    warehouse_id = fields.Many2one(related='to_move_id.picking_type_id.warehouse_id', relation='stock.warehouse',
                                   string='Warehouse', readonly=True, store=True)
    location_id = fields.Many2one(related='to_move_id.location_id', relation='stock.location',
                                   string='Location', readonly=True, store=True)
    
#     from_price_unit = fields.Float(related='from_move_id.price_unit',string="Price Unit")
#     from_product_uom_qty = fields.Float(related='from_move_id.product_uom_qty',string="From Original Qty")
    
    product_id = fields.Many2one(related='from_move_id.product_id', string='Product', readonly=True,store=True)
    uom_id = fields.Many2one(related='from_move_id.primary_uom_id', string='UoM', readonly=True)
    allocated_qty = fields.Float(string='Allocated Qty', readonly=True,digits=(12, 0))
    allocated_value = fields.Float(string='Allocated Value', readonly=True)
#     to_product_uom_qty = fields.Float(related='to_move_id.product_uom_qty',string="To Original Qty")
#     qty_remain = fields.Float(compute='_qty_remain', string='Qty Remain', readonly=True, store=True)

    
    
    @api.model
    def cron_stock_fifo(self,ids=None):
        location_id = self.env['stock.location'].search([('usage','=','NVP - BMT')])
        location_dest_id = self.env['stock.location'].search([('usage','=','HCM')]) 
        #Kiet: Query nghệp vụ xuất kho.
        outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),('location_dest_id','=',location_dest_id.id)
                                                  ,('entries_id','=',False),('fifo_out','=',False)], order ="date")
        for outgoing in outgoing_ids:
            while(not outgoing.fifo_out):
                incoming_ids = self.env['stock.move'].search([('location_id','!=',location_id.id),('location_dest_id','=',location_id.id)
                            ,('price_unit','!=',0),('fifo','=',False),('product_id','=',outgoing.product_id.id)], order ="date")
                if incoming_ids:
                    for incoming in incoming_ids:
    #                     if outgoing.unfifo_qty == incoming_move.fifo_qty:
    #                         break
                        fifo = outgoing.unfifo_qty - incoming.unfifo_qty
                        #Kiet: Truong hop số lượng stock move lớn hơn lượng cần FIFO
                        if fifo - outgoing.unfifo_qty  >0:
                            qty_fifo = outgoing.unfifo_qty 
                        else:
                            qty_fifo = fifo
                         
                        val ={
                              'fifo_id':incoming.id,
                              'product_qty':qty_fifo,
                              'fifo_out_id':outgoing.id
                        }
                        self.env['stock.move.fifo'].create(val)
                else:
                    break
        return  

class StockMove(models.Model):
    _inherit = "stock.move"
    
    allocated = fields.Boolean(string='Allocated', default=False)
    allocated_to_moves = fields.One2many('stock.move.allocation', 'from_move_id', string='Allocated To Moves')
    split_from_moves = fields.One2many('stock.move.allocation', 'to_move_id', string='Split From Moves')

    @api.multi
    def action_done(self):
        super(StockMove,self).action_done()
        #Kiet Update lai Allocation 
        for move in self:
            #Kiệt: Query nghiệp vụ nhập kho chưa phân bổ theo product
            sql ='''
            UPDATE stock_move SET allocated = false 
            WHERE
                id in (
                    SELECT sm.id
                    FROM stock_move sm  
                    WHERE 
                        product_id = %s
                        and sm.state = 'done'
                        and date(timezone('UTC',sm.date::timestamp)) >= date(timezone('UTC','%s'::timestamp))
                    ORDER BY date )
            '''%(move.product_id.id,move.date)
            self.env.cr.execute(sql)
            
            sql ='''
                DELETE FROM stock_move_allocation
                WHERE
                    date(timezone('UTC',in_date::timestamp)) >= date(timezone('UTC','%s'::timestamp))
                    and product_id = %s
            '''%(move.date,move.product_id.id)
            self.env.cr.execute(sql)
        return True
    
    # kiet sinh bút toán
    def _get_accounting_data_for_valuation(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_input'].id
        acc_dest = accounts['stock_output'].id
        
        #Kiệt: Trường hợp xuất kho
        if line.location_id.usage =='internal' and line.location_dest_id.usage != 'internal':
            #kiet: Trường hợp xuất kho mất mát
            if line.location_dest_id.usage == 'inventory' and (not line.location_dest_id.scrap_location):
                acc_dest = accounts['account_loss']
            #Kiet: Trường hợp xuất kho (Xuất bán thành phẩm hay xuất NVL Sản xuất
            else :
                acc_dest = accounts['stock_output'].id
        
        #Kiet: Trượng hợp nhập kho
        if line.location_id.usage !='internal' and line.location_dest_id.usage == 'internal':
            #Kiet: Nhập kho sản xuất 
            if line.location_id.usage == 'production':
                acc_src = accounts['wip_account']
            #Kiệt: Nhập kho mua hàng
            else:
                acc_src = accounts['stock_input'].id
            
        acc_valuation = accounts.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (line.product_id.name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (line.product_id.name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation
    
    def _prepare_account_move_line(self,line, qty,  credit_account_id, debit_account_id):
        debit = credit = line.price_unit * qty
        partner_id = (line.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(line.picking_id.partner_id).id) or False
        name =''
        if line.picking_id:
            name = line.picking_id.origin + ' - ' +line.product_id.default_code
        else:
            name = line.product_id.default_code
        debit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit':  0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            #'amount_currency':amount_currency,
            'account_id': debit_account_id,
            #'currency_id': line.second_currency_id.id
        }
        credit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': 0.0,  
            'credit': credit or 0.0,
            #'second_ex_rate':second_ex_rate or 0.0,
            #'amount_currency': (-1) * amount_currency,
            'account_id': credit_account_id,
            #'currency_id': line.second_currency_id.id
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    #Kiet: Nghiep vu nhập kho NVL khi đã FIFO
    def get_entries_input(self):
        move = self.env['stock.move']
        move_obj = self.env['account.move']
        move_lines =[]
        for move_line in move.search([('entries_id','=',False),('state','=','done'),('date','>=','2016-10-01'),('product_qty','!=',0),
                                      ('price_unit','!=',0),
                                      ('location_id.usage','in',('procurement','production')),('location_dest_id.usage','=','internal')]):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(move_line)
            move_lines = self._prepare_account_move_line(move_line, move_line.product_qty,  acc_src, acc_valuation)
            if move_lines:
                journal = self.env['account.journal'].browse(journal_id)
                ref =''
                if move_line.picking_id:
                    ref = move_line.picking_id.name
                else:
                    ref = journal.name
                date = move_line.date
                
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line.entries_id = new_move_id.id
    
    def get_entries_output(self):
        move = self.env['stock.move']
        move_obj = self.env['account.move']
        move_lines =[]
        for move_line in move.search([('entries_id','=',False),('state','=','done'),('date','>=','2016-10-01'),('product_qty','!=',0),
                                      ('price_unit','!=',0),
                                      ('location_id.usage','=','internal'),('location_dest_id.usage','!=','internal')]):
            journal_id, acc_src, acc_dest, acc_valuation = self._get_accounting_data_for_valuation(move_line)
            move_lines = self._prepare_account_move_line(move_line, move_line.product_qty,  acc_src, acc_valuation)
            if move_lines:
                journal = self.env['account.journal'].browse(journal_id)
                ref =''
                if move_line.picking_id:
                    ref = move_line.picking_id.name
                else:
                    ref = journal.name
                date = move_line.date
                
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line.entries_id = new_move_id.id
    @api.model
    def cron_create_entries_fifo(self,ids=None):
        print 'Create en'
        self.get_entries_input()
        return 1
    
    
    second_currency_id = fields.Many2one('res.currency',related='company_id.second_currency_id', string="2rd Currency", readonly=True)
    com_currency_id = fields.Many2one('res.currency', related='company_id.currency_id',string="Currency", readonly=True)
    
    entries_id = fields.Many2one('account.move', string='Entries', readonly=True)
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d-%m-%Y')
    
    def get_dates(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y-%m-%d')
    
    @api.depends('date')
    def _compute_date(self):
        for line in self:
            line.date_tz = self.get_dates(line.date)
            line.day_tz = self.get_date(line.date)
            
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    
    
    @api.depends('location_id','location_dest_id')
    def _compute_type(self):
        for line in self:
            if (line.location_id.usage != 'internal' and line.location_dest_id.usage == 'internal'):
                line.trans_type = 'In'
            elif (line.location_id.usage == 'internal' and line.location_dest_id.usage != 'internal'):
                line.trans_type = 'Out'
            else:
                line.trans_type = 'internal'
    
    trans_type = fields.Char(compute='_compute_type', store=True,string='Trans Type')
    
    @api.depends('split_from_moves','split_from_moves.product_id','split_from_moves.uom_id',
                 'split_from_moves.allocated_qty','split_from_moves.allocated_value')
    def _compute_values(self):
        for line in self:
            
            if (line.location_id.usage != 'internal' and line.location_dest_id.usage == 'internal'):
                line.values = line.product_qty * line.price_unit
                line.product_allocation = 0.0
            elif (line.location_id.usage == 'internal' and line.location_dest_id.usage != 'internal'):
                value = 0.0
                product_allocation = 0
                for allocation in line.split_from_moves:
                    value += allocation.allocated_value or 0.0
                    product_allocation += allocation.allocated_qty or 0.0
                line.values = value
                line.product_allocation = product_allocation
            else:
                line.values =  0.0
                line.product_allocation =0.0
                
    values = fields.Float(compute='_compute_values', store=True,string='Values')
    product_allocation= fields.Float(compute='_compute_values', store=True,string='Allocated')
