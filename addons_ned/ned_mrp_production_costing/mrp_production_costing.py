# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
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


from lxml import etree
import base64
import xlrd
from openerp.exceptions import UserError


class  ReportFifoManagement(models.Model):
    _name ="report.fifo.management"
    
    name = fields.Many2one('account.period',string="period")
    location_id =fields.Many2one('stock.location',string="From Location")
    location_dest_id =fields.Many2one('stock.location',string="To Location")
    fifo_ids =  fields.One2many('report.fifo.management.line','fifo_id',string='FIFO',readonly=True)
    fifo_management_ids = fields.One2many('stock.picking','fifo_management_id',string='FIFO',readonly=True)
    
    
    
    @api.multi
    def adj_fifo_qty(self):
#         for line in self.fifo_management_ids:
#             line.action_revert_done()
#             line.unlink()
#             line.fifo_stock()
            
        for line in self.fifo_ids:
            if line.adj_qty and line.adj_qty<0:
                 
                picking_val = { 
                    'fifo_management_id':self.id,
                    'date_done':time.strftime(DATETIME_FORMAT), 
                    'name':'/' or False,
                    'picking_type_id': 111,
                    'date': time.strftime(DATETIME_FORMAT),
                    'location_id': self.location_id.id or False, 
                    'location_dest_id': self.location_dest_id.id, 
                    'state':'done',
                }
                picking_id = self.env['stock.picking'].create(picking_val)
                
                move_val = {
                    'picking_id':picking_id.id,
                    'name': line.product_id.name or '',
                    'product_id': line.product_id.id,
                    'product_uom': line.product_id.uom_id.id,
                    'init_qty':line.adj_qty or 0.0,
                    'product_uom_qty': line.adj_qty or 0.0,
                    'price_unit': 0.0,
                    'location_id': self.location_id.id or False, 
                    'location_dest_id': self.location_dest_id.id,  
                    'date': time.strftime(DATETIME_FORMAT), 
                    'company_id': 1,
                    'state':'done', 'scrapped': False,
                    'warehouse_id': 1}
                move_id = self.env['stock.move'].create(move_val)
                picking_id.fifo_stock()
        
    @api.multi
    def load_fifo(self):
        this = self
        location_id = this.location_id  
        location_dest_id = this.location_dest_id
        
        sql ='''
            DELETE from report_fifo_management_line where fifo_id = %s
        '''%(this.id)
        self.env.cr.execute(sql)
        
        now = time.strftime('%Y-%m-%d')
        fiscalyear = self.env['account.fiscalyear'].search([('date_start', '<', now), ('date_stop', '>', now)], limit=1)
    
        val ={
              'company_id':1,
              'name':'Report Stock Balance Sheet',
              'period_length':'day',
              'times':'month',
              'date_end':this.name.date_stop,
              'date_start':this.name.date_start,
              
              'month':time.strftime('%m'),
              'fiscalyear_id':fiscalyear.id
              }
        on_hand = self.env['report.stock.balance.sheet'].create(val)
        on_hand.write({'location_ids':[[6,0,[location_id.id]]]})
        on_hand.load_data()
        on_hand.refresh()
        
        for line in on_hand.report_lines:
            
            incoming_ids = self.env['stock.move'].search([('location_id','!=',location_id.id),
                    ('location_dest_id','=',location_id.id),
                    ('state','=','done'),
                    #('date','<=',this.name.date_stop),
#                    ('date','>=','2017-01-02'),
                    ('product_id','=',line.product_id.id)], order ="date,id")
            unfifo_qty =0
            for incoming in incoming_ids:
                unfifo_qty += incoming.unfifo_qty
                    
            vals = {'product_id':line.product_id.id,
                    'onhand_qty':line.end_qty,
                    'onhand_vaue':line.end_value,
                    'unfifo_qty':unfifo_qty,
                    'fifo_id':this.id
                }
            self.env['report.fifo.management.line'].create(vals)
            on_hand.unlink()
#         outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
#               ('state','=','done'),('location_dest_id','=',location_dest_id),
#               ('entries_id','!=',False)], order ="date")


class  ReportFifoManagementLine(models.Model):
    _name ="report.fifo.management.line"
    
    
    @api.depends('onhand_qty', 'unfifo_qty')
    def _compute_qty(self):
        for line in self:
            line.adj_qty = line.onhand_qty - line.unfifo_qty
    
    
    product_id = fields.Many2one('product.product',string="product",)
    onhand_qty = fields.Float(string="Bal Qty",digits=(12, 0))
    onhand_vaue = fields.Float(string="Bal Values",digits=(12, 2))
    unfifo_qty = fields.Float(string="Un Fifo Qty",digits=(12, 0))
    adj_qty = fields.Float(string="ADJ Qty",digits=(12, 0),compute='_compute_qty')
    fifo_id = fields.Many2one('report.fifo.management',string="Fifo")

class  FifoManagement(models.Model):
    _name ="fifo.management"
    
    name = fields.Many2one('account.period',string="period", domain=[('state','=','draft')])
    location_id =fields.Many2one('stock.location',string="From Location")
    location_dest_id =fields.Many2one('stock.location',string="To Location")
    fifo_ids =  fields.Many2many('stock.move','management_fifo_ids','fifo_id','move_id',string='FIFO')
    product_id = fields.Many2one('product.product',string="Product")
    debit_account_id = fields.Many2one('account.account',string="Debit Acc")
    credit_account_id = fields.Many2one('account.account',string="Credit Acc")
    
    @api.depends('fifo_ids','fifo_ids.entries_id',)
    def _compute_perform(self):
        for this in self:
            count =0
            for line in this.fifo_ids:
                if line.queue == 'entries':
                    count +=1
            this.in_perform = count
            
    in_perform= fields.Float(compute='_compute_perform' ,string="Perform" ,store = True)
    
    state = fields.Selection([
        ('draft','Draft'),
        ('queue','Queue'),
        ('entries','Entries'),
        ('done','Done'),
        ],'Status', select=True, readonly=True,default='draft')
    
    @api.onchange('search_product_status')
    def on_change_search_product_status(self):
        search_product_status = self.search_product_status
        value = {}
        stock_move = self.env['stock.move']
        domain = []
        if search_product_status:
            domain.append(('queue','ilike',search_product_status))
        if domain:
            fifo_ids = stock_move.search( domain)
            value = {'inventory_line_id':fifo_ids}
        return {'value':value}
    
    @api.model
    def cron_watch_cron_validate_fifo(self, ids=None):
        mod_obj = self.env['ir.model.data']
        
        dummy, schedule_id = tuple(mod_obj.get_object_reference('ned_mrp_production_costing', "ir_cron_validate_fifo"))
        if schedule_id:
            try:
                schedule = self.env['ir.cron'].browse(schedule_id)
                inv_ids = self.env['stock.move'].search([('queue', '=', 'queue')])
                if len(inv_ids) and not schedule.active:
                    schedule.method_direct_trigger()
                
                for management_fifo_ids in self.env['fifo.management'].search([('state', '=', 'queue')]):
                    flag = False
                    for i in management_fifo_ids.fifo_ids:
                        if i.queue in ('draft','queue'):
                            return True
                    
                    if flag:
                        return True
                            
                    
            except Exception, ex:
                print 'fifo.management'
                pass
        return True
    
    @api.model
    def cron_validate_fifo(self, ids=None):
        mod_obj = self.env['ir.model.data']
        
        dummy, schedule_id = tuple(mod_obj.get_object_reference('ned_mrp_production_costing', "ir_cron_validate_fifo"))
        if schedule_id:
            try:
                for inv_ids  in self.env['stock.move'].search([('queue', '=', 'queue')], order='date', limit=30):
                    self.validate_fifo(inv_ids)
                    inv_ids.refresh()
                    if inv_ids.qty_out_fifo == inv_ids.product_uom_qty:
                        amount =0
                        for fifo in inv_ids.fifo_out_ids:
                            amount += fifo.out_qty * fifo.fifo_id.price_unit
                        inv_ids.price_unit = amount / inv_ids.product_uom_qty
                        #self.get_entries_gdn_fifo(inv_ids,amount)
                        inv_ids.queue ='entries'
#                 cron = self.env['ir.cron'].browse(schedule_id)
#                 if cron:
#                     cron.write({'active': False})
            except Exception, ex:
                return True
#                 cron.write({'active': False})
        return True
    
    
    def fifo_reopen_fifo(self,move_ids):
        for move in self.env['stock.move'].browse(move_ids):
            move.remove_fifo()
    
    
    def update_entries_create(self):
        
        sql = '''
               SELECT id from stock_move where date(timezone('UTC',date::timestamp)) between '2017-01-01' and '2017-02-28'
                and entries_id is not null and location_dest_id = 9
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            line = self.env['stock.move'].browse(i['id'])
            origin = line.origin
            origin = origin + ' - ' + line.product_id.default_code
            if line.entries_id:
                sql ='''
                    UPDATE account_move_line set name = '%s' where move_id = %s
                '''%(origin,line.entries_id.id)
                self.env.cr.execute(sql)
        
            
                
    
    @api.multi
    def entries_create(self):
#         self.update_entries_create()
#         return
        this =self
        
        

#         for move in this.fifo_ids:
#             if move.qty_out_fifo == move.product_uom_qty:
#                 debit_ac = this.debit_account_id.id
#                 credit_acc = this.credit_account_id.id
#                 self.get_entries_gdn_fifo(move,debit_ac,credit_acc,move.price_unit * move.product_uom_qty)
        
        for move in this.fifo_ids:
            if not move.entries_id:
                debit_ac = this.debit_account_id.id
                credit_acc = this.credit_account_id.id
                self.get_entries_gdn_fifo(move,debit_ac,credit_acc,move.price_unit * move.product_uom_qty)
            else:
                move.entries_id.button_cancel()
                move.entries_id.unlink()
        
        
#         for move in this.fifo_ids:
#             move.entries_id.button_cancel()
#             move.entries_id.unlink()
        
                    
                       
        
    @api.multi
    def load_fifo(self):
        this = self
        location_id = this.location_id
        location_dest_id = this.location_dest_id.id
        
        date_start = this.name.date_start + ' 00:00:00'
        date_stop = this.name.date_stop + ' 23:59:00'
        
        if this.product_id:
            outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
                                                      ('state','=','done'),('location_dest_id','=',location_dest_id),
                                                      ('date','>=',date_start),('date','<=',date_stop),
                                                      ('product_id','=',this.product_id.id),
                                                      ('queue','!=','entries')], order ="date")
        else:
            outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
                                                      ('state','=','done'),('location_dest_id','=',location_dest_id),
                                                      ('date','>=',date_start),('date','<=',date_stop),
                                                      ], order ="date")
        
        res =[]
        for outgoing in outgoing_ids:
            outgoing.queue ='draft'
            res.append(outgoing.id)
            outgoing.price_unit = 0
            outgoing.price_subtotal =0
        if res:
            self.fifo_reopen_fifo(res)
            
        
        this.write({'fifo_ids':[[6,0,res]]})
    
    
    @api.multi
    def button_fifo(self):
        
        for outgoing in self.fifo_ids:
            outgoing.queue = 'queue'
        
        self.state = 'queue'
            
    @api.multi
    def validate_fifo(self,move_line):
        outgoing =move_line
            
        outgoing.refresh()
        if outgoing.fifo_out:
            return
        while(not outgoing.fifo_out):
            if outgoing.fifo_out:
                continue
              
            incoming_ids = self.env['stock.move'].search([('location_id','!=',move_line.location_id.id),
                    ('location_dest_id','=',move_line.location_id.id),
                    ('state','=','done'),
                    ('product_id','=',outgoing.product_id.id)], order ="date,id")
            
            incoming_idss =[]
            for x in incoming_ids:
                if x.fifo == False:
                    incoming_idss.append(x)
                else:
                    x.state_queue = 'entries'
                      
            if incoming_idss:
                for incoming in incoming_idss:
                    incoming.refresh()
                    if outgoing.fifo_out == True:
                        outgoing.state_queue = 'entries'
                        break
                    if incoming.fifo == True:
                        incoming.state_queue = 'entries'
                        continue
                    fifo = outgoing.qty_out_unfifo - incoming.unfifo_qty
                    #Kiet: Truong hop số lượng stock move lớn hơn lượng cần FIFO outgoing.unfifo_qty 
                    if fifo >0:
                        incoming.state_queue = 'entries'
                        qty_fifo = incoming.unfifo_qty
                    else:
                        qty_fifo = outgoing.qty_out_unfifo
                    if incoming.id and outgoing.id:
                        val ={
                              'fifo_id':incoming.id,
                              'product_qty':qty_fifo,
                              'fifo_out_id':outgoing.id,
                              'out_qty':qty_fifo
                        }
                        self.env['stock.move.fifo'].create(val)
                    incoming.refresh()
                    outgoing.refresh()
            else:
                break
                    
        return  True
    
    def _prepare_account_move_line(self,line, qty,amount , debit_account_id, credit_account_id):
        debit = credit = amount
        
        ##PARTNER Nedbv
        res_company_id = self.env['res.partner'].search([('name','=','NEDCOFFEE BV')])
        
        if res_company_id:
            partner_id = res_company_id.id
        else:
            partner_id = line.picking_id and line.picking_id.partner_id and line.picking_id.partner_id.id or False
        #name =''
#         if line.picking_id:
#             name = line.picking_id.origin + ' - ' +line.product_id.default_code
#         else:

        name = line.product_id.default_code
        if line.picking_id:
            name += '-' + line.picking_id.name
            
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
    
    
    def _get_accounting_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        
        acc_src = accounts['stock_output'].id
        
        if line.location_id.code in ('NVP - BMT','Vinacafe - NVP') and line.location_dest_id.code == 'HCM':
            acc_dest = accounts.get('stock_valuation', False)
            acc_dest = acc_dest and acc_dest.id or False
            
        acc_dest = accounts.get('cogs_export', False) 
        
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest
    
    
    def get_entries_gdn_fifo(self,move_line_ids,debit_acc,credit_acc,amount):
        move_obj = self.env['account.move']
        move_lines =[]
        
        if amount and amount !=0:
            
            journal_id,  acc_dest , acc_src  = self._get_accounting_data(move_line_ids)
            
            move_lines = self._prepare_account_move_line(move_line_ids, move_line_ids.product_qty ,amount , debit_acc,credit_acc)
            if move_lines:
                warehouse_id = move_line_ids.picking_id and move_line_ids.picking_id.warehouse_id.id or 1
                ref = move_line_ids.picking_id.name
                if move_line_ids.picking_id.origin:
                    ref += '- ' + move_line_ids.picking_id.origin
                date = move_line_ids.date
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'warehouse_id':warehouse_id,
                                      'ref': ref,
                                      'narration':False})
                new_move_id.post()
                move_line_ids.entries_id = new_move_id.id
                return amount
        
    @api.multi
    def button_entries_fifo(self):
        for move in self.fifo_ids:
            if move.qty_out_fifo  == move.product_uom_qty:
                if move.entries_id:
                    continue
                self.get_entries_gdn_fifo(move)
        return
    
class ProductionAnalysis(models.Model):
    _inherit = "production.analysis"

    premium_id = fields.Many2one('mrp.bom.premium', 'Premium')
    bom_id = fields.Many2one('mrp.bom', 'Bom')
    
    @api.multi
    def load_data(self):
        for this in self:
            product_nvl_ids=[]
            product_tp_ids=[]
            prod_pl = nvl_net__qty = nvl_basis_qty = 0
            
            sql ='''
                SELECT  sum(total_init_qty) net_qty,sum(total_qty) basis_qty 
                FROM stock_picking  sp
                    WHERE production_id = %s
                        and picking_type_code in ('production_out')
                        and state ='done'
                    GROUP By picking_type_code,product_id
            '''%(this.production_id.id)
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                nvl_net__qty = i['net_qty'] or 0.0
                nvl_basis_qty = i['basis_qty'] or 0.0
            
            sql ='''
                DELETE FROM production_analysis_line_input;
                DELETE FROM production_analysis_line_output;
                DELETE FROM production_analysis_line;
                
                SELECT  picking_type_code,product_id, sum(total_init_qty) net_qty,sum(total_qty) basis_qty 
                FROM stock_picking  sp
                    WHERE production_id = %s
                        and picking_type_code in ('production_in','production_out')
                        and state ='done'
                    GROUP By picking_type_code,product_id
            '''%(this.production_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                premium = 0
                sql ='''
                    SELECT line.*
                    FROM  mrp_bom_premium  pre join mrp_bom_premium_line line on pre.id = line.prem_id
                    WHERE pre.active = true
                    and line.product_id = %s
                    and pre.id = %s
                    limit 1
                '''%(line['product_id'],this.premium_id.id)
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    premium = j['premium']
                
                bom_tp = 0
                sql ='''
                    SELECT line.*
                    FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                        join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id
                    WHERE bom.id = %s and line.product_id = %s
                '''%(this.bom_id.id,line['product_id'])
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    bom_tp = j['off_topic']
                
                mc = belowsc12 = screen13 = screen16 = screen18 = fm = black = brown = broken = 0.0
                count = 0
                if line['picking_type_code'] != 'production_out':
                    sql ='''
                        SELECT sp.total_init_qty npe_qty, qc.*
                        FROM stock_picking  sp join request_kcs_line qc on sp.id = qc.picking_id
                            WHERE sp.production_id = %s
                                and sp.picking_type_code ='%s'
                                and sp.state ='done'
                                and sp.product_id = %s
                    '''%(this.production_id.id,line['picking_type_code'],line['product_id'])
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        mc += i['mc'] * i['npe_qty'] or 0.0
                        fm += i['fm'] * i['npe_qty'] or 0.0
                        black += i['black'] * i['npe_qty'] or 0.0
                        broken += i['broken'] * i['npe_qty'] or 0.0
                        brown +=  i['brown'] * i['npe_qty'] or 0.0
                        screen18 += i['screen18'] * i['npe_qty'] or 0.0
                        screen16 += i['screen16'] * i['npe_qty'] or 0.0
                        screen13 += i['screen13'] * i['npe_qty'] or 0.0
                        belowsc12 += i['belowsc12'] * i['npe_qty'] or 0.0
                        count += i['npe_qty']
                    
                    actual = nvl_basis_qty and line['basis_qty'] / nvl_basis_qty or 0.0
                    var_usd = (this.cost_of_purchases + premium) * (actual*100 - bom_tp) * nvl_basis_qty /1000
                    var_usd = var_usd /100
                    prod_pl += var_usd
                    val ={
                          'analysis_id':this.id,
                          'product_id':line['product_id'],
                          'net_qty':line['net_qty'],
                          'basis_qty':line['basis_qty'],
                          'mc':count and mc/count or 0.0,
                          'fm':count and fm/count or 0.0, 
                          'black':count and black/count or 0.0, 
                          'broken':count and broken/count or 0.0, 
                          'brown':count and brown/count or 0.0, 
                          'screen18':count and screen18/count or 0.0, 
                          'screen16':count and screen16/count or 0.0, 
                          'screen13':count and screen13/count or 0.0, 
                          'screen12':count and belowsc12/count or 0.0, 
                          'actual':actual * 100,
                          'premium':premium,
                          'bom':bom_tp,
                          'var': actual * 100 - bom_tp,
                          'var_usd':var_usd
                          }
                    self.env['production.analysis.line.output'].create(val)
                    if line['product_id'] not in product_tp_ids:
                        product_tp_ids.append(line['product_id'])
                else:
                    bom_nvl = 0
                    actual = nvl_basis_qty and line['basis_qty'] / nvl_basis_qty or 0.0
                    sql ='''
                        SELECT line.*
                        FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                            join mrp_bom_stage_material_line line on stage.id = line.bom_stage_line_id
                        WHERE bom.id = %s and line.product_id = %s
                    '''%(this.bom_id.id,line['product_id'])
                    self.env.cr.execute(sql)
                    for j in self.env.cr.dictfetchall():
                        bom_nvl = j['off_topic']
                    sql ='''
                        SELECT sp.total_init_qty npe_qty, stack.*
                        FROM stock_picking  sp join stock_stack stack on sp.stack_id = stack.id
                            WHERE sp.production_id = %s
                                and picking_type_code ='%s'
                                and sp.state ='done'
                                and sp.product_id = %s
                    '''%(this.production_id.id,line['picking_type_code'],line['product_id'])
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        mc += i['mc'] * i['npe_qty'] or 0.0
                        fm += i['fm'] * i['npe_qty'] or 0.0
                        black += i['black'] * i['npe_qty'] or 0.0
                        broken += i['broken'] * i['npe_qty'] or 0.0
                        brown +=  i['brown'] * i['npe_qty'] or 0.0
                        screen18 += i['screen18'] * i['npe_qty'] or 0.0
                        screen16 += i['screen16'] * i['npe_qty'] or 0.0
                        screen13 += i['screen13'] * i['npe_qty'] or 0.0
                        belowsc12 += i['screen12'] * i['npe_qty'] or 0.0
                        count += i['npe_qty']
                    
                    
                    actual_nvl = nvl_basis_qty and line['basis_qty'] / nvl_basis_qty or 0.0
                    var_usd = (this.cost_of_purchases + premium) * (actual*100 - bom_tp) * nvl_basis_qty /1000
                    var_usd = var_usd /100
                    prod_pl += var_usd
                    
                    val ={
                          'analysis_id':this.id,
                          'product_id':line['product_id'],
                          'net_qty':line['net_qty'],
                          'basis_qty':line['basis_qty'],
                          'mc':count and mc/count or 0.0,
                          'fm':count and fm/count or 0.0,
                          'black':count and black/count or 0.0, 
                          'broken':count and broken/count or 0.0, 
                          'brown':count and brown/count or 0.0, 
                          'screen18':count and screen18/count or 0.0, 
                          'screen16':count and screen16/count or 0.0, 
                          'screen13':count and screen13/count or 0.0, 
                          'screen12':count and belowsc12/count or 0.0, 
                          'premium':premium,
                          'bom':bom_nvl,
                          'actual':actual_nvl * 100,
                          'var': actual_nvl * 100 - bom_nvl,
                          'var_usd':var_usd
                    }
                    
                    analysis = self.env['production.analysis.line.input'].create(val)
                    if line['product_id'] not in product_nvl_ids:
                        product_nvl_ids.append(line['product_id'])
                
            this.refresh()
           
            #kiet: Thanh pham vao truoc
            sql ='''
                SELECT line.*
                FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                    join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id
                WHERE bom.id = %s and line.product_id not in (%s)
            '''%(this.production_id.bom_id.id,','.join(map(str, product_tp_ids)))
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                var_usd = (this.cost_of_purchases + premium) * (0 - j['off_topic']) * nvl_basis_qty /1000
                var_usd = var_usd /100
                val ={
                  'analysis_id':this.id,
                  'product_id':j['product_id'],
                  'net_qty':0,
                  'basis_qty':0,
                  'mc': 0.0,
                  'fm': 0.0,
                  'black': 0.0, 
                  'broken': 0.0, 
                  'brown': 0.0, 
                  'screen18': 0.0, 
                  'screen16': 0.0, 
                  'screen13': 0.0, 
                  'screen12': 0.0, 
                  'premium':premium,
                  'bom':j['off_topic'],
                  'actual':0,
                  'var': 0- j['off_topic'],
                  'var_usd':var_usd
                }
                prod_pl += var_usd
                analysis = self.env['production.analysis.line.output'].create(val)
            
            #kiet: NVL
            sql ='''
                SELECT line.*
                FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                    join mrp_bom_stage_material_line line on stage.id = line.bom_stage_line_id
                WHERE bom.id = %s and line.product_id not in (%s)
            '''%(this.bom_id.id,','.join(map(str, product_nvl_ids)))
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                var_usd = (this.cost_of_purchases + premium) * (0 - j['off_topic']) * nvl_basis_qty /1000
                var_usd = var_usd /100
                val ={
                      'analysis_id':this.id,
                      'product_id':j['product_id'],
                      'net_qty':0,
                      'basis_qty':0,
                      'mc':0.0,
                      'fm':0.0,
                      'black': 0.0, 
                      'broken':0.0, 
                      'brown': 0.0, 
                      'screen18': 0.0, 
                      'screen16':0.0, 
                      'screen13': 0.0, 
                      'screen12':0.0, 
                      'premium':premium,
                      'bom':j['off_topic'],
                      'actual':0,
                      'var': 0 - bom_nvl,
                      'var_usd':var_usd
                    }
                prod_pl += var_usd
                analysis = self.env['production.analysis.line.input'].create(val)
                        
                        
            this.prod_pl= prod_pl/ (nvl_basis_qty/1000)
            
            this.refresh()
            #Tao summary
            for loop in (1,2,3):
                total = 0.0
                bom = 0
                sql ='''
                    SELECT line.*
                    FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                        join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                    WHERE bom.id = %s and line.product_id = 1175
                '''%(this.bom_id.id,)
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    #kiet: Code lay Drying loss
                    bom = j['off_topic']
                
                if loop == 1:
                    in_avg_mc = net_qty  =0
                    for input in this.input_ids:
                        in_avg_mc += input.net_qty * input.mc
                        net_qty += input.net_qty
                    #Kiet Bình quân in
                    in_avg_mc = round(in_avg_mc/ net_qty,1)
                    
                    out_avg_mc = net_qty =0
                    for output in this.output_ids:
                        net_qty += output.net_qty
                        out_avg_mc += output.net_qty * output.mc
                    #Kiet: Bình quân Out
                    out_avg_mc = round(out_avg_mc/ net_qty,1)
                    
                    wloss = this.input_basis_qty * (1-((1- in_avg_mc/100)/(1- out_avg_mc/100)))
                    actual = this.input_basis_qty and wloss/ this.input_basis_qty or 0.0
                    vals ={
                    'basis':wloss,
                    'name':   'MC loss',
                    'bom':bom,
                    'analysis_id':this.id,
                    'actual':actual or 0.0,
                    'var':(actual - bom) or 0.0
                    }
                    self.env['production.analysis.line'].create(vals)
                    total += wloss
                
                if loop == 2:
                    sql ='''
                        SELECT  pp.id product_id, pp.default_code, sum(total_qty) basis_qty 
                            FROM stock_picking  sp join product_product pp on sp.product_id = pp.id
                                join product_template pt on pp.product_tmpl_id = pt.id
                                join product_category pc on pt.categ_id = pc.id
                                WHERE production_id = %s
                                    and picking_type_code in ('production_in')
                                    and sp.state ='done'
                                    and pc.code in ('Reject')
                                GROUP By pp.id,pp.default_code
                        '''%(this.production_id.id)
                    self.env.cr.execute(sql)
                    for k in self.env.cr.dictfetchall():
                        bom = 0
                        sql ='''
                            SELECT line.off_topic
                            FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                                join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                            WHERE bom.id = %s and line.product_id = %s
                            LIMIT 1
                        '''%(this.production_id.bom_id.id,k['product_id'])
                        self.env.cr.execute(sql)
                        for j in self.env.cr.dictfetchall():
                            #kiet: Code lay Drying loss
                            bom = j['off_topic']
                        
                        actual = this.input_basis_qty and k['basis_qty']/ this.input_basis_qty or 0.0
                            
                        premium = 0
                        vals ={
                        'name':   k['default_code'],
                        'bom':bom,
                        'basis':k['basis_qty'],
                        'actual':actual,
                        'var':(actual - bom) or 0.0,
                        'analysis_id':this.id
                        }
                        self.env['production.analysis.line'].create(vals)
                        total += k['basis_qty']
                
                if loop == 3:
                    bom = 0
                    sql ='''
                        SELECT line.*
                        FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                            join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                        WHERE bom.id = %s and line.product_id = 1373
                    '''%(this.production_id.bom_id.id)
                    self.env.cr.execute(sql)
                    for j in self.env.cr.dictfetchall():
                        #kiet: Code lay Drying loss
                        bom = j['off_topic']
                    
                    basis = this.input_basis_qty - this.output_product_received - total
                    actual = this.input_basis_qty and basis/ this.input_basis_qty or 0.0
                    
                    vals ={
                    'name':   'Invisible loss',
                    'bom':bom,
                    'basis':basis,
                    'analysis_id':this.id,
                    'actual':actual or 0.0,
                    'var':(actual - bom) or 0.0
                    }
                    self.env['production.analysis.line'].create(vals)
                    
            return
    
class FifoOperation(models.Model):
    _name ='fifo.operation'
    
    
    
    
class StockMoveFifo(models.Model):
    _name= 'stock.move.fifo'
    _description = 'Stock Move Fifo'
    _order = 'id desc'
    
    fifo_id = fields.Many2one('stock.move', string='FIFO', required=False,ondelete='cascade')
    product_id = fields.Many2one('product.product', related='fifo_id.product_id',string="Product", store=True)
    price_unit = fields.Float(related='fifo_id.price_unit',string="Price unit", store=True, group_operator="avg",)
    
    product_qty = fields.Float(string="Product qty")
    fifo_colletion_id = fields.Many2one('stock.move.allocation', string='Move Allocation', required=False,ondelete='cascade')
    out_qty = fields.Float(string="Out qty")
    fifo_out_id = fields.Many2one('stock.move', string='Move Allocation', required=False, ondelete='cascade')
    
#     fifo_hcm_id = fields.Many2one('stock.move', string='FIFO', required=False,ondelete='cascade')
#     product_hcm_qty =fields.Float(string="Product HCM qty")
#     fifo_cus_id = fields.Many2one('stock.move', string='Move Allocation', required=False, ondelete='cascade')
#     product_cus_qty =fields.Float(string="Product Cus qty")
    
    

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    fifo_management_id = fields.Many2one('report.fifo.management',string="TP")
    
class StockMove(models.Model):
    _inherit = "stock.move"
    
    def compute_fifo(self):
        for order in self:
            price_out_fifo = fifo_qty_out = fifo_qty = 0.0
            for fifo in order.fifo_ids:
                fifo_qty += fifo.product_qty
            
            for fifo in order.fifo_out_ids:
                fifo_qty_out += fifo.out_qty
                price_out_fifo += fifo.out_qty * fifo.fifo_id.price_unit
                
            if order.product_uom_qty == fifo_qty:
                order.fifo = True
            else:
                order.fifo = False
            
            if order.product_uom_qty == fifo_qty_out:
                order.fifo_out = True
            else:
                order.fifo_out = False
            
            order.fifo_qty = fifo_qty
            order.unfifo_qty = order.product_uom_qty - fifo_qty
            
            order.qty_out_fifo = fifo_qty_out
            order.qty_out_unfifo = order.product_uom_qty - fifo_qty_out
            order.price_out_fifo = price_out_fifo
            
#             for fifo in order.fifo_hcm_ids:
#                 product_hcm_qty += fifo.product_hcm_qty
#             
#             for fifo in order.fifo_cus_ids:
#                 product_cus_qty += fifo.product_cus_qty
#                 price_cus_fifo += fifo.product_cus_qty * fifo.fifo_hcm_id.price_unit
#                 
#             if order.product_uom_qty == product_hcm_qty:
#                 order.fifo_hcm = True
#             else:
#                 order.fifo_hcm = False
#             
#             if order.product_uom_qty == product_cus_qty:
#                 order.fifo_cus = True
#             else:
#                 order.fifo_cus = False
#             
#             order.fifo_hcm_qty = product_hcm_qty
#             order.unfifo_hcm_qty = order.product_uom_qty - product_hcm_qty
#             
#             order.qty_cus_out_fifo = product_cus_qty
#             order.qty_cus_out_unfifo = order.product_uom_qty - product_cus_qty
#             order.price_cus_fifo = price_cus_fifo
            
    
    fifo_ids = fields.One2many('stock.move.fifo','fifo_id', string='FIFO', required=False)
    fifo = fields.Boolean(string='Allocated',compute="compute_fifo", default=False,store= False)
    
    fifo_qty = fields.Float(string='Fifo Qty',compute="compute_fifo", default=False,store= False)
    unfifo_qty = fields.Float(string='UnFifo Qty',compute="compute_fifo", default=False,store= False)
    
    fifo_out_ids = fields.One2many('stock.move.fifo','fifo_out_id', string='FIFO', required=False)    
    fifo_out = fields.Boolean(string='FIfo',compute="compute_fifo", store= False)    
    qty_out_fifo =fields.Float(string='Fifo Out Qty',compute="compute_fifo", )
    price_out_fifo = fields.Float(string='Amount',compute="compute_fifo", )
    qty_out_unfifo = fields.Float(string='UnFifo Out Qty',compute="compute_fifo",)
    
    consumed_id = fields.Many2one('mrp.periodical.production.costing',string="NVL")
    produced_id = fields.Many2one('mrp.periodical.production.costing',string="TP")
    
    queue = fields.Selection([
        ('draft','Draft'),
        ('queue','Queue'),
        ('entries','Entries'),
        ],'Status', select=True, readonly=True,default='draft')
    
    
    
    
#     fifo_hcm_ids = fields.One2many('stock.move.fifo','fifo_hcm_id', string='FIFO HCM', required=False)
#     fifo_hcm = fields.Boolean(string='FIfo',compute="compute_fifo", default=False,store= False)
#     fifo_hcm_qty = fields.Float(string='Fifo Qty',compute="compute_fifo", default=False,store= False)
#     unfifo_hcm_qty = fields.Float(string='UnFifo Qty',compute="compute_fifo", default=False,store= False)
#     
    
#     fifo_cus_ids = fields.One2many('stock.move.fifo','fifo_cus_id', string='FIFO Customer', required=False)    
#     fifo_cus = fields.Boolean(string='FIfo',compute="compute_fifo", store= False)    
    #qty_cus_out_fifo =fields.Float(string='Fifo Customer Qty',compute="compute_fifo", )
#     qty_cus_out_unfifo = fields.Float(string='UnFifo Cus Out Qty',compute="compute_fifo",)
#     price_cus_fifo = fields.Float(string='Amount Customer',compute="compute_fifo", )
    
    
    
    
class MrpBomPremium(models.Model):
    _name= 'mrp.bom.premium'
    _description = 'Mrp Bom Premium'
    _order = 'id desc'
    
    name = fields.Char(string="Name", required=True)
    crop_id = fields.Many2one('ned.crop', string='Crop', required=False)
    active = fields.Boolean(string="Active",default="active")
    prem_ids = fields.One2many('mrp.bom.premium.line','prem_id', string='Crop', required=False)
    file = fields.Binary('File', help='Choose file Excel')
    file_name =  fields.Char('Filename', readonly=True)
    standard_cost = fields.Monetary(string='Standard Cost',currency_field='com_currency_id', default=16.35)
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    com_currency_id = fields.Many2one('res.currency', related='company_id.currency_id',string="Currency", readonly=True)
    bom_id = fields.Many2one('mrp.bom', string='Bom', required=False)
    
    @api.multi
    def import_file(self):
        flag = False
        for this in self:
            sql ='''
                DELETE FROM  Mrp_Bom_Premium_Line where prem_id = %s
            '''%(this.id)
            self.env.cr.execute(sql)
            
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(_('Warning !!!'))
            if sh:
                for row in range(sh.nrows):
                    if row > 0:
                        product_code = sh.cell(row,1).value or False
                        if not product_code:
                            continue
                        if product_code =='QualityCode':
                            flag =True
                            continue
                            
                        if flag:
                            premium = sh.cell(row,16).value or 0.0
                            if isinstance(premium, float):
                                premium = float(premium)
                                premium = round(premium,0)
                                premium = str(premium)
                            product_id = self.env['product.product'].search([('default_code','=', product_code)],limit =1)
                            if not product_id:
                                print product_code
                                continue
                            product_uom = self.env['product.uom'].search([('name','=', 'kg')],limit =1)
                            try:
                                self.env['mrp.bom.premium.line'].create({'prem_id':this.id,'product_id':product_id.id,'product_uom':product_uom.id,'premium':premium})
                            except Exception, e:
                                raise UserError(_('Warning !!!'))
                            
    
class MrpBomPremiumLine(models.Model):
    _name= 'mrp.bom.premium.line'
    _description = 'Mrp Bom Premium Line'
    _order = 'id desc'
    
    prem_id = fields.Many2one('mrp.bom.premium', required=False)
    product_id = fields.Many2one('product.product',string="Product", required=True)
    product_uom = fields.Many2one('product.uom',string="UoM", required=True)
    premium = fields.Float(string='Prem/Disct')
    mc = fields.Float(string='MC')
    fm = fields.Float(string='FM')
    black = fields.Float(string='Black')
    broken = fields.Float(string='Broken')
    brown = fields.Float(string='Brown')
    mold = fields.Float(string='Mold')
    cherry = fields.Float(string='Cherry')
    excelsa = fields.Float(string='Excelsa')
    screen18 = fields.Float(string='Screen18')
    screen16 = fields.Float(string='Screen16')
    screen13 = fields.Float(string='Screen13')
    belowsc12 = fields.Float(string='Below12')
    burned = fields.Float(string='Burned')
    eaten = fields.Float(string='Eaten')
    immature = fields.Float(string='Immature')
    
    flag = fields.Boolean(string='Flag',default=False)


class CostingPremiumLine(models.Model):
    _name= 'costing.premium.line'
    _description = 'Costing Premium Line'  
    _order = 'id desc'
    
    collection_id = fields.Many2one('mrp.periodical.production.costing',string="Premium", required=False,ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product',string="Product", required=True)
    product_uom = fields.Many2one('product.uom',related='product_id.uom_id',string="UoM", required=False)
    
    premium = fields.Float(string='Prem/Disct')
    #price = fields.Monetary(string='Price',currency_field='company_currency_id')
    price = fields.Float(string='Price',digits=(12, 9))
    value = fields.Monetary(string='Value', compute="compute_values", currency_field='company_currency_id')
    #value = fields.Float(string='Value', compute="compute_values",digits=(12, 4))
    flag= fields.Boolean(string="Flag", default=False)
    
    cost_collection_id = fields.Many2one('mrp.production.order.cost.collection',string="Premium", required=False,ondelete='cascade', index=True)
    
    
    @api.depends('product_qty','value')
    def compute_values(self):
        for order in self:
            order.value = order.product_qty * order.price
    
    company_currency_id = fields.Many2one('res.currency', related='collection_id.company_currency_id', readonly=True)
    
    
#     @api.depends('product_qty','collection_id','product_id')
#     def _compute_qty(self):
#         for order in self:
#             produced_qty = 0.0
#             fin_id = self.env['mo.direct.cost.collection'].search([('cost_id','=',order.collection_id.id),('product_id','=',order.product_id.id)])
#             if fin_id:
#                 produced_qty = fin_id.produced_qty
#             else:
#                 produced_qty = 0.0
#             ma_id = self.env['cost.materials.collection'].search([('cost_id','=',order.collection_id.id),('product_id','=',order.product_id.id)])
#             if ma_id:
#                 produced_qty = produced_qty - ma_id.product_qty
#             
#             order.product_qty = produced_qty
                
    product_qty = fields.Float(string = 'Product Qty' ,digits=(12, 0))
    
    
class MrpPeriodicalProductionCosting(models.Model):
    _name= 'mrp.periodical.production.costing'
    _description = 'Periodical Production Costing'
    _order = 'id desc'
    
    name = fields.Many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]})
    notes = fields.Text(string="Notes")
    production_order_ids = fields.Many2many('mrp.production', 'mo_periodical_production_costing_rel', 'periodical_costing_id', 'production_id', 'Production orders', required=False)
    #Thanh: Related Production Order Allocation
    mo_cost_collection_lines = fields.One2many('mrp.production.order.cost.collection', 'periodical_costing_id', 'Production Orders', readonly=True)
    premium_ids =fields.One2many('costing.premium.line', 'collection_id', 'Premium Orders', readonly=False)
    #Thanh: Group Factory Overhead Control
    #periodical_overhead_lines = fields.One2many('periodical.overhead', 'periodical_costing_id', 'Overhead Details'),
    
    premium_id = fields.Many2one('mrp.bom.premium', 'Premium', required=True, readonly=True, states={'draft':[('readonly',False)]})
    
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted'),
        ('done','Done'),
        ('cancel','Cancelled'),
        ],'Status', select=True, readonly=True,default='draft')
    
    date_end = fields.Date(related='name.date_stop', readonly=True)
    
    #kiet: moi them
    direct_cost_lines = fields.One2many('mo.direct.cost.collection', 'cost_id', 'Direct costs', readonly=True)
    direct_materials_ids = fields.One2many('cost.materials.collection','cost_id',string='Direct Materials')
    direct_cost_ids = fields.One2many('mo.cost.direct', 'cost_id', 'Direct costs', readonly=True)
    
    file = fields.Binary('File', help='Choose file Excel')
    file_name =  fields.Char('Filename', readonly=True)
    consumed_products_ids = fields.One2many('stock.move', 'consumed_id', 'Consumed Products', readonly=True)
    produced_products_ids = fields.One2many('stock.move', 'produced_id', 'Produced Products', readonly=True)
    
    
    @api.multi
    def dieuchinh_values(self):
        for this in self:
                
            for move in this.consumed_products_ids:
                move.entries_id.button_cancel()
                move.entries_id.unlink()
                move.state = 'draft'
                move.unlink()
#             
                 
                    
    
    def fifo_reopen_fifo(self,move_ids):
        for move in self.env['stock.move'].browse(move_ids):
            move.remove_fifo()
            
    
        
    @api.multi
    def post_done(self):
#         for line in self.consumed_products_ids:
#             if not line.entries_id:
#                 self.get_entries(line)
        
        for line in self.produced_products_ids:
            if not line.entries_id:
                self.get_entries(line)
#             if line.entries_id:
#                 line.entries_id.button_cancel()
#                 line.entries_id.unlink()

    @api.multi
    def cancel(self):
        for this in self:
            for input in this.consumed_products_ids:
                if input.entries_id:
                    input.entries_id.button_cancel()
                    input.entries_id.unlink()
                input.action_cancel()
                input.unlink()
            
            for output in this.produced_products_ids:
                if output.entries_id:
                    output.entries_id.button_cancel()
                    output.entries_id.unlink()
                output.action_cancel()
                output.unlink()
        
    @api.multi
    def fifo_nvl(self):
        for this in self.direct_materials_ids:
            this.fifo_nvl()
        return 1
    
    @api.multi
    def import_price(self):
        for this in self:
            flag= False
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(_('Warning !!!'))
            if sh:
                for row in range(sh.nrows):
                    if not flag:
                        flag= True
                        continue
                    
                    in_product_code = sh.cell(row,0).value or False
                    in_qty = sh.cell(row,1).value or False
                    out_product_code = sh.cell(row,2).value or False
                    out_qty = sh.cell(row,3).value or False
                    price = sh.cell(row,4).value or False
                    
                    in_product = self.env['product.product'].search([('default_code','=',in_product_code)])
                    if in_product and in_qty and in_qty !=0:
                        material = self.env['cost.materials.collection'].search([('product_id','=', in_product.id),('cost_id','=', this.id)],limit =1)
                        if material:
                            material.write({'fifo_net_qty':in_qty})
                        else:
                            var ={
                                'cost_id':this.id,
                                'product_id':in_product.id,
                                'state': 'draft',
                                'fifo_net_qty':in_qty
                            }
                            self.env['cost.materials.collection'].create(var)
                            
                    out_product = self.env['product.product'].search([('default_code','=',out_product_code)])
                    if out_product and out_qty and out_qty !=0:
                        premium = self.env['costing.premium.line'].search([('product_id','=', in_product.id),('collection_id','=', this.id)],limit =1)
                        if premium:
                            premium.write({'product_qty':out_qty,'price':price/1000})
                        else:
                            val ={
                                'collection_id':this.id,
                                'product_id':out_product.id,
                                'product_qty':out_qty,
                                'price':round(price/1000,5)
                                #'price':prem.premium +premium_id.premium
                                }
                            self.env['costing.premium.line'].create(val)
                    
    
    
    @api.depends('mo_cost_collection_lines')
    def compute_qty(self):
        for order in self:
            total_cost = 0.0
            for line in order.direct_materials_ids:
                total_cost += line.amount_fifo_qty or 0.0
            order.total_cost = total_cost
            
    total_cost = fields.Monetary(string = 'Total Cost',compute='compute_qty',currency_field ='company_currency_id')
    
    #total_cost = fields.Monetary(string = 'Total Cost',currency_field ='company_currency_id')
    
    company_id = fields.Many2one('res.company', string='Company', 
        required=False, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('mrp.periodical.production.costing'))
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    second_currency_id = fields.Many2one('res.currency', related='company_id.second_currency_id', readonly=True)
    
    @api.multi
    def printf_mo(self):
        return {
            'type': 'ir.actions.report.xml',
            'report_name':'report_cost_productions'
        }
        
    
    def _get_accounting_data(self, line):
        product_obj = self.env['product.template']
        accounts = product_obj.browse(line.product_id.product_tmpl_id.id).get_product_accounts()
        acc_valuation = accounts.get('stock_valuation', False)
        #Kiệt: Trường hợp xuất kho NVL
        if line.location_id.usage =='internal' and line.location_dest_id.usage == 'production':
            acc_dest = line.location_dest_id.valuation_in_account_id.id
            acc_src =  acc_valuation.id
        
        #Kiet: Trượng hợp nhập kho Thành phẩm
        if line.location_id.usage =='production' and line.location_dest_id.usage == 'internal':
            #Kiet: Nhập kho sản xuất 
            acc_dest = acc_valuation.id
            acc_src = line.location_id.valuation_out_account_id.id
            
        if not accounts.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts'))
        journal_id = accounts['stock_journal'].id
        return journal_id, acc_src, acc_dest
    
    
    def _prepare_account_move_line(self,line, qty,  credit_account_id, debit_account_id):
        debit = credit = line.price_unit * qty
        partner_id = (line.picking_id.partner_id and self.pool.get('res.partner')._find_accounting_partner(line.picking_id.partner_id).id) or False
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
    def get_entries(self,move_line):
        move_obj = self.env['account.move']
        
        journal_id, acc_src, acc_dest = self._get_accounting_data(move_line)
        move_lines = self._prepare_account_move_line(move_line, move_line.product_qty,  acc_src, acc_dest)
        ref = u'Giá thành ' + self.name.name 
        if move_lines:
            date = move_line.date
            new_move_id = move_obj.create({'journal_id': journal_id,
                                  'line_ids': move_lines,
                                  'date': date,
                                  'ref': ref,
                                  'narration':False})
            new_move_id.post()
            move_line.entries_id = new_move_id.id
    
    
    @api.multi
    def post(self):
        for this in self:
            for line in this.produced_products_ids:
                if line.fifo_qty != 0:
                    raise
# #             
#             for line in this.consumed_products_ids:
#                 line.action_cancel()
#                 if line.entries_id:
#                     line.entries_id.button_cancel()
#                     line.entries_id.unlink()
#                 line.unlink()
#                     
#                 
#             for line in this.produced_products_ids:
#                 line.action_cancel()
#                 line.unlink()
                  
                  
            origin = u'Giá thành tháng ' + this.name.name
            location_id = self.env['stock.location'].search([('code','=','NVP - BMT')])
#             Thành phẩm
            for premium in self.premium_ids:
                if not premium.product_qty and not premium.price and premium.price ==0:
                    continue
                data = {
                        'product_uom_qty':premium.product_qty,
                        'price_unit':premium.price,
                        'location_id':premium.product_id.property_stock_production.id or False,
                        'name': premium.product_id.default_code,
                        'date': this.name.date_stop,
                        'product_id': premium.product_id.id,
                        'product_uom': premium.product_id.uom_id.id, 
                        'location_dest_id': location_id.id,
                        'company_id': this.company_id.id,
                        'origin': origin, 
                        'produced_id':this.id,
                        'state': 'done'}
                move_id = self.env['stock.move'].create(data)
                self.get_entries(move_id)
                   
                #Bút toán giá nhập kho
             
            #NVL tiêu thụ
            for materials in self.direct_materials_ids:
                if not materials.fifo_qty:
                    continue
                for allocation in materials.allocation_ids:
                    data = {
                            'product_uom_qty':allocation.allocated_qty,
                            'price_unit':allocation.allocated_value,
                            'location_id':location_id.id,
                            'name': materials.product_id.default_code, 
                            'date': this.name.date_stop,
                            'product_id': materials.product_id.id,
                            'product_uom': materials.product_id.uom_id.id, 
                            'location_dest_id': materials.product_id.property_stock_production.id or False, 
                            'company_id': this.company_id.id,
                            'origin': origin,
                            'consumed_id':this.id,
                            'state': 'done'}
                    move_id = self.env['stock.move'].create(data)
                    self.get_entries(move_id)
                    
                    move_fifo = self.env['stock.move.fifo'].search([('fifo_colletion_id','=',allocation.id)])
                    if move_fifo:
                        move_fifo.fifo_out_id = move_id.id
                    else:
                        val ={
                              'fifo_id':allocation.from_move_id.id,
                              'product_qty':allocation.allocated_qty,
                              'fifo_colletion_id':allocation.id,
                              'out_qty':allocation.allocated_qty,
                              'fifo_out_id':move_id.id
                        }
                        fifo_id = self.env['stock.move.fifo'].create(val)
            #Lien ket voi bang phan6 bo
#             for i in this.direct_materials_ids:
#                 for j in i.allocation_ids:
#                     move_id = self.env['stock.move'].search([('product_id','=',j.product_id.id),('price_unit','=',j.allocated_value),
#                                         ('consumed_id','=',this.id),('product_qty' ,'=',j.allocated_qty)])
#                     
#                     if len(move_id)>=2:
#                         move_idss =[]
#                         for kk in move_id:
#                             move_idss.append(kk.id)
#                         
#                         sql ='''
#                             select id from stock_move where id in (%s) and origin like '%s'
#                         '''%(','.join(map(str, move_idss)),j.from_origin)
#                         print sql
#                         self.env.cr.execute(sql)
#                         for iii in self.env.cr.dictfetchall():
#                             move_id = iii['id']
                    
            
            this.state = 'posted'
    @api.multi
    def compute_cost(self):
        for this in self:
            #Xoá data làm lại
            sql='''
                DELETE FROM mo_direct_cost_collection where cost_id = %s;
                DELETE FROM cost_materials_collection where cost_id = %s;
                DELETE FROM mo_cost_direct where cost_id = %s;
                DELETE FROM costing_premium_line where collection_id = %s
            '''%(this.id,this.id,this.id,this.id)
            self.env.cr.execute(sql)
            
        #kiet: Lấy Lệnh sản xuất:
            mrp_ids = []
            sql ='''
                SELECT id 
                FROM mrp_production 
                WHERE state ='done'
                    and date(timezone('UTC',date_planned::timestamp)) between '%s' and '%s'
            '''%(this.name.date_start,this.name.date_stop)
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                mrp_ids.append(i['id'])
            this.write({'production_order_ids':[[6,0,mrp_ids]]})
        #kiet: Lay thanh pham:
            sql ='''
                SELECT distinct product_id 
                FROM stock_move  sm 
                    join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'production'
                    join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'internal'
                where production_id in (%s)
                    and state ='done'
                    and product_uom_qty !=0
                    and init_qty !=0
            '''%(','.join(map(str, mrp_ids)))
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                var ={
                    'cost_id':this.id,
                    'product_id':i['product_id'],
                }
                new_id = self.env['mo.direct.cost.collection'].create(var)
                
        # Kiet Tong gop cac GRP
                sql='''
                    SELECT sm.id move_id
                    FROM stock_move  sm 
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'production'
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'internal'
                    where production_id in  (%s)
                        and state ='done'
                        and product_uom_qty !=0
                        and init_qty !=0
                        and product_id = %s
                '''%(','.join(map(str, mrp_ids)),i['product_id'])
                self.env.cr.execute(sql)
                for i in self.env.cr.dictfetchall():
                    varl ={
                        'move_id':i['move_id'],
                        'fin_id':new_id.id,
                    }
                    self.env['cost.finishs.details'].create(varl)
        
        #Kiet: Lay Nguyen vat lieu
            sql ='''
                SELECT distinct product_id 
                FROM stock_move  sm 
                    join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'internal'
                    join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'production' 
                where production_id in (%s)
                    and state ='done'
                    and product_uom_qty !=0
                    and init_qty !=0
            '''%(','.join(map(str, mrp_ids)))
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                var ={
                    'cost_id':this.id,
                    'product_id':i['product_id'],
                    'state': 'draft',
                }
                new_id = self.env['cost.materials.collection'].create(var)
                
                # Kiet Tong gop cac GIP
                sql='''
                    SELECT sm.id move_id
                    FROM stock_move  sm
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.usage = 'internal'
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.usage = 'internal' 
                    where production_id in  (%s)
                        and state ='done'
                        and product_uom_qty !=0
                        and init_qty !=0
                        and product_id = %s
                '''%(','.join(map(str, mrp_ids)),i['product_id'])
                self.env.cr.execute(sql)
                for i in self.env.cr.dictfetchall():
                    varl ={
                        'move_id':i['move_id'],
                        'material_id':new_id.id,
                    }
                    self.env['cost.materials.details'].create(varl)
                
                #new_id.fifo_allocation()
                
        
        #Kiet: Tạo bảng tính giá thành
            for prem in this.premium_id.prem_ids:
                this.standard_cost = this.premium_id.standard_cost or 0.0
                premium_id = self.env['mrp.bom.premium.line'].search([('flag','=',True)],limit=1)
                produced_qty = 0.0
                sql ='''
                    SELECT sum(produced_qty) produced_qty 
                    FROM mo_direct_cost_collection this where cost_id in (%s)
                    and product_id = %s
                    GROUP BY product_id
                    HAVING sum(produced_qty) >0
                '''%(this.id,prem.product_id.id)
                self.env.cr.execute(sql)
                for y in self.env.cr.dictfetchall():
                    produced_qty = y['produced_qty'] or 0.0
                    
                val ={
                    'collection_id':this.id,
                    'product_id':prem.product_id.id,
                    'product_qty':produced_qty,
                    'premium':prem.premium or 0.0,
                    #'price':prem.premium +premium_id.premium
                    }
                self.env['costing.premium.line'].create(val)
            
# 
class MrpProductionOrderCostCollection(models.Model):
    _name= 'mrp.production.order.cost.collection'
    _description = 'Production Order Cost Collection'
    _order = 'id desc'
 
    name = fields.Many2one('mrp.production', 'Production order', required=False )
    #warehouse_id = fields.Many2one(related='name.warehouse_id', string="Warehouse")
    
    period_id = fields.Many2one(related='periodical_costing_id.name', string="Period")
    warehouse_id = fields.Many2one(related='name.warehouse_id', string="Warehouse",store= True)
    date_finished = fields.Datetime(related='name.date_finished', string="Date Finished",store= True)
    
    direct_cost_lines = fields.One2many('mo.direct.cost.collection', 'cost_collection_id', 'Direct costs', readonly=True)
    direct_materials_ids = fields.One2many('cost.materials.collection','collection_id',string='Direct Materials')
    direct_cost_ids = fields.One2many('mo.cost.direct', 'collection_id', 'Direct costs', readonly=True)
#     overhead_absorbed_lines = fields.One2many('mo.overhead.absorbed', 'cost_collection_id', 'OH absorbed', readonly=True)
    periodical_costing_id = fields.Many2one('mrp.periodical.production.costing', 'Related Periodical Costing',ondelete='cascade')
    date_approve = fields.Date(string="Date Approve",default=fields.Datetime.now)
    state = fields.Selection([
        ('draft','Draft'),
        ('posted','Posted'),
        ('cancel','Cancelled'),
        ],'Status', select=True, readonly=True)
    
    company_currency_id = fields.Many2one('res.currency', related='periodical_costing_id.company_currency_id', readonly=True)
    premium_ids =fields.One2many('costing.premium.line', 'cost_collection_id', 'Premium Orders', readonly=False)
    
    @api.depends('direct_cost_ids','direct_materials_ids.value','direct_materials_ids','standard_cost')
    def _compute_values(self):
        for this in self:
            cost = 0
            product_qty = 0.0
            materials_cost = 0.0
            other_cost = 0.0
            for line in this.direct_materials_ids:
                cost += line.value
                materials_cost += line.value
                if line.product_id.flag_standard_cost:
                    product_qty += line.product_qty or 0.0
            
            for line in this.direct_cost_ids:
                cost +=  line.total_consume
                other_cost +=  line.total_consume
            
            standard_cost = this.standard_cost and this.standard_cost * product_qty /1000  or 0.0
            this.total_cost = cost + standard_cost
            this.materials_cost = materials_cost
            this.other_cost = other_cost
            
    total_cost = fields.Monetary(string='Total Cost',compute='_compute_values',store = True,currency_field='company_currency_id')
    currency_id = fields.Many2one('res.currency',default=3)
    
    standard_cost = fields.Monetary(string='Standard Cost',currency_field='company_currency_id', default=16.35)
    materials_cost = fields.Monetary(string='Material Cost',compute='_compute_values',store = True,currency_field='company_currency_id')
    other_cost = fields.Monetary(string='Other costs',compute='_compute_values',store = True,currency_field='company_currency_id')
    
    
    @api.multi
    def post(self):
        production_list =[]
        cost_collection_ids =[]
        for this in self:
            production_list.append(this.name.id) 
            cost_collection_ids.append(this.id)
        #Kiet:Update toan bo cac giao dich stock Move
        for line in self.premium_ids:
            price_currency = self.env.user.company_id.currency_id.with_context(date=self.date_approve).compute(line.price,self.env.user.company_id.second_currency_id)
            sql='''
            UPDATE stock_move SET price_unit= %s ,price_currency = %s
            WHERE id in (
                SELECT sm.id
                FROM stock_move sm 
                JOIN stock_location sl on sm.location_id = sl.id and sl.usage != 'internal'
                JOIN stock_location des on sm.location_dest_id = des.id and des.usage = 'internal'
                WHERE sm.production_id in (%s) 
                    AND sm.product_id = %s)
            '''%(line.price,price_currency,','.join(map(str, production_list)),line.product_id.id)
            self.env.cr.execute(sql)
            
            sql ='''
                UPDATE mo_direct_cost_collection
                SET price_unit = %s,price_subtotal =  %s * produced_qty
                WHERE
                    product_id = %s
                    and cost_collection_id in (%s)
            '''%(line.price,line.price,line.product_id.id,','.join(map(str, cost_collection_ids)))
            self.env.cr.execute(sql)
            
    @api.multi
    def compute_cost(self, context=None):
        for this in self:
            ## delete table material Labor Marchine
            sql='''
                DELETE FROM mo_direct_cost_collection where cost_collection_id = %s;
                DELETE FROM cost_materials_collection where collection_id = %s;
                DELETE FROM mo_cost_direct where collection_id = %s;
                DELETE FROM costing_premium_line where cost_collection_id = %s
            '''%(this.id,this.id,this.id,this.id)
            self.env.cr.execute(sql)
            # Fin good
            sql = '''
                SELECT mpwpp.product_uom,mpwpp.product_id,sum(mpwpp.product_qty) product_qty 
                FROM  mrp_production_workcenter_line mpwl join 
                    mrp_production_workcenter_product_produce mpwpp on mpwl.id = mpwpp.operation_id
                WHERE production_id = %s
                GROUP BY mpwpp.product_uom,mpwpp.product_id
                HAVING sum(mpwpp.product_qty) > 0
            '''%(this.name.id)
            self.env.cr.execute(sql)
            res = self.env.cr.dictfetchall()
            for res_line in res:
                var ={
                    'cost_collection_id':this.id,
                    'product_id':res_line['product_id'],
                    'product_uom_id':res_line['product_uom'],
                    'produced_qty':res_line['product_qty'],
                    'state': 'draft'
                    }
                self.env['mo.direct.cost.collection'].create(var)
            
            #material
            materials_id = False
            sql ='''
                SELECT distinct sm.product_id
                    FROM mrp_production_consumed_products_move_ids pref join stock_move sm
                        on pref.move_id = sm.id
                    WHERE pref.production_id = %s
            '''%(this.name.id)
            self.env.cr.execute(sql)
            for res_line in self.env.cr.dictfetchall():
                prod_obj = self.env['product.product'].browse(res_line['product_id'])
                var ={
                    'collection_id':this.id,
                    'product_id':prod_obj.id,
                    'product_uom':prod_obj.uom_id.id,
                    'theory_qty':0.0,
                    }
                materials_id = self.env['cost.materials.collection'].create(var)
            
            if materials_id:
                sql ='''
                    SELECT sm.id,sm.product_id,sm.product_uom, product_qty,sm.date
                    FROM mrp_production_consumed_products_move_ids pref join stock_move sm
                        on pref.move_id = sm.id
                    WHERE pref.production_id = %s
                    GROUP BY sm.product_id,product_uom,sm.id
                    order by sm.date desc
                ''' %(this.name.id)
                
                self.env.cr.execute(sql)
                for res_line in self.env.cr.dictfetchall():
                    allocation_id =[]
                    allocation_ids = self.env['stock.move.allocation'].search([('to_move_id','=',res_line['id'])])
                    values = 0.0
                    for allocation in allocation_ids:
                        values = values + allocation.allocated_value
                        allocation_id.append(allocation.id)
                    
                    if not materials_id:
                        raise
                    
                    var ={
                        'allocation_ids':[[6,0,allocation_id]],
                        'date':res_line['date'],
                        'material_id':materials_id.id,
                        'move_id':res_line['id'],
                        'product_id':res_line['product_id'],
                        'product_uom':res_line['product_uom'],
                        'product_qty':res_line['product_qty'],
                        'values': values
                    }
                    self.env['cost.materials.details'].create(var)
                    
                #Kiet: ADD NVL mất mát
                for res_line in self.name.move_loss_ids:
                    allocation_id =[]
                    allocation_ids = self.env['stock.move.allocation'].search([('to_move_id','=',res_line['id'])])
                    values = 0.0
                    for allocation in allocation_ids:
                        values = values + allocation.allocated_value
                        allocation_id.append(allocation.id)
                        
                    var ={
                        'allocation_ids':[[6,0,allocation_id]],
                        'date':res_line.date,
                        'material_id':materials_id.id,
                        'move_id':res_line.id,
                        'product_id':res_line.product_id.id,
                        'product_uom':res_line.product_uom.id,
                        'product_qty':res_line.product_qty,
                        'values': values
                    }
                    self.env['cost.materials.details'].create(var)
                    
            #Các chi phí khác
            nvl_consumed =0.0
            for consum in this.name.move_lines2:
                nvl_consumed += consum.product_qty or 0.0
            
            for consum in this.name.move_loss_ids:
                nvl_consumed += consum.product_qty or 0.0
                
            stack=[]
            for move_ids in this.name.move_lines:
                if move_ids.stack_id.id not in stack:
                    stack.append(move_ids.stack_id.id)
            for stack in self.env['stock.stack'].browse(stack):
                stack.btt_expenses()
                #Kiet: Goi sự kiện gọi Compute Stack
                for expenses in stack.expenses_ids:
                    direct_id = False
                    expenses_ids = self.env['mo.cost.direct'].search([('collection_id','=',this.id),('name','=',expenses.name)])
                    if expenses_ids:
                        expenses_ids.write({'valuesen':expenses.total_values + expenses_ids.valuesen})
                        vals ={
                               'direct_id':expenses_ids.id,
                               'picking_id':expenses.picking_id.id,
                               'product_qty':expenses.product_qty,
                               'cost':expenses.values,
                               'valuesvn':expenses.total_values2rd,
                               'valuesen':expenses.total_values
                               
                               }
                        self.env['mo.cost.direct.line'].create(vals)
                    else:
                        vals ={
                               'product_qty':nvl_consumed,
                               'name':expenses.name or False,
                               'valuesen': expenses.total_values or 0.0,
                               'collection_id':this.id,
                        }
                        direct_id = self.env['mo.cost.direct'].create(vals)
                        vals ={
                               'direct_id':direct_id.id,
                               'picking_id':expenses.picking_id.id,
                               'product_qty':expenses.product_qty,
                               'cost':expenses.values,
                               'valuesvn':expenses.total_values2rd,
                               'valuesen':expenses.total_values
                               
                               }
                        self.env['mo.cost.direct.line'].create(vals)
            
            #Kiet: Tạo bảng tính giá thành
            for prem in this.periodical_costing_id.premium_id.prem_ids:
                this.standard_cost = this.periodical_costing_id.premium_id.standard_cost or 0.0
                premium_id = self.env['mrp.bom.premium.line'].search([('flag','=',True)],limit=1)
                produced_qty = 0.0
                sql ='''
                    SELECT sum(produced_qty) produced_qty 
                    FROM mo_direct_cost_collection this where cost_collection_id in (%s)
                    and product_id = %s
                    GROUP BY product_id
                    HAVING sum(produced_qty) >0
                '''%(this.id,prem.product_id.id)
                self.env.cr.execute(sql)
                for y in self.env.cr.dictfetchall():
                    produced_qty = y['produced_qty'] or 0.0
                    
                val ={
                    'cost_collection_id':this.id,
                    'product_id':prem.product_id.id,
                    'product_qty':produced_qty,
                    'premium':prem.premium or 0.0,
                    'price':prem.premium +premium_id.premium
                    }
                self.env['costing.premium.line'].create(val)
            
            a = b = 0.0
            for line in this.premium_ids:
                a += line.product_qty * line.premium
                b += line.product_qty
            
            cp = this.total_cost - a / 1000
            price = b and cp / b or 0.0
            
            for line in this.premium_ids:
                line.price = line.premium/1000 + price
                        
        return True
    
class StockMoveAllocation(models.Model):
    _inherit = "stock.move.allocation"
    _order = 'in_date,allocated_date'
    
    cost_id = fields.Many2one('cost.materials.collection', 'collection', required=False, ondelete='cascade')
    allocated_qty = fields.Float(string='Basis qty', readonly=False,digits=(12, 0))
    net_qty = fields.Float(string='Net Qty', readonly=True,digits=(12, 0))
    allocated_value = fields.Float(related='from_move_id.price_unit',string='Price ($)', readonly=True)
    price_vnd = fields.Float(related='from_move_id.price_currency',string='Price (VND)', readonly=True, )
    
class CostMaterialsCollection(models.Model):
    _name = 'cost.materials.collection'
    _order = 'id desc'
     
    collection_id = fields.Many2one('mrp.production.order.cost.collection', 'MO Cost collection', required=False, ondelete='cascade')
    product_id =fields.Many2one('product.product', 'Product', required=False)
    #categ_id =fields.Many2one('product.category',related='product_id.categ_id',  string= 'Product Categoy', required=False)
    
    theory_qty = fields.Float(string ='Theory Qty',digits=(12, 0))
    theory_value = fields.Float(string ='Theory Value',digits=(12, 0))
    
    material_ids = fields.One2many('cost.materials.details','material_id', 'Materials Details', required=False ,ondelete='cascade')
    state = fields.Selection(selection=[("draft", "Draft"), ("post", "Post")],
                         readonly=True, copy=False,default="draft")          
    
    
    cost_id = fields.Many2one('mrp.periodical.production.costing', 'MO Cost collection', required=False, ondelete='cascade')
    allocation_ids = fields.One2many('stock.move.allocation', 'cost_id', string='FIFO',ondelete='cascade')
    
    @api.depends('material_ids','material_ids.product_qty','material_ids.values')
    def compute_consumed(self):
        for order in self:
            values = init_qty = product_qty = 0.0
            for line in order.material_ids:
                product_qty += line.product_qty
                init_qty += line.init_qty
                values = values + (line.values)
            order.product_qty = product_qty
            order.value = values
            order.init_qty = init_qty
    
    value = fields.Monetary(compute="compute_consumed",string="Consumed Value",store= True,currency_field='company_currency_id')
    product_qty = fields.Float(compute="compute_consumed", string ='Basis Qty',digits=(12, 0),store= True)
    #product_qty = fields.Float(string ='Basis Qty',digits=(12, 0))
    init_qty =fields.Float(compute="compute_consumed", string ='NET Qty',digits=(12, 0),store= True)
    company_currency_id = fields.Many2one('res.currency', related='collection_id.company_currency_id', readonly=True)
    product_uom = fields.Many2one('product.uom', related='product_id.uom_id', readonly=True)
    
    @api.depends('allocation_ids','allocation_ids.allocated_qty','allocation_ids.from_move_id')
    def compute_fifo_allocation(self):
        for order in self:
            fifo_qty  = 0.0
            price_fifo = 0.0
            for line in order.allocation_ids:
                fifo_qty += line.allocated_qty
                price_fifo += line.allocated_qty * line.allocated_value
                #price_fifo_net += line.net_qty * line.price_vnd
            
#             company = self.env['res.company'].browse(1)
#             second_currency_id = company.second_currency_id
#             price_fifo = second_currency_id.compute(price_fifo, company.currency_id)
#             price_fifo_net = second_currency_id.compute(price_fifo_net, company.currency_id)
            
            order.fifo_qty = fifo_qty
            #order.fifo_net_qty = fifo_net_qty
            order.amount_fifo_qty = price_fifo
            #order.amount_fifo_net_qty = price_fifo_net
            
    fifo_qty = fields.Float(compute="compute_fifo_allocation",string ='FIFO Qty',digits=(12, 0))
    fifo_net_qty = fields.Float(string ='FIFO Request Qty',digits=(12, 0))
    amount_fifo_qty = fields.Monetary(compute="compute_fifo_allocation",string ='FIFO Basis Amount',currency_field='company_currency_id',store= False)
    #fifo_qty = fields.Float(string ='FIFO Qty',digits=(12, 0))
    
    @api.multi
    def fifo_nvl(self):
        if self.fifo_net_qty !=0:
            self.fifo_allocation()
    
    def fifo_allocation(self):
        line = self
        location_nvp_id = self.env['stock.location'].search([('code','=','NVP - BMT')])
        while(line.fifo_net_qty - line.fifo_qty != 0):
            if line.product_id.default_code != 'FAQ':
#                 sql ='''
#                     DELETE 
#                     FROM stock_move_fifo 
#                     WHERE date(timezone('UTC',create_date::timestamp)) >'%s' 
#                     and product_id= %s
#                 '''%(self.cost_id.name.date_start,line.product_id.id)
#                 self.env.cr.execute(sql)
                
                sql ='''
                    SELECT sm.id, sm.price_unit,sm.price_currency,sm.date
                    FROM stock_move sm
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.id != %s
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.id = %s
                    WHERE 
                        product_id = %s
                        and sm.state ='done'
                        and (sm.price_unit != 0)
                        and sm.date > '2016-12-29'
                    order by sm.date
                '''%(location_nvp_id.id,location_nvp_id.id,line.product_id.id)
            else:
                sql ='''
                    SELECT sm.id, sm.price_unit,sm.price_currency,sm.date
                    FROM stock_move sm
                        join stock_location loc1 on sm.location_id = loc1.id and loc1.id != %s
                        join stock_location loc2 on sm.location_dest_id = loc2.id and loc2.id = %s
                    WHERE
                        product_id = %s
                        and picking_id != 84441 -- Dong điêu chỉnh. khong cho chạy FIFO
                        and sm.state ='done'
                        and (sm.price_unit != 0)
                    order by sm.date
                '''%(location_nvp_id.id,location_nvp_id.id,line.product_id.id)
            self.env.cr.execute(sql)
            for incoming in self.env.cr.dictfetchall():
                move = self.env['stock.move'].search([('id','=',incoming['id'])])
                if move and move.fifo:
                    continue
                if line.fifo_net_qty == line.fifo_qty:
                    break
                if move.qty_out_fifo <0:
                    continue
                move = self.env['stock.move'].browse(incoming['id'])
                fifo = line.fifo_net_qty - line.fifo_qty
                unfifo_qty = move.product_qty - (move.fifo_qty  + move.qty_out_fifo)
                #Kiet: Truong hop số lượng stock move lớn hơn lượng cần FIFO
                if fifo - unfifo_qty  >0:
                    qty_fifo = unfifo_qty
                else:
                    qty_fifo = fifo
                if qty_fifo <=0:
                    continue
                val ={
                      'cost_id':line.id,
                      'from_move_id':move.id,
                      'allocated_qty':qty_fifo,
                    }
                allocation_id = self.env['stock.move.allocation'].create(val)
                val ={
                      'fifo_id':move.id,
                      'product_qty':qty_fifo,
                      'fifo_colletion_id':allocation_id.id,
                      'out_qty':qty_fifo
                }
                fifo_id =self.env['stock.move.fifo'].create(val)
                move.refresh()
            return 1
        

class CostMaterialsDetails(models.Model):
    _name = 'cost.materials.details'
    _order = 'id desc'
    
    material_id = fields.Many2one('cost.materials.collection', 'Materials Details', required=False, ondelete='cascade')
    #product_id = fields.Many2one('product.product', 'Product ProdOpenuct', required=False, ondelete='cascade')
    #product_uom = fields.Many2one('product.uom', 'UoM', required=False, ondelete='cascade')
    #product_qty = fields.Float(string="Consumed Qty",digits=(12, 0))    
    values = fields.Monetary(string="Values Consumed",currency_field='company_currency_id')  
    
    #split_from_moves = fields.One2many('stock.move.allocation', 'to_move_id', string='Split From Moves')
    date = fields.Datetime(string="Date")
    #allocation_ids = fields.Many2many('stock.move.allocation', 'cost_material_rel', 'costing_material_id', 'allocation_id', 'FiFo', required=False)
    company_currency_id = fields.Many2one('res.currency', related='material_id.collection_id.company_currency_id', readonly=True)
    
    move_id = fields.Many2one('stock.move', 'Move', required=False)
    #kiet:
    picking_id = fields.Many2one('stock.picking',related='move_id.picking_id',  readonly=True,store= False)
    product_uom = fields.Many2one('product.uom',related='move_id.product_id.uom_id',string="UoM",  readonly=True,store= True)
    product_id = fields.Many2one('product.product',related='move_id.product_id',string="Product",  readonly=True,store= True)
    init_qty =  fields.Float(related='move_id.init_qty',string="Ned Qty",digits=(12, 0),store= True)  
    product_qty =  fields.Float(related='move_id.product_uom_qty',string="Basis Qty",digits=(12, 0),store= True)
    origin = fields.Many2one(related='move_id.picking_id',string="GIP",store= False) 
    notes = fields.Many2one('mrp.production',related='move_id.picking_id.production_id', string="Mos", readonly=True,store= False)
    #notes = fields.Text(related='move_id.note',string="Mo",store= True) 
#

class CostFinishsDetails(models.Model):
    _name = 'cost.finishs.details'
    _order = 'id desc'
    
    move_id = fields.Many2one('stock.move', 'Move', required=False)
    
    fin_id = fields.Many2one('mo.direct.cost.collection', 'Finishs Details', required=False, ondelete='cascade')
    #product_id = fields.Many2one('product.product', 'Product Product', required=False, ondelete='cascade')
    #product_uom = fields.Many2one('product.uom', 'UoM', required=False, ondelete='cascade')
    #product_qty = fields.Float(string="Basis Qty",digits=(12, 0))   
    #init_qty =  fields.Float(string="Ned Qty",digits=(12, 0))  
    values = fields.Monetary(string="Values Consumed",currency_field='company_currency_id')  
    move_id = fields.Many2one('stock.move', 'Move', required=False)
    #split_from_moves = fields.One2many('stock.move.allocation', 'to_move_id', string='Split From Moves')
    #date = fields.Datetime(string="Date")
    #allocation_ids = fields.Many2many('stock.move.allocation', 'cost_material_rel', 'costing_material_id', 'allocation_id', 'FiFo', required=False)
    company_currency_id = fields.Many2one('res.currency', related='fin_id.cost_id.company_currency_id', readonly=True)
    picking_id = fields.Many2one('stock.picking',related='move_id.picking_id',  readonly=True)
    product_uom = fields.Many2one('product.uom',related='move_id.product_id.uom_id',string="UoM",  readonly=True)
    product_id = fields.Many2one('product.product',related='move_id.product_id',string="Product",  readonly=True)
    init_qty =  fields.Float(related='move_id.init_qty',string="Ned Qty",digits=(12, 0),store= True)  
    product_qty =  fields.Float(related='move_id.product_uom_qty',string="Basis Qty",digits=(12, 0),store= True)  
    
class MoDirectCostCollection(models.Model):
    _name= 'mo.direct.cost.collection'
    _order = 'id desc'
    
    @api.depends('price_unit','produced_qty')
    def compute_price_subtotal(self):
        for order in self:
            order.price_subtotal = order.price_unit * order.produced_qty
    
    @api.depends('fis_ids','fis_ids.move_id')
    def compute_total_qty(self):
        for order in self:
            init_qty = product_uom =0.0
            for line in order.fis_ids:
                product_uom += line.product_qty
                init_qty += line.init_qty
            order.produced_qty = product_uom
            order.init_qty = init_qty
            
    cost_collection_id = fields.Many2one('mrp.production.order.cost.collection', 'MO Cost collection', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    #product_uom_id = fields.Many2one('product.uom', 'UoM', required=True)
    produced_qty = fields.Float('Basis Qty',compute="compute_total_qty", digits=(12, 0), readonly=True)
    init_qty = fields.Float('Net Qty',compute="compute_total_qty", digits=(12, 0), readonly=True)
    price_unit = fields.Monetary('Unit Price', currency_field='company_currency_id')
    price_subtotal = fields.Monetary('Price Subtotal',compute="compute_price_subtotal",currency_field='company_currency_id',store= True)
    company_currency_id = fields.Many2one('res.currency', related='cost_collection_id.company_currency_id', readonly=True)
    
    #Moi them
    cost_id = fields.Many2one('mrp.periodical.production.costing', 'MO Cost collection', required=False, ondelete='cascade')
    fis_ids = fields.One2many('cost.finishs.details', 'fin_id', string='GRP')
    product_uom_id = fields.Many2one('product.uom', related='product_id.uom_id',string="UoM", readonly=True)

class MoCostDirect(models.Model):
    _name= 'mo.cost.direct'
    _order = 'id desc'
    
    @api.depends('valuesen')
    def _compute_values(self):
        for this in self:
            total_qty = 0.0
            for move in this.collection_id.name.move_lines:
                total_qty += move.product_qty or 0.0
            this.total_consume = total_qty and this.product_qty * this.valuesen /total_qty or 0.0
        
    name = fields.Char(string="Name")
    valuesen = fields.Monetary(string="Total Values",currency_field='company_currency_id')
    product_qty = fields.Float(string="Qty Consumed",digits=(12, 0))
    collection_id = fields.Many2one('mrp.production.order.cost.collection', 'MO Cost collection', required=False, ondelete='cascade')
    total_consume = fields.Monetary(string='Value Consume',compute='_compute_values', store = True,currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', related='collection_id.company_currency_id', readonly=True)
    second_currency_id  = fields.Many2one(related='company_id.second_currency_id', relation='res.currency', string="Currency",store= False)
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    direct_line = fields.One2many('mo.cost.direct.line','direct_id', 'Direct Details', required=False)
    
    cost_id = fields.Many2one('mrp.periodical.production.costing', 'MO Cost collection', required=False, ondelete='cascade')
    
#     @api.depends('material_ids','material_ids.product_qty','material_ids.values')
#     def compute_consumed(self):
#         for order in self:
#             product_qty = 0.0
#             values = 0.0
#             for line in order.material_ids:
#                 product_qty = product_qty + line.product_qty
#                 values = values + (line.values)
#             order.product_qty = product_qty
#             order.value = values
#     
#     value = fields.Monetary(compute="compute_consumed",string="Consumed Value",store= True,currency_field='company_currency_id')


class MoCostDirectLine(models.Model):
    _name= 'mo.cost.direct.line'
    _order = 'id desc'
    
    direct_id = fields.Many2one('mo.cost.direct', 'Direct Cost Details', required=False, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', 'GRN', required=False, ondelete='cascade')
    product_qty = fields.Float(string="GRN Qty",digits=(12, 0))    
    cost = fields.Monetary(string="Cost",currency_field='second_currency_id')    
    valuesvn = fields.Monetary(string="Total Values",currency_field='second_currency_id')    
    valuesen = fields.Monetary(string="Total Values",currency_field='com_currency_id')   
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    second_currency_id = fields.Many2one('res.currency',related='company_id.second_currency_id', string="2rd Currency", readonly=True)
    com_currency_id = fields.Many2one('res.currency', related='company_id.currency_id',string="Currency", readonly=True)
    
    
    
    