# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.float_utils import float_compare, float_round

from openerp.tools.misc import formatLang
import time
from openerp.tools import append_content_to_html
from openerp import SUPERUSER_ID
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class DeliveryOrder(models.Model):
    _inherit = "delivery.order"
    
    @api.depends('picking_id.move_lines.bag_no','picking_id.move_lines.weighbridge','picking_id','picking_id.state','post_shippemnt_ids.post_line','post_shippemnt_ids','post_shippemnt_ids.post_line.bags','post_shippemnt_ids.post_line.shipped_weight')
    def _factory_qty(self):
        for order in self:
            weight = bagsfactory  = 0
            for pick in order.picking_id:
                if pick.state == 'done':
                    for line in pick.move_lines:
                        bagsfactory += line.bag_no or 0.0
                        #weight += line.product_uom_qty
                        weight += line.weighbridge or 0.0 
            
            shipped_weight = bags  = 0
            for post in order.post_shippemnt_ids:
                for line in post.post_line:
                    bags += line.bags
                    shipped_weight += line.shipped_weight
                    
            order.bags = bags
            order.shipped_weight = shipped_weight
            
            order.bagsfactory = bagsfactory
            order.weightfactory = weight
            order.storing_loss = order.total_qty -  weight 
            order.transportation_loss = weight -  shipped_weight 
            
    bagsfactory = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Bags Factory',store =True)
    weightfactory = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Weight Factory',store =True)
    
    storing_loss  = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Storing Loss',store =False)
    transportation_loss  = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Transportation Loss',store =True)
    bags = fields.Float(compute='_factory_qty', digits=(12, 0) , string='BagsHCM',store =True)
    shipped_weight = fields.Float(compute='_factory_qty', digits=(12, 0) , string='WeightHCM',store =True)
    from_warehouse_id= fields.Many2one('stock.warehouse',string="From Warehouse")
    
    @api.multi
    def create_picking(self):
        this =self
        product_id = this.delivery_order_ids and this.delivery_order_ids[0].product_id
        form_picking_type = this.from_warehouse_id.int_type_id
        var = {'name': '/', 
               'picking_type_id': form_picking_type.id or False, 
               'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
               'origin':this.name,
               'partner_id': this.partner_id.id or False,
               'picking_type_code': form_picking_type.code or False,
               'location_id': form_picking_type.default_location_src_id.id or False, 
               'vehicle_no':this.trucking_no or '',
               'location_dest_id': form_picking_type.default_location_dest_id.id or False, 
               'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
        picking_id = self.env['stock.picking'].create(var)  
         
        self.env['stock.move'].create({'picking_id': picking_id.id or False, 
               'name': product_id.name or '', 
               'product_id': product_id.id or False,
               'product_uom': product_id.uom_id.id or False, 
               'product_uom_qty':  0.0,
               'init_qty': 0.0,
               'price_unit': 0.0,
               'picking_type_id': form_picking_type.id or False, 
               'location_id': form_picking_type.default_location_src_id.id or False, 
               'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
               'location_dest_id': form_picking_type.default_location_dest_id.id or False, 
#                'type': form_picking_type.code or False,
               'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
               'partner_id': this.partner_id.id or False,
               'company_id': 1,
               'state':'draft', 
               'scrapped': False, 
               'warehouse_id': this.from_warehouse_id.id or False})
        
    
class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    production_out_type_consu_id = fields.Many2one('stock.picking.type', 'Production Type Material - Out')
    transfer_in_id = fields.Many2one('stock.picking.type', 'Transfer In')
    transfer_out_id = fields.Many2one('stock.picking.type', 'Transfer Out')
    out_type_local_id = fields.Many2one('stock.picking.type', 'Delivery Local')

class DeliveryPlace(models.Model):
    _inherit = "delivery.place"
    _order = 'id desc'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}
        if context.get('picking_type_code', False):
            if context['picking_type_code'] == 'incoming':
                args += [('type', '=', 'purchase')]
            if context['picking_type_code'] == 'outgoing':
                args += [('type', '=', 'transport')]
        return super(DeliveryPlace, self).search(args, offset, limit, order, count=count)


class StockPackOperation(models.Model):
    _inherit = "stock.pack.operation"
    
    @api.multi
    def unlink(self):
        if any([x.state in ('done', 'cancel') for x in self]):
            raise UserError(_('You can not delete pack operations of a done picking'))
        return super(StockPackOperation, self).unlink()
     
class StockPicking(models.Model):
    _inherit = "stock.picking"
    _order = 'id desc'
    
    def get_datetime(self, date):
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y-%m-%d')
    
    def get_years(self, date):
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y')
    
    @api.depends('date_done','state')
    def _compute_date(self):
        for line in self:
            if line.date_done:
                line.day_tz = self.get_datetime(line.date_done)
                line.years_tz = self.get_years(line.date_done)
            else:
                line.day_tz = False
                line.years_tz =False
    
    day_tz = fields.Date(compute='_compute_date',string = "Day tz", store=True)
    years_tz = fields.Char(compute='_compute_date',string = "Years tz", store=True)
    
    delivery_order_id = fields.Many2one('delivery.order',string="Delivery Order")
    
    
#     @api.model
#     def create(self, vals):
#         new_id = super(StockPicking, self).create(vals)
#         new_id.barcode = self.general_barcode_pick() or False
#         return new_id

    
    @api.multi
    def button_load(self):
        this = self
        if this.delivery_order_id:
            delivery_order_ids = this.delivery_order_id.delivery_order_ids
            product_id = delivery_order_ids[0].product_id
            this.min_date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            
            form_picking_type = this.delivery_order_id.from_warehouse_id.int_type_id
            
            this.name = form_picking_type.sequence_id.with_context(ir_sequence_date=self.get_datetime(this.min_date)).next_by_id()
            
            
            this.picking_type_id = form_picking_type.id or False, 
            
            this.origin = this.delivery_order_id.name
            this.partner_id = this.delivery_order_id.partner_id and this.delivery_order_id.partner_id.id or False
            this.picking_type_code = form_picking_type.code or False
            this.location_id = form_picking_type.default_location_src_id.id or False
            this.location_dest_id = form_picking_type.default_location_dest_id.id or False
            this.vehicle_no = this.delivery_id.trucking_no or ''
             
            self.env['stock.move'].create({'picking_id': this.id or False, 
                   'name': product_id.name or '', 
                   'product_id': product_id.id or False,
                   'product_uom': product_id.uom_id.id or False, 
                   'product_uom_qty':  0.0,
                   'init_qty': 0.0,
                   'price_unit': 0.0,
                   'picking_type_id': form_picking_type.id or False, 
                   'location_id': form_picking_type.default_location_src_id.id or False, 
                   'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   'location_dest_id': form_picking_type.default_location_dest_id.id or False, 
                   'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
                   'partner_id': this.partner_id.id or False,
                   'company_id': 1,
                   'state':'draft', 
                   'scrapped': False, 
                   'warehouse_id': this.delivery_id.from_warehouse_id.id or False})
        
        
        
  
    def general_barcode_pick(self):
        sequence_obj = self.env['ir.sequence']
        system_sequence_obj = self.env['system.sequence']
        barcode = False
        code = system_sequence_obj.get_current_sequence('picking_code')
        print code,'asasa'
        if code:
            barcode = sequence_obj.seq_generate_ean13(code)
        return barcode
    
    barcode = fields.Char(string="Barcode")
    
    
    
    def _prepare_account_move_line(self,line, qty,amount , debit_account_id, credit_account_id):
        debit = credit = amount
        partner_id = line.picking_id.partner_id.id
        name = line.product_id.default_code
        debit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            
            'debit': debit or 0.0,
            'credit':  0.0,
            'account_id': debit_account_id,
            #'currency_id':self.company_id.second_currency_id.id,
            #'amount_currency':debit,
        }
        credit_line_vals = {
            'name': name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'partner_id': partner_id,
            'debit': 0.0,  
            'credit': credit or 0.0,
            'account_id': credit_account_id,
            #'currency_id':self.company_id.second_currency_id.id,
            #'amount_currency':debit * (-1)
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    def update_entries_adj(self,move):
        debit_id = move.picking_id.acc_dr_id.id
        credit_id = move.picking_id.acc_cr_id.id
        if move and move.product_uom_qty == move.qty_out_fifo:
            move_lines = self._prepare_account_move_line(move, move.product_qty ,move.price_out_fifo , debit_id,credit_id)
        else:
            move_lines = self._prepare_account_move_line(move, move.product_qty ,move.price_unit * move.product_qty, debit_id,credit_id)

        return move_lines
        
    def create_entries_adj(self,move):
        #Kiet: GIao dich nhap
        move_obj = self.env['account.move']
        debit_id = move.picking_id.acc_dr_id.id
        credit_id = move.picking_id.acc_cr_id.id
        
        if move and move.fifo_out:
            product_obj = self.env['product.template']
            accounts = product_obj.browse(move.product_id.product_tmpl_id.id).get_product_accounts()
            journal_id = accounts['stock_journal'].id
            move_lines = self._prepare_account_move_line(move, move.product_qty ,move.price_out_fifo, debit_id,credit_id)
            if move_lines:
                ref = move.picking_id.name
                date = move.picking_id.date_done
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': ref,
                                      'narration':False})
                
                new_move_id.post()
                move.entries_id = new_move_id.id
                move.price_unit = move.product_uom_qty and move.price_out_fifo/move.product_uom_qty or 0.0
        else:
            product_obj = self.env['product.template']
            accounts = product_obj.browse(move.product_id.product_tmpl_id.id).get_product_accounts()
            journal_id = accounts['stock_journal'].id
            move_lines = self._prepare_account_move_line(move, move.product_qty ,move.price_unit * move.product_uom_qty, debit_id,credit_id)
            if move_lines:
                ref = move.picking_id.name
                date = move.picking_id.date_done
                new_move_id = move_obj.create({'journal_id': journal_id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': u'Điều chỉnh kho - ' +ref,
                                      'narration':False})
                new_move_id.post()
                move.entries_id = new_move_id.id
            return False

    
    @api.multi
    def fifo_stock(self):
        for outgoing in self.move_lines:
            if outgoing.location_id.usage=='internal':
                outgoing.refresh()
                
                if outgoing.fifo_out:
                    continue
                
                while(not outgoing.fifo_out):
                    if outgoing.fifo_out:
                        continue
                    
                    incoming_ids = self.env['stock.move'].search([('location_id','!=',outgoing.location_id.id),
                                ('location_dest_id','=',outgoing.location_id.id),('state','=','done'),
                                ('price_unit','!=',0),('product_id','=',outgoing.product_id.id)], order ="date,id")
                    incoming_idss =[]
                    for x in incoming_ids:
                        if  x.fifo == False:
                            incoming_idss.append(x)
                    if incoming_idss:
                        for incoming in incoming_idss:
                            incoming.refresh()
                            if outgoing.fifo_out == True:
                                break
                            if incoming.fifo == True:
                                continue
                            fifo = outgoing.qty_out_unfifo - incoming.unfifo_qty
                            #Kiet: Truong hop số lượng stock move lớn hơn lượng cần FIFO outgoing.unfifo_qty 
                            if fifo >0:
                                qty_fifo = incoming.unfifo_qty
                            else:
                                qty_fifo = outgoing.qty_out_unfifo
                            
                            if qty_fifo <0:
                                continue
                                
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
                    
                    
        for move in self.move_lines:
            move.refresh()
            if move.entries_id:
                move.entries_id.button_cancel()
                sql ='''
                    DELETE from account_move_line where move_id = %s
                '''%(move.entries_id.id)
                self.env.cr.execute(sql)
                move.entries_id.write({'line_ids':self.update_entries_adj(move)})
                move.entries_id.post()
                move.price_unit = move.product_uom_qty and move.price_out_fifo / move.product_uom_qty or 0.0
            else:
                if move.fifo_out:
                    self.create_entries_adj(move)
                if move.location_id.usage !='internal' and move.location_dest_id.usage =='internal':  
                    if move.price_unit and move.price_unit:
                        self.create_entries_adj(move)
        return 1
    
#         
#     @api.multi
#     def fifo_stock1(self):
#         for outgoing in self.move_lines:
#             if outgoing.location_id.usage=='internal':
#                 outgoing.refresh()
#                 if outgoing.fifo_cus:
#                     continue
#                 while(not outgoing.fifo_cus):
#                     if outgoing.fifo_cus:
#                         continue
#                     incoming_ids = self.env['stock.move'].search([
#                     ('location_id','!=',outgoing.location_id.id),('location_dest_id','=',outgoing.location_id.id),
#                                 ('product_id','=',outgoing.product_id.id)], order ="date,id")
#                     flag = False
#                     for x in incoming_ids:
#                         if  x.fifo_hcm == False:
#                             flag = True
#                     if flag:
#                         for incoming in incoming_ids:
#                             incoming.refresh()
#                             if outgoing.fifo_cus == True:
#                                 break
#                             if incoming.fifo_hcm == True:
#                                 continue
#                             fifo = outgoing.qty_cus_out_unfifo - incoming.unfifo_hcm_qty
#                             #Kiet: Truong hop số lượng stock move lớn hơn lượng cần FIFO outgoing.unfifo_qty 
#                             if fifo >0:
#                                 qty_fifo = incoming.unfifo_hcm_qty
#                             else:
#                                 qty_fifo = outgoing.qty_cus_out_unfifo
#                             if incoming.id and outgoing.id:
#                                 val ={
#                                       'fifo_hcm_id':incoming.id,
#                                       'product_hcm_qty':qty_fifo,
#                                       'fifo_cus_id': outgoing.id,
#                                       'product_cus_qty':qty_fifo
#                                 }
#                                 self.env['stock.move.fifo'].create(val)
#                             incoming.refresh()
#                             outgoing.refresh()
#                     else:
#                         break
#                     
#         for move in self.move_lines:
#             move.refresh()
#             if move.entries_id:
#                 move.entries_id.button_cancel()
#                 sql ='''
#                     DELETE from account_move_line where move_id = %s
#                 '''%(move.entries_id.id)
#                 self.env.cr.execute(sql)
#                 move.entries_id.write({'line_ids':self.update_entries_adj(move)})
#                 move.entries_id.post()
#                 move.price_unit = move.product_uom_qty and move.price_cus_fifo / move.product_uom_qty or 0.0
#             else:
#                 if move.price_cus_fifo:
#                     self.create_entries_adj(move)
#                 if move.location_id.usage !='internal' and move.location_dest_id.usage =='internal':  
#                     if move.price_unit and move.price_unit:
#                         self.create_entries_adj(move)
#         return 1
        
    
    @api.model
    def default_get(self, fields):
        res = super(StockPicking, self).default_get(fields)
        picking_type = self.env['stock.picking.type']
        location = self.env['stock.location']
        
        location_transit_ids = [x.id for x in location.search([('usage','=','transit'),('active','=',True)])]
        if self._context.get('transfer_out'):
            picking_type_id = picking_type.search([('code','=','transfer'),('default_location_dest_id','in',location_transit_ids),('active','=',True)], limit=1)
        elif self._context.get('transfer_in'):
            picking_type_id = picking_type.search([('code','=','transfer'),('default_location_src_id','in',location_transit_ids),('active','=',True)], limit=1)
        elif self._context.get('picking_internal'):
            picking_type_id = picking_type.search([('code','=','internal'),('active','=',True)], limit=1)
        elif self._context.get('picking_outgoing'):
            picking_type_id = picking_type.search([('code','=','outgoing'),('active','=',True)], limit=1)
        elif self._context.get('picking_return_supplier'):
            picking_type_id = picking_type.search([('code','=','return_supplier'),('active','=',True)], limit=1)
        
        elif self._context.get('picking_return_supplier'):
            picking_type_id = picking_type.search([('code','=','return_supplier'),('active','=',True)], limit=1)
            
        elif self._context.get('picking_grp_Goods'):
            picking_type_id = picking_type.search([('code','=','production_in'),('active','=',True)], limit=1)
            res.update({'domain': {'picking_type_id': picking_type_id.id}})
            
        elif self._context.get('picking_grn_Goods'):
            picking_type_id = picking_type.search([('code','=','incoming'),('active','=',True)], limit=1)
            
        else:
            picking_type_id = picking_type.search([('active','=',True)], limit=1)
            
        res['picking_type_id'] = picking_type_id.id
        res['picking_type_code'] = picking_type_id.code
        return res
    
    grn_id = fields.Many2one('stock.picking', string='GRN',)
    delivery_place_id = fields.Many2one('delivery.place', string='Delivery Place',
       readonly=True, states={'draft': [('readonly', False)]}, required=False,)
    
    delivery_fee = fields.One2many('delivery.fee','picking_id', string='Delivery Fee',)
    vehicle_no = fields.Char(string='Vehicle No.', required=False, size=128)
    transfer = fields.Boolean(String='Transfer',default= False)
    stack_id = fields.Many2one(related='move_lines.stack_id',  string='Stack',store = True)
    zone_id = fields.Many2one(related='move_lines.zone_id',  string='Zone',store = True)
    certificate_id = fields.Many2one('ned.certificate', string='Certificate', ondelete='restrict')
    districts_id = fields.Many2one('res.district', string='Source', ondelete='restrict')
    move_weight = fields.One2many('stock.move','picking_id', string='Weighing',)
    packing_id = fields.Many2one(related='move_lines.packing_id',  string='Packing')
    pledg = fields.Char(string='Pledging', required=False, size=128)
    to_picking_type_id =fields.Many2one('stock.picking.type',  string='To Warehouse',copy=False)
    
    
    @api.depends('move_lines.product_uom_qty','move_lines','move_lines.product_qty','move_lines.weighbridge','move_lines.init_qty')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            total_init_qty = 0
            total_weighbridge_qty = 0
            for line in order.move_lines:
                total_qty +=line.product_qty
                total_init_qty +=line.init_qty or 0.0
                total_weighbridge_qty += line.weighbridge or 0.0
            order.total_qty = total_qty
            order.total_init_qty = total_init_qty or 0.0
            order.total_weighbridge_qty = total_weighbridge_qty or 0.0
            
            
    total_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Total Qty',store=True)
    total_init_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Init Qty',store=True)
    total_weighbridge_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Real Qty',store=False)
    
    @api.multi
    def create_picking_itr(self):
        for pick in self:
            
            
            if pick.delivery_order_id:
                #Trường hợp từ BMT - > chuyển wa các kho khác
                if pick.origin:
                    names = (pick.name) + '; '+ pick.origin
                else:
                    names = (pick.name)
                
                picking_type = pick.delivery_order_id.warehouse_id.transfer_in_id
                new_id = pick.copy({'name':'/','picking_type_id':picking_type.id,
                       'location_id':picking_type.default_location_src_id.id,
                       'location_dest_id':picking_type.default_location_dest_id.id,
                       'origin':names,
                       'date_done':pick.date_done,
                       'orign_transfer_internal_ids':[(6, 0,[])],
                       'transfer':False,
                       'backorder_id':pick.id,
                       'picking_transfer_internal_ids':[(4,pick.id)]})
                
                zone = self.env['stock.zone'].search([('warehouse_id','=',picking_type.warehouse_id.id)], limit =1)
                for line_move in new_id.move_lines:
                    count = 1
                    for line_move1 in new_id.move_lines:
                        if count == 1:
                            line_move1.product_uom_qty = 0.0
                            line_move1.init_qty = 0.0
                            line_move1.bag_no = 0.0
                            line_move1.zone_id = zone.id
                            line_move1.tare_weight = 0.0
                            count=0
                        else:
                            line_move1.unlink()
                
                new_id.btt_loads()
                #Trường hợp từ BMT - > chuyển wa các kho khác
                allocation = self.env['lot.stack.allocation'].search([('gdn_id','=',pick.id)],limit =1)
                if allocation:
                    manager = allocation.lot_id
                    for line in new_id.kcs_line:
                        line.mc = manager.mc_on_despatch or manager.mc
                        line.fm = manager.fm
                        line.black = manager.black
                        line.broken = manager.broken or 0.0
                        line.brown = manager.brown or 0.0
                        line.mold = manager.mold or 0.0
                        line.cherry = manager.cherry or 0.0
                        line.excelsa = manager.excelsa or 0.0
                        line.screen18 = manager.screen18 or 0.0
                        line.screen16 = manager.screen16 or 0.0
                        line.screen13 = manager.screen13 or 0.0
                        line.belowsc12 = manager.screen12 or 0.0
                          
                        line.burned = manager.burn or 0.0
                        line.eaten = manager.eaten or 0.0
                        line.immature = manager.immature or 0.0
                        line.stick_count = manager.stick
                        line.stone_count = manager.stone
                        line.maize = manager.maize
                else:
                    #Truong hợp chât lượng chuyển từ kho khác về 
                    stack = pick.stack_id
                    for line in new_id.kcs_line:
                        line.bb_sample_weight = 100
                        line.sample_weight =100
                        line.mc = stack.mc
                        line.fm = stack.fm
                        line.black = stack.black
                        line.broken = stack.broken or 0.0
                        line.brown = stack.brown or 0.0
                        line.mold = stack.mold or 0.0
                        line.cherry = stack.cherry or 0.0
                        line.excelsa = stack.excelsa or 0.0
                        line.screen18 = stack.screen18 or 0.0
                        line.screen16 = stack.screen16 or 0.0
                        line.screen13 = stack.screen13 or 0.0
                        line.belowsc12 = stack.screen12 or 0.0
                           
                        line.burned = stack.burn or 0.0
                        line.eaten = stack.eaten or 0.0
                        line.immature = stack.immature or 0.0
                        line.stick_count = stack.stick_count
                        line.stone_count = stack.stone_count
                        line.maize = stack.maize

                new_id._total_qty()    
                new_id.state_kcs = 'approved'
                
                
                
            if pick.picking_type_id.transfer_picking_type_id:
                if pick.origin:
                    names = (pick.name) + '; '+ pick.origin
                else:
                    names = (pick.name)
                new_id = pick.copy({'name':'/','picking_type_id':pick.picking_type_id.transfer_picking_type_id.id,
                       'location_id':pick.picking_type_id.transfer_picking_type_id.default_location_src_id.id,
                       'location_dest_id':pick.picking_type_id.transfer_picking_type_id.default_location_dest_id.id,
                       'origin':names,
                       'date_done':pick.date_done,
                       'orign_transfer_internal_ids':[(6, 0,[])],
                       'transfer':False,
                       'backorder_id':pick.id,
                       'picking_transfer_internal_ids':[(4,pick.id)]})
                
                for line_move in new_id.move_lines:
                    for line_move1 in new_id.move_lines:
                        if line_move.product_id == line_move1.product_id:
                            if pick.picking_type_id.transfer_picking_type_id.stack:
                                line_move1.product_uom_qty = 0.0
                                line_move1.init_qty = 0.0
                                line_move1.init_qty = 0.0
                                line_move1.first_weight = 0.0
                                line_move1.second_weight  = 0.0
                                line_move1.packing_id = False
                                line_move1.bag_no = 0.0
                                line_move1.tare_weight = 0.0
                                
                            line_move1.stack_id = False
                            line_move1.zone_id = False
                
                
    
    def do_transfer(self):
        res = super(StockPicking,self).do_transfer()
        if self.backorder_id and self.backorder_id.picking_type_id.warehouse_id.code == 'BCCE':
            this = self
            for line in this.move_lines:
                for line1 in self.backorder_id.move_lines:
                    if line.product_id.id == line1.product_id.id:
                        product_uom_qty = line.init_qty - round((line.init_qty * abs(line1.stack_id.avg_deduction/100)),0)
                        sql ='''
                            update stock_move set product_uom_qty = %s,init_qty = %s,product_qty =  %s
                            WHERE id = %s
                        '''%(product_uom_qty,line.init_qty,line.init_qty,line1.id)
                        self.env.cr.execute(sql)
                        
                        self.backorder_id.action_done()
                        self.backorder_id._total_qty()   
                        line.product_uom_qty = product_uom_qty
            self._total_qty()   
            self.action_done()
                        
        return res
        
    def action_done(self):
        super(StockPicking,self).action_done()
        #Kiet: Update the same stock_move with date done of stock_picking
        for pick in self:
            if pick.to_picking_type_id:
                if pick.origin:
                    names = (pick.name) + '; '+ pick.origin
                else:
                    names = (pick.name)
                    
                new_id = pick.copy({'name':'/','picking_type_id':pick.to_picking_type_id.id,
                       'location_id':pick.picking_type_id.default_location_src_id.id,
                       'location_dest_id':pick.to_picking_type_id.default_location_dest_id.id,
                       'origin':names,
                       'date_done':pick.date_done,
                       'to_picking_type_id':False,
                       'backorder_id':pick.id,
                       'orign_transfer_internal_ids':[(6, 0,[])],
                       'transfer':False,
                       'picking_transfer_internal_ids':[(6, 0,[pick.id])]})
                
                for line_move in new_id.move_lines:
                    for line_move1 in new_id.move_lines:
                        if line_move.product_id == line_move1.product_id:
                            if pick.to_picking_type_id.stack:
                                line_move1.product_uom_qty = 0.0
                                line_move1.init_qty = 0.0
                                line_move1.first_weight = 0.0
                                line_move1.second_weight  = 0.0
                                line_move1.packing_id = False
                                line_move1.bag_no = 0.0
                                line_move1.tare_weight = 0.0
                                
                            line_move1.stack_id = False
                            line_move1.zone_id = False
                
        
        return True
 
class DeliveryFee(models.Model):
    _order = 'create_date desc, id desc'
    _name = "delivery.fee"
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    district_id = fields.Many2one('res.district', string='District',)
    cost = fields.Monetary(string='Amount')
    picking_id = fields.Many2one('stock.picking', string='Picking',)
    province_id = fields.Many2one("res.country.state", 'Province')
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency_id)
    
class ReasonLockStack(models.Model):
    _order = 'create_date desc, id desc'
    _name = "reason.lock.stack"
    _description = "Reason Lock Stack"
    
    name = fields.Char(string='Description', required=True, size=128)


class StockStackTranfer(models.Model):
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'create_date desc, id desc'
    _name = "stock.stack.transfer"
    _description = "Stock Stack Transfer"
     
    name = fields.Char(string='Description', required=True, size=128, readonly=True, states={'draft': [('readonly', False)]})
    from_zone_id = fields.Many2one('stock.zone', string='From Zone', ondelete='cascade', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    to_zone_id = fields.Many2one('stock.zone', string='To Zone', ondelete='cascade', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved')],
         readonly=True, copy=False , default='draft', track_visibility='onchange')
     
    note = fields.Text(string='Note', required=False, size=128, readonly=True, states={'draft': [('readonly', False)]})
    stack_ids = fields.Many2many('stock.stack', 'transfer_stack_rel', 'transfer_id', 'stack_id', string='Stack', readonly=True, states={'draft': [('readonly', False)]})
    date_order = fields.Date(string='Date', default=fields.Datetime.now, readonly=True, states={'draft': [('readonly', False)]})
    date_approve = fields.Date('Date Approval', readonly=True, select=True, copy=False,)
    user_approve_id = fields.Many2one('res.users', string='User Approve', readonly=True)
    user_responsible_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self._uid, readonly=True,)
    
    
    @api.multi
    def button_approved(self):
        for lock in self:
            for stack in lock.stack_ids:
                stack.zone_id = lock.to_zone_id.id
            self.write({'state': 'approved', 'user_approve_id': self.env.uid,
                    'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            
    
class StackLock(models.Model):
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'create_date desc, id desc'
    _name = "stack.lock"
    _description = "Lock Stack"
    
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    reason_id = fields.Many2one('reason.lock.stack', string='Reason', ondelete='cascade', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Description', required=True, size=128, readonly=True, states={'draft': [('readonly', False)]})
    zone_id = fields.Many2one('stock.zone', string='Zone', ondelete='cascade', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'), ('cancel', 'Cancelled')],
         readonly=True, copy=False , default='draft', track_visibility='onchange')
    note = fields.Text(string='Note', required=False, size=128, readonly=True, states={'draft': [('readonly', False)]})
    stack_ids = fields.Many2many('stock.stack', 'lock_stack_rel', 'lock_id', 'stack_id', string='Stack', readonly=True, states={'draft': [('readonly', False)]})
    date_order = fields.Date(string='Date', default=fields.Datetime.now, readonly=True, states={'draft': [('readonly', False)]})
    date_approve = fields.Date('Date Approval', readonly=True, select=True, copy=False,)
    user_approve_id = fields.Many2one('res.users', string='User Approve', readonly=True)
    user_responsible_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self._uid, readonly=True,)
    type = fields.Selection(selection=[('lock', 'Lock'), ('unlock', 'Unlock'), ],
         required=True, copy=False , default='lock', readonly=True, states={'draft': [('readonly', False)]})
    bank_id = fields.Many2one('res.bank', string='Banks', readonly=True, states={'draft': [('readonly', False)]})
    
    mortgage_amount = fields.Monetary(string='Amount', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency_id, readonly=True, states={'draft': [('readonly', False)]})
    production_id = fields.Many2one('mrp.production', string='Manufacturing Orders')
    contract_id = fields.Many2one('s.contract', string='SNo.')
    notes = fields.Text(string="Notes")
    
    
    @api.multi
    def button_approved(self):
        for lock in self:
            if lock.type == 'lock':
                for stack in lock.stack_ids:
                    stack.lock = True
                    stack.production_id = lock.production_id.id
                    stack.contract_id = lock.contract_id.id
                    
                self.write({'state': 'approved', 'user_approve_id': self.env.uid,
                        'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            
            if lock.type == 'unlock':
                for stack in lock.stack_ids:
                    stack.lock = False
                self.write({'state': 'approved', 'user_approve_id': self.env.uid,
                        'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi
    def button_cancel(self):
        for lock in self:
            if lock.type == 'lock':
                for stack in lock.stack_ids:
                    stack.lock = False
                    stack.production_id = False
                    stack.contract_id = False
                self.write({'state': 'cancel', 'user_approve_id': False,
                    'date_approve': False})
            if lock.type == 'unlock':
                for stack in lock.stack_ids:
                    stack.lock = True
                self.write({'state': 'cancel', 'user_approve_id': False,
                    'date_approve': False})
                
    
    @api.multi
    def button_draft(self):
        for lock in self:
            if lock.type == 'lock':
                for stack in lock.stack_ids:
                    stack.lock = False
                self.write({'state': 'draft', 'user_approve_id': False,
                    'date_approve': False})
            
            if lock.type == 'unlock':
                for stack in lock.stack_ids:
                    stack.lock = True
                self.write({'state': 'draft', 'user_approve_id': False,
                    'date_approve': False})

class StockZone(models.Model):
    _name = "stock.zone"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'create_date desc, id desc'
    
    name = fields.Char(string='Name', required=True, size=128)
    code = fields.Char(string='Code', required=False, size=128)
    description = fields.Char(string='Description', required=False, size=128)
    stack_ids = fields.One2many('stock.stack', 'zone_id' , string='Stack Line')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    active = fields.Boolean(string='Active', default=True)
    
    @api.multi
    def is_code_uniq(self):
        for zone in self:
#             zone_ids = self.search([('code','=', zone.code),
#                                               ('id','<>', zone.id)])
#             if zone_ids:
#                 return False
            
            zone_ids = self.search([('name','=', zone.name),
                                              ('id','<>', zone.id)])
            if zone_ids:
                return False
        return True

    _constraints = [(is_code_uniq, 'Zone Exist', ['name'])]
    
    
class StockStack(models.Model):
    _name = "stock.stack"
    _order = 'create_date desc, id desc'
    
    @api.multi
    def unlink(self):
        if self.move_ids:
            raise UserError(_('You can not delete Stack'))
        return super(StockStack, self).unlink()
    
    @api.multi
    def stack_reports(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'report_stack',
                }
    @api.multi
    def dieuchinhqc(self):
        for this in self:
#             sql ='''
#                 SELECT id from stock_picking where backorder_id is not null and picking_type_id = 104
#                     and delivery_order_id is not null
#             '''
#             self.env.cr.execute(sql)
#             for line in self.env.cr.dictfetchall():
#                 pick = self.env['stock.picking'].browse(line['id'])
#                 for line in pick.backorder_id.move_lines:
#                     belowsc12 = line.stack_id.screen12
#                     pick.kcs_line[0].belowsc12 = belowsc12
#                     pick.move_lines[0].stack_id._compute_qc()
                    
            
#             this._get_remaining_qty()
#             gip_ids =[]
#             for gip in self.move_ids:
#                 if gip.picking_id and gip.picking_id.picking_type_id.id  == 152:
#                     sql ='''
#                         SELECT id from stock_picking where backorder_id = %s
#                     '''%(gip.picking_id.id)
#                     self.env.cr.execute(sql)
#                     for line in self.env.cr.dictfetchall():
#                         #ITR
#                         pick = self.env['stock.picking'].browse(line['id'])
#                         for move in pick.move_lines:
#                             sql = '''
#                                 UPDATE stock_move set product_qty = %s, product_uom_qty = %s
#                                 WHERE id = %s
#                             '''%(gip.product_uom_qty,gip.product_uom_qty,move.id)
#                             self.env.cr.execute(sql)
#                             move.refresh()
#                             move.stack_id._get_remaining_qty()
#                         pick._total_qty()
            
#             
                        
#                     
                
#             this._get_remaining_qty()
#             for gip in self.move_ids:
#                 if gip.picking_type_id and gip.picking_type_id.id  == 7:
#                     gip.picking_id.action_revert_done()
#                     gip_ids.append(gip.id)
# #  
#             if gip_ids:
#                 sql ='''
#                     UPDATE stock_move set state='done' where id in (%s)
#                 '''%(','.join(map(str,gip_ids)))
#                 self.env.cr.execute(sql)
#             this.refresh()
# #
#             for gip in self.move_ids:
#                 if gip.picking_id and gip.picking_id.picking_type_id.id  == 152:
#                     gip.picking_id.action_revert_done()
#             this._get_remaining_qty()
#             for gip in self.move_ids:
#                 if gip.picking_id.picking_type_id.id == 152:
#                     gip.product_uom_qty = gip.init_qty - round((gip.init_qty * abs(gip.stack_id.avg_deduction/100)),0)
#                     gip.product_qty = gip.product_uom_qty
#                     gip.picking_id._total_qty()   
#                     gip.picking_id.action_done()
#                     this.refresh()
            
            for gip in self.move_ids:
                if gip.picking_id and gip.picking_id.picking_type_id.id  == 152:
                    sql ='''
                        SELECT id from stock_picking where backorder_id = %s
                    '''%(gip.picking_id.id)
                    self.env.cr.execute(sql)
                    for line in self.env.cr.dictfetchall():
                        #ITR
                        pick = self.env['stock.picking'].browse(line['id'])
                        for move in pick.move_lines:
                            for zz in move.stack_id.move_ids:
                                #Gip
                                if zz.picking_id and zz.picking_id.picking_type_id.id  == 104:
                                    sql = '''
                                        UPDATE stock_move set product_qty = %s, product_uom_qty = %s
                                        WHERE id = %s
                                    '''%(gip.product_uom_qty,gip.product_uom_qty,zz.id)
                                    self.env.cr.execute(sql)
                                    zz.refresh()
                                    zz.stack_id._get_remaining_qty()
                                zz.picking_id._total_qty()
                                     
                            #update GIP 
#                             for gip_stack in move.stack_id.move_ids:
#                                 if gip_stack.picking_id.picking_type_id.id  == 7:
#                                     sql = '''
#                                         UPDATE stock_move set product_qty = %s, product_uom_qty = %s
#                                         WHERE id = %s
#                                     '''%(gip.product_uom_qty,gip.product_uom_qty,gip_stack.id)
#                                     self.env.cr.execute(sql)
#                                     gip_stack.refresh()
#                                     gip_stack.stack_id._get_remaining_qty()
#                                     gip_stack.picking_id._total_qty()
#                                     gip_stack.picking_id.state='done'
#                                 pick._total_qty()
    
    @api.model
    def create(self, vals):
        if not vals['name']:
            if 'hopper' in vals and vals['hopper']:
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.stack.hopper.seq') or 'New'
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.sack.seq') or 'New'
        if not vals['date']:
            vals['date'] =  time.strftime(DATE_FORMAT)
        result = super(StockStack, self).create(vals)
        return result
    
    @api.model
    @api.depends('move_ids','move_ids.state','move_ids.product_uom_qty','move_ids.location_id','move_ids.location_dest_id')
    def _get_remaining_qty(self):
        uom_obj = self.env['product.uom']
        for stack in self:
            stack_qty = remaining_qty = 0.0
            rounding = 0.0
            init =0.0
            bag_qty = 0
            for move_line in stack.move_ids:
                qty = uom_obj._compute_qty_obj(move_line.product_uom, move_line.product_uom_qty,
                                   move_line.product_id.uom_id, product_id=move_line.product_id.id)
                init_qty = uom_obj._compute_qty_obj(move_line.product_uom, move_line.init_qty,
                                   move_line.product_id.uom_id, product_id=move_line.product_id.id)
                rounding = move_line.product_id.uom_id.rounding
                if move_line.location_dest_id.usage in ('internal','procurement') and move_line.location_id.usage not in ('internal','procurement') and move_line.state == 'done':
                    remaining_qty += qty 
                    stack_qty += qty
                    init += init_qty
                    bag_qty += move_line.bag_no
                    
                if move_line.location_dest_id.usage not in ('internal') and move_line.location_id.usage in ('internal') and move_line.state == 'done':
                    #kiet: Trừ dòng xuất tiêu thụ ra vì đã trừ rồi
                    if move_line.location_dest_id.usage in ('production') and move_line.location_id.usage in ('internal') and move_line.state == 'done':
                        continue
                    remaining_qty -= qty 
                    init -= init_qty
                    bag_qty -= move_line.bag_no or 0.0
                    
                if move_line.location_dest_id.usage in ('internal') and move_line.location_id.usage in ('internal') and move_line.state == 'done':
                    remaining_qty -= qty 
                    init -= init_qty
                    bag_qty -= move_line.bag_no or 0.0
                
                    
            stack.remaining_qty = float_round(remaining_qty, precision_rounding=rounding)
            stack.stack_qty = float_round(stack_qty, precision_rounding=rounding)
            stack.init_qty = init
            stack.bag_qty = bag_qty
            
    bag_qty = fields.Float(compute='_get_remaining_qty',  string='Bag',store=True, digits=(12, 0),)
    stack_qty = fields.Float(compute='_get_remaining_qty',  string='Basis Weight',store=True, digits=(12, 0),)
    init_qty = fields.Float(compute='_get_remaining_qty',  string='Net Weight',store=True, digits=(12, 0),)
    remaining_qty = fields.Float(compute='_get_remaining_qty',  string='Remain Weight',store=True, digits=(12, 0),)
    name = fields.Char(string='Code', required=False, size=128)
    code = fields.Char(string='code', required=False, size=128)
    date = fields.Date(string="Date")
    zone_id = fields.Many2one('stock.zone', string='Zone',  ondelete='cascade',  copy=False)
    active = fields.Boolean(string='Active',default = True,)
    move_ids = fields.One2many('stock.move', 'stack_id' ,'Move Line',)
    province_id = fields.Many2one('res.country.state','Province',)
    delivery_place_id = fields.Many2one('delivery.place','Delivery Place')
    lock = fields.Boolean(string='Lock',default = False,)
    
    stack_his_ids = fields.Many2many('stock.stack.transfer', 'transfer_stack_rel', 'stack_id', 'transfer_id', string='Stack', readonly=True,)
    product_id = fields.Many2one(related='move_ids.product_id',  string='Product',store=True)
    categ_id = fields.Many2one(related='move_ids.product_id.categ_id',  string='Category',store=True)
    bank_id = fields.Many2one('res.bank', string='Banks', readonly=True)
    mortgage_amount = fields.Monetary(string='Amount',readonly=True, )
    currency_id = fields.Many2one('res.currency', string='Currency')
    limit_qty = fields.Float(string='Limit Qty',digits=(12, 0))
    production_id = fields.Many2one('mrp.production', string='Manufacturing Orders')
    contract_id = fields.Many2one('s.contract', string='SNo.')
    expenses_ids = fields.One2many('expenses.stack', 'stack_id' ,'Expenses')
    loss_ids = fields.One2many('loss.stack', 'stack_id' ,'Los',)
    allocation_npe_ids = fields.One2many('stack.nvp.relation', 'stack_id' ,'Allocation NPE',)
    districts_id = fields.Many2one('res.district', string='Source', ondelete='restrict')
    picking_id = fields.Many2one(related ='move_ids.picking_id',  string='Picking',store=True)
    pledged = fields.Char(string="Pledged.")
    warehouse_id = fields.Many2one(related='zone_id.warehouse_id',  string='Warehouse',store = True)
    stack_type = fields.Selection([('pallet', 'Pallet'), ('stacked', 'Stacked')], string='Stack type', defaul='stacked')
    
    
    @api.multi
    def change_product(self):
        if self.move_ids:
            for move in self.move_ids:
                move.action_cancel()
                move.product_id = self.product_change_id.id
                move.picking_id.product_id = self.product_change_id.id
                move.action_done()
                
    product_change_id = fields.Many2one('product.product', string='Change Product')
    
#     @api.multi
#     def is_code_uniq(self):
#         for stack in self:
#             zone_ids = self.search([('code','=', stack.code),
#                                               ('id','<>', stack.id)])
#             if zone_ids:
#                 return False
#             
#         return True
# 
#     _constraints = [(is_code_uniq, 'Stack Exist', ['name'])]
    
    @api.depends('allocation_npe_ids','allocation_npe_ids.product_qty',)
    def _total_qty(self):
        for order in self:
            total_allocation = 0
            for line in order.allocation_npe_ids:
                total_allocation +=line.product_qty
            order.total_allocation = total_allocation
            order.total_remain = order.remaining_qty - total_allocation
            
    total_allocation = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Allocation Qty',store=True)
    total_remain = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Remain Qty',store=True)
    
    
    @api.model
    @api.depends('move_ids','move_ids.state','move_ids.product_qty','move_ids.product_uom_qty')
    def _get_avg_deduct(self):
        for stack in self:
            init_qty = stack.init_qty
            basis_qty = stack.remaining_qty
            if init_qty:
                stack.avg_deduction = (init_qty- basis_qty)*100 / init_qty
            else:
                stack.avg_deduction = 0.0
            
    avg_deduction = fields.Float(compute='_get_avg_deduct',digits=(16,3) , string = 'Avg Deduction')
    
#     @api.model
#     def name_search(self, name, args=None, operator='ilike', limit=80):
#         args = args or []
#         domain = []
#         stack = self.search(domain + args, limit=limit)
#         return stack.name_get()
        
    
#     @api.model
#     def search(self, args, offset=0, limit=None, order=None, count=False):
#         context = self._context or {}
#          
# #         if context.get('zone_id', False):
# #             args = [('zone_id', '=', context['zone_id']),('lock','=',False)]
# #         ids = super(StockStack, self).search(args, offset, limit, order, count=count)
#         
#         if context.get('product_id', False):
#             args = [('product_id', '=', context['product_id']),('lock','=',False)]
#         ids = super(StockStack, self).search(args, offset, limit, order, count=count)
#         
# #         if context.get('production_id', False):
# #             args = [('production_id', '=', context['production_id'])]
# #             cuano_ids = super(StockStack, self).search(args, offset, limit, order, count=count)
# #             ids += cuano_ids
#         
# #         if context.get('picking_id', False):
# #             scontract_ids =[]
# #             sql ='''
# #                 SELECT si.contract_id
# #                 FROM delivery_order dos JOIN sale_contract sc ON dos.contract_id = sc.id
# #                 JOIN shipping_instruction si ON sc.shipping_id  = si.id
# #                 WHERE picking_id = %s
# #             '''%(context['picking_id'])
# #             self.env.cr.execute(sql)
# #             for line in self.env.cr.dictfetchall():
# #                 scontract_ids.append(line['contract_id'])
# #                 
# #             if scontract_ids:
# #                 args = [('contract_id', 'in', scontract_ids)]
# #                 cuano_ids = super(StockStack, self).search(args, offset, limit, order, count=count)
# #                 ids += cuano_ids
#                 
#         return ids
    
    
    @api.multi
    def btt_expenses(self):
        for this in self:
            for exp in this.expenses_ids:
                if exp.entries_id.id:
                    sql ='''
                        DELETE from account_move where id  = %s;
                    '''%(exp.entries_id.id)
                    self.env.cr.execute(sql)
                 
            sql ='''
                DELETE FROM expenses_stack WHERE stack_id = %s;
                DELETE FROM loss_stack WHERE stack_id = %s;
            '''%(this.id,this.id)
            self.env.cr.execute(sql)
            
            for move in this.move_ids:
                if not move.product_qty:
                    continue
                if move.location_id.usage == 'supplier':
                    if (not move.picking_id) and (not move.picking_id.delivery_place_id):
                        continue
                    for expenses in move.picking_id.delivery_place_id.account_ids:
                        vals = {
                                'date':move.date,
                                'move_id':move.id,
                                'name':expenses.credit_acc_id.name,
                                'product_qty':move.product_qty ,
                                'values':expenses.values,
                                'stack_id':this.id
                                }
                        new_ids = self.env['expenses.stack'].create(vals)
                        #new_ids.shipping_cost_entry()
                            
                if move.location_id.usage == 'transit':
                    for transfer in move.picking_id.picking_transfer_internal_ids:
                        first_qty = 0.0
                        second_qty = move.init_qty or 0.0
                        second_bassis_qty = move.product_qty or 0.0
                        if transfer.picking_transfer_internal_ids:
                            picking_id = transfer.picking_transfer_internal_ids[0].id
                            for move_trans in transfer.move_lines:
                                first_bassis_qty =  move_trans.product_qty or 0.0
                                first_qty = move_trans.init_qty 
                            if second_bassis_qty < first_bassis_qty:
                                vals = {
                                        'picking_id':picking_id,
                                        'first_qty':first_qty or 0.0,
                                        'first_bassis_qty':first_bassis_qty or 0.0,
                                        'second_qty':second_qty or 0.0,
                                        'second_bassis_qty':second_bassis_qty or 0.0,
                                        'loss_qty': abs(second_bassis_qty - first_bassis_qty) or 0.0,
                                        'stack_id':this.id,
                                        'product_id':move.product_id.id,
                                        'product_uom':move.product_uom.id
                                }
                                self.env['loss.stack'].create(vals)
                            if not transfer.delivery_place_id:
                                continue
                            for expenses in transfer.delivery_place_id.account_ids:
                                vals = {
                                    'date':move.date,
                                    'move_id':move.id,
                                    'name':expenses.credit_acc_id.name,
                                    'product_qty':move.product_qty ,
                                    'values':expenses.values,
                                    'stack_id':this.id
                                    }
                                new_ids = self.env['expenses.stack'].create(vals)
                                #new_ids.shipping_cost_entry()
                            

class StackNvpRelation(models.Model):
    _name = "stack.nvp.relation"
    
    @api.depends('stack_id','contract_id')
    def _origin_qty(self):
        for this in self:
            origin_qty = 0.0
            if this.stack_id:
                for line in this.stack_id.stack_line:
                    origin_qty +=line.product_qty
                this.origin_qty = origin_qty
                
    stack_id = fields.Many2one('stock.stack', string='Stack')
    contract_id = fields.Many2one('purchase.contract', string='NPE')
    product_qty = fields.Float('Qty Allocation',digits=(16, 0))
    #origin_qty = fields.Float(compute='_origin_qty',string = 'Original Qty',digits=(16, 0))
    
class StockMove(models.Model): 
    _inherit = "stock.move"
        
    stack_id = fields.Many2one('stock.stack', string='Stack', ondelete='cascade', index=True, copy=False)
    zone_id = fields.Many2one('stock.zone', string='Zone', index=True, copy=False, ondelete='restrict')
    
    grp_id = fields.Many2one('stock.picking', string='GRP', index=True, copy=False, )
    weighbridge = fields.Float('Weigh Bridge')
    
    @api.multi
    @api.onchange('stack_id')
    def onchange_stack(self):
        if not self.stack_id:
            self.update({'zone_id':False})
        else:
            self.update({'zone_id':self.stack_id.zone_id.id})
            
    @api.multi
    @api.onchange('first_weight','second_weight','packing_id','bag_no','tare_weight')
    def onchange_weight(self):
        if not self.packing_id:
            tare_weight = 0.0
            net_weight = (self.first_weight or 0.0) - (self.second_weight or 0.0) - tare_weight
            if net_weight:
                self.update({'tare_weight':tare_weight,'init_qty':net_weight})
        else:
            tare_weight = self.packing_id.tare_weight or 0.0
            tare_weight = round(self.bag_no * tare_weight,0)
            net_weight = (self.first_weight or 0.0) - (self.second_weight or 0.0) - tare_weight
            if net_weight:
                self.update({'tare_weight':tare_weight,'init_qty':net_weight})
            
            
    first_weight = fields.Float(string="First Weight",digits=(12, 0))
    second_weight = fields.Float(string="Second Weight",digits=(12, 0))
    packing_id = fields.Many2one('ned.packing', string='Packing')
    bag_no = fields.Float(string="Bag nos.",digits=(12, 0))
    tare_weight = fields.Float(string="Tare Weight",digits=(12, 0))
    
    @api.multi  
    def create_stack(self):
        for this in self:
            if this.stack_id:
                raise UserError(_('Warning !!!'))
            if not this.zone_id:
                raise UserError(_('Warning !!!'))
            
            var = {
                    'zone_id':this.zone_id.id,
                    'date':time.strftime('%Y-%m-%d'),
                  }
            stack_id = self.env['stock.stack'].create(var)
            this.stack_id = stack_id
        return 1
    
    @api.multi
    def action_done(self):
        for line in self:
            if not line.stack_id:
                continue
            onhand_stack = line.stack_id.init_qty
            if line.location_id.usage == 'internal' and line.location_dest_id.usage == 'internal':
                if onhand_stack < line.init_qty :
                    stt = u''' Stact %s tồn kho: %s nhỏ  hơn lượng xuất : %s''' %(line.stack_id.name,onhand_stack,line.init_qty)
                    raise UserError(_(stt))
            
            #THANH: Update the same stock_move with date done of stock_picking
            #Kiet goi su kien stack
        for move in self:
            super(StockMove,self).action_done()
#             if move.stack_id:
#                 move.stack_id.btt_expenses()
                #kiet kiểm tro tồn kho Stack khong xuất ấm
                    
        
        
        return True
    
#     @api.multi
#     @api.onchange("stack_id")
#     def onchange_stack_id(self):
#         values ={}
#         if not self.stack_id:
#             values = {'product_uom_qty': 0}
#         if self.picking_type_id.code  not in ('incoming','production_in'):
#             values = {'product_uom_qty': self.stack_id.remaining_qty or 0.0}
#         self.update(values)
        
#     @api.model
#     def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
#         context = self._context
#         res = super(StockMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
#         
#         if view_type in ['tree','form']:
#             doc = etree.XML(res['arch'])
#             type = context.get('default_type', False)
#             for node in doc.xpath("//button[@name='create_gdn']"):
#                 node.set('invisible',  '1')
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res
    
        
class StockPickingType(models.Model):
    _inherit = "stock.picking.type"
    
    picking_type_npe_id = fields.Many2one('stock.picking.type', string='Picking type for NPE')
    picking_type_nvp_id = fields.Many2one('stock.picking.type', string='Picking type for NVP')
    stack = fields.Boolean(string="Stack")
    allow_fifo = fields.Boolean(string="Allow Fifo")
    
class StockIncoterms(models.Model):
    _inherit = "stock.incoterms"
 
    type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string='Type', defaul='sale')
    transit_day = fields.Integer(string='Transit day')
    description = fields.Char(string='Description')

class ExpensesStack(models.Model):
    _order = 'create_date desc, id desc'
    _name = "expenses.stack"
    
    def _prepare_account_move_line(self, amount, credit_account_id, debit_account_id,description,picking_id):
        partner_id = self.pool.get('res.partner')._find_accounting_partner(picking_id.partner_id).id or False
        second_currency_id = self.env['res.users'].browse(self.env.uid).company_id.second_currency_id
        currency_id = self.env['res.users'].browse(self.env.uid).company_id.currency_id
        
        
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency,currency_id = aml_obj.with_context(date=self.date).compute_amount_fields(amount, second_currency_id, self.company_id.currency_id)
        
        debit_line_vals = {
            'name': description,
            'product_id': False,
            'quantity': 1,
            'product_uom_id': False,
            'ref': description,
            'partner_id': partner_id,
            'debit': debit or 0,
            'credit': 0,
            'account_id': debit_account_id,
            'currency_id': second_currency_id.id,
            'amount_currency':amount_currency
        }
        credit_line_vals = {
            'name': description,
            'product_id': False,
            'quantity': 1,
            'product_uom_id': False,
            'ref': description,
            'partner_id': partner_id,
            'credit': debit,
            'debit': 0,
            'account_id': credit_account_id,
            'currency_id': second_currency_id.id,
            'amount_currency':amount_currency * (-1)
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    def shipping_cost_entry(self):
        move_ids =[]
        move_obj = self.env['account.move'] 
        for expenses in self:
            if expenses.entries_id:
                continue
            
            for place in expenses.delivery_place_id:
                if not place.account_ids:
                    continue
                for acc in place.account_ids:
                    debit_account_id = acc.debit_acc_id.id
                    credit_account_id = acc.credit_acc_id.id
                    
                amount = expenses.total_values2rd
                name =(expenses.picking_id.name or '') +' - ' +  (expenses.name or '')
                journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            
                move_lines = self._prepare_account_move_line(amount, credit_account_id, debit_account_id,name,expenses.picking_id)
                date = expenses.picking_id.date_done
                new_move_id = move_obj.create({'journal_id': journal_id.id,
                                      'line_ids': move_lines,
                                      'date': date,
                                      'ref': name,
                                      'narration':name})
                new_move_id.post()
                expenses.entries_id = new_move_id
            
        return move_ids
    
    
    @api.depends('product_qty','values')
    def _compute_values(self):
        for order in self:
            order.total_values2rd = order.values * order.product_qty 
            order.total_values = order.second_currency_id.with_context(date=order.date).compute(order.total_values2rd, 
                                                                                                 order.company_currency_id)
            
     
    values = fields.Float(string="Values")
    name = fields.Char('Name')
    stack_id = fields.Many2one('stock.stack', string='Stack')
    product_qty = fields.Float(string="Product Qty")
    total_values = fields.Monetary(compute='_compute_values',string="Total Values",currency_field='company_currency_id')
    total_values2rd = fields.Monetary(compute='_compute_values',string="Total Values",currency_field='second_currency_id')
    date = fields.Date(string="Date")
    company_id = fields.Many2one('res.company', string='Company', 
        required=False, readonly=True, 
        default=lambda self: self.env['res.company']._company_default_get('expenses.stack'))
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    second_currency_id = fields.Many2one('res.currency', related='company_id.second_currency_id', readonly=True)
    move_id = fields.Many2one('stock.move', readonly=True)
    picking_id = fields.Many2one(related='move_id.picking_id',  readonly=True)
    delivery_place_id = fields.Many2one(related='move_id.picking_id.delivery_place_id',  readonly=True)
    entries_id = fields.Many2one('account.move',  'Entries')

class LossStack(models.Model):
    _order = 'create_date desc, id desc'
    _name = "loss.stack"
    
    picking_id = fields.Many2one('stock.picking', string='Picking')
    stack_id = fields.Many2one('stock.stack', string='Stack')
    product_id = fields.Many2one('product.product', string='Product')
    product_uom = fields.Many2one('product.uom', string='UoM')
    first_qty = fields.Float(string="1st Qty")
    first_bassis_qty = fields.Float(string="1st Bassis Qty")
    second_qty = fields.Float(string="2rd Qty")
    second_bassis_qty = fields.Float(string="2rd Bassis Qty")
    loss_qty =fields.Float(string="Loss Qty")
    
    
    
    

