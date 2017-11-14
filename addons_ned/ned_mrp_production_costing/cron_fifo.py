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


class AccountPayment(models.Model):
    _inherit = "account.payment"
    
    @api.model
    def create_account_payment_entries(self,ids=None):
        sql ='''
            select id from account_payment where  payment_date > '2017-01-01' and partner_type ='supplier' and payment_type = 'outbound' 
            and purchase_contract_id is not null and state ='posted'
            and id not in (select payment_id from account_move_line where payment_id is not null)
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            pay = self.env['account.payment'].browse(i['id'])
            pay.cancel()
            pay.post()
        return True
    
class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def action_revert_done(self):
        for pick in self:
            #Kiet delete các stock move của NVL tiêu hao khi Reopen các thành phẩm
            for move in pick.move_lines:
                move.remove_fifo()
        super(StockPicking,self).action_revert_done()

        
        
class StockMove(models.Model):
    _inherit = "stock.move"
    
    
    @api.model
    def cron_update_entries_faq(self,ids=None):
#         location_npe_id = self.env['stock.location'].search([('code','=','NPE - BMT')])
#         location_nvp_id = self.env['stock.location'].search([('code','=','Kho chưa phân bổ - BMT')])  
#         location_dest_id = self.env['stock.location'].search([('code','=','NVP - BMT')]) 
#         
#         stock_move_ids = self.env['stock.move'].search([('state','=','done'),('price_unit','!=',0),
#                               ('entries_id','!=',False),('date','>=','2017-02-01 00:00:00'),
#                               ('location_id','in',(location_npe_id.id,location_nvp_id.id)),('location_dest_id','=',location_dest_id.id)])
#         
#         
#         for move in stock_move_ids:
#             unlink = False
#             for line in move.entries_id.line_ids:
#                 if line.debit:
#                     a = round(move.price_unit * move.product_qty,5)
#                     if round(move.price_unit * move.product_qty,5) - line.debit !=0:
#                         unlink  = True
#                         print str(move.price_unit * move.product_qty) + '-' + str(move.id)
#             if unlink == True:
#                 move.entries_id.button_cancel()
#                 move.entries_id.unlink()
#                 self.get_entries_faq_nvp(move)
        
        date_start = date_stop = False
        sql='''
            select date_start,date_stop from account_period where state ='draft'  order by date_start limit 1
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            date_start = '2017-10-01'
            date_stop = '2017-12-01'
                
        sql ='''
                SELECT price_currency * product_uom_qty as amount , product_uom_qty, date(timezone('UTC',date::timestamp)) date,id
                FROM stock_move where location_dest_id in (73,93)
                    and date(timezone('UTC',date::timestamp)) between '%s' and '%s'
                    and price_currency is not null and product_uom_qty is not null
            '''%(date_start,date_stop)
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            amount = self.env.user.company_id.second_currency_id.with_context(date=i['date']).compute(i['amount'], 
                                                                                                 self.env.user.company_id.currency_id,
                                                                                                 round=5)
            price_unit = amount / i['product_uom_qty']
            line ='''
                Update stock_move
                    set price_unit = %s 
                    where id = %s
            '''%(price_unit,i['id'])
            self.env.cr.execute(line)
        
        
#         sql ='''
#             Update ir_cron set active = false where name = 'Update entries faq'
#         '''
#         self.env.cr.execute(sql)
                
    @api.multi
    def create_entries(self):
        for this in self:
            if this.entries_id:
                this.entries_id.button_cancel()
                this.entries_id.unlink()
            self.get_entries_buonme_hcm(this) 
        
    @api.multi
    def remove_fifo(self):
        for this in self:
            for line in this.fifo_out_ids:
                line.unlink()
#             this.price_unit =0.0
             
            for line in this.fifo_ids:
                line.unlink()
            
            
#             if this.entries_id:
#                 this.entries_id.button_cancel()
#                 this.entries_id.unlink()
            this.compute_fifo()
                
                
class StockMoveAllocation(models.Model):
    _inherit = "stock.move.allocation"
    
    @api.model
    def cron_update_qty_faq_allocation(self,ids=None):
        sql ='''
            SELECT *from npe_nvp_relation where date_fixed between '2017-02-01' and '2017-03-01' and contract_id = 6314
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            sql = '''
                SELECT count(id) dem FROM stock_picking where purchase_contract_id = %s
            '''%(i['contract_id'])
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                if j['dem'] == 0:
                    contract = self.env['purchase.contract'].browse(i['contract_id'])
                    contract.button_cancel()
                    contract.button_draft()
                    contract.button_approve()
                else :
                    contract = self.env['purchase.contract'].browse(i['contract_id'])
                    a = contract.contract_line[0].product_qty
                    qty_im = 0.0
                    sql = '''
                        SELECT total_qty  FROM stock_picking where purchase_contract_id = %s
                    '''%(i['contract_id'])
                    self.env.cr.execute(sql)
                    for k in self.env.cr.dictfetchall():
                        qty_im = k['total_qty']
                    if contract.contract_line and contract.contract_line[0].product_qty != qty_im:
                        contract.button_cancel()
                        contract.button_draft()
                        contract.button_approve()
            
        sql='''
            SELECT * from stock_allocation  where date_allocation between '2017-02-01' and '2017-03-01' 
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            sql = '''
                SELECT count(id) dem FROM stock_picking where allocation_id = %s
            '''%(i['contract_id'])
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                if j['dem'] != 1:
                    contract = self.env['stock.allocation'].browse(i['id'])
                    contract.cancel_allocation()
                    contract.approve_allocation()
                
                else :
                    allocation = self.env['stock.allocation'].browse(i['id'])
                    sql = '''
                        SELECT id, total_init_qty  FROM stock_picking where allocation_id = %s
                    '''%(i['contract_id'])
                    self.env.cr.execute(sql)
                    for j in self.env.cr.dictfetchall():
                        pick = self.env['stock.picking'].browse(j['id'])
                        if allocation.qty_allocation != pick.total_init_qty:
                            allocation.button_cancel()
                            allocation.button_draft()
                            allocation.button_approve()
    
    
    def update_prce_stock_move(self):
        sql ='''
            SELECT id from stock_move where location_dest_id = 73
            and price_currency is not null
            and date between '2017-05-01' and '2017-06-01'
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            move =self.env['stock.move'].browse(i['id'])
            price_unit = self.env.user.company_id.second_currency_id.with_context(date=move.date_order).compute(move.price_currency, 
                                                                                                 self.env.user.company_id.currency_id)
            move.price_unit = price_unit
            
    @api.model
    def cron_update_qty_mrp(self,ids=None):
        mrp = self.env['mrp.production'].search([('state','!=','done')])
        for line in mrp:
            sql = '''
                INSERT into mrp_production_move_ids
                    select %s ,id from stock_move where picking_id in(
                    select id from stock_picking where production_id= %s and picking_type_id =7)
                    and id not in (
                    select move_id from mrp_production_move_ids where production_id = %s)
            '''%(line.id,line.id,line.id)
            self.env.cr.execute(sql)
            sql ='''
                UPDATE stock_move set init_qty = product_uom_qty where id in (
                    SELECT id FROM stock_move where picking_type_id  = 6  
                and product_uom_qty != init_qty
                and production_id = %s
                )
            '''%(line.id)
            self.env.cr.execute(sql)
            line._compute_qty()
#         sql='''
#             SELECT sp.id FROM stock_picking sp
#                 join stock_move sm on sp.id = sm.picking_id
#                 where sp.picking_type_id in (6,7)
#                 and sm.product_id is null
#         '''
#         self.env.cr.execute(sql)
#         for line in self.env.cr.dictfetchall():
#             pick = self.env['stock.picking'].browse(line['id'])
#             for line in pick.move_lines:
#                 sql ='''
#                     UPDATE stock_picking set product_id =%s where id = %s
#                 '''%(pick.id,line.product_id.id)
#                 self.env.cr.execute(sql)
        
        sql ='''
            UPDATE stock_move sm SET production_id= (select production_id
                FROM stock_picking sp where sp.id = sm.picking_id and sp.production_id is not null)
            WHERE sm.id in(
                SELECT id from stock_move where location_dest_id = 20
                    AND production_id is null)
        '''
        self.env.cr.execute(sql) 
        
#         for request_pay in self.env['request.payment'].search([('state','=','paid'),('date','>','2016-09-30')]):
#             payed = False
#             for pay in request_pay.request_payment_ids:
#                 payed += pay.amount 
#             
#             if not payed or payed == 0:
#                 request_pay.state = 'approved'
#                 continue
#         
#         for request_pay in self.env['request.payment'].search([('state','=','approved')]):
#             payed = False
#             for pay in request_pay.request_payment_ids:
#                 payed += pay.amount 
#             
#             if not payed or payed == 0:
# #                 request_pay.state = 'continue'
#                 continue
#             if request_pay.amount_approved == payed:
#                 request_pay.state = 'paid'
#             if request_pay.request_amount == payed:
#                 request_pay.state = 'paid'
#         self.cron_update_qty_faq_allocation()
        return True
        

    
    def fifo_reopen_fifo(self,move_ids):
        for move in self.env['stock.move'].browse(move_ids):
            move.remove_fifo()
            
    def cron_stock_fifo_details(self):
        
        location_id = self.env['stock.location'].search([('code','=','NVP - BMT')])
        location_dest_ids = []
        for destination in self.env['stock.location'].search([('code','=','HCM')]):
            location_dest_ids.append(destination.id)
        
        date_start  = False
        sql='''
            select date_start,date_stop from account_period where state ='draft'  order by date_start limit 1
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            date_start = i['date_start']
        
        date_start = date_start + ' 00:00:00'
        
        outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
                                                      ('state','=','done'),('location_dest_id','in',location_dest_ids),
                                                      ('date','>=',date_start)], order ="date")
        res =[]
        for outgoing in outgoing_ids:
            res.append(outgoing.id)
        if res:
            self.fifo_reopen_fifo(res)
        
        for outgoing in outgoing_ids:
            outgoing.refresh()
            if outgoing.fifo_out:
                continue
            while(not outgoing.fifo_out):
                if outgoing.fifo_out:
                    continue
                 
                incoming_ids = self.env['stock.move'].search([('location_id','!=',location_id.id),('location_dest_id','=',location_id.id),
                           # ('id','!=',90780),
                            ('price_unit','!=',0),('product_id','=',outgoing.product_id.id),('entries_id','!=',False)], order ="date,id")
                 
                flag = False
                for x in incoming_ids:
                    if x.fifo == False:
                        flag = True
                    if x.unfifo_qty <0:
                            flag = False
                         
                if flag:
                    for incoming in incoming_ids:
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
                       
        for outgoing in outgoing_ids:
            outgoing.refresh()
            if outgoing.qty_out_fifo == outgoing.product_uom_qty:
                amount =0
                for fifo in outgoing.fifo_out_ids:
                    amount += fifo.out_qty * fifo.fifo_id.price_unit
                outgoing.price_unit = amount / outgoing.product_uom_qty
        
                 
        return  True
    
    @api.model
    def cron_stock_hcm_cus_fifo(self):
        
        location_id = self.env['stock.location'].search([('code','=','HCM')])
        
        location_dest_ids =[]
        for location_dest in self.env['stock.location'].search([('code','in',('adj_stock','Customers'))]) :
            location_dest_ids.append(location_dest.id)
        
        date_start  = False
        sql='''
            select date_start,date_stop from account_period where state ='draft'  order by date_start limit 1
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            date_start = i['date_start']
        
        date_start = date_start + ' 00:00:00'
        
        outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),('date','>=',date_start),
                                                      ('state','=','done'),('location_dest_id','in',location_dest_ids),
                                                      ], order ="date")
        
        res =[]
        for outgoing in outgoing_ids:
            res.append(outgoing.id)
        if res:
            self.fifo_reopen_fifo(res)
#              
        for outgoing in outgoing_ids:
            outgoing.refresh()
            if outgoing.fifo_out:
                continue
            while(not outgoing.fifo_out):
                if outgoing.fifo_out:
                    continue
                incoming_ids = self.env['stock.move'].search([('location_id','!=',location_id.id),('location_dest_id','=',location_id.id),
                            ('price_unit','!=',0),
                            ('date','>=','2017-01-01 00:00:00'),
                            ('product_id','=',outgoing.product_id.id)], order ="date,id")
                flag = False
                for x in incoming_ids:
                    if  x.fifo == False:
                        flag = True
                    if x.unfifo_qty <0:
                        flag = False
                        
                if flag:
                    for incoming in incoming_ids:
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
                        
                        if qty_fifo <=0:
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
#             
        for outgoing in outgoing_ids:
            outgoing.refresh()
            if outgoing.qty_out_fifo == outgoing.product_uom_qty:
                amount =0
                for fifo in outgoing.fifo_out_ids:
                    amount += fifo.out_qty * fifo.fifo_id.price_unit
                outgoing.price_unit = amount / outgoing.product_uom_qty
#         
        return
    
    @api.model
    def cron_stock_fifo(self,ids=None):
        
        #Kiet: FIfo dành cho hàng đi từ NVP - BMT - > HCM
#         location_id = self.env['stock.location'].search([('code','=','Vật Tư')])
#         location_dest_id = self.env['stock.location'].search([('code','=','Production (Ảo)')]) 
#         self.cron_stock_fifo_details(location_id, location_dest_id)
        
        #Kiet: FIfo dành cho hàng đi từ NVP - BMT - > HCM
        
        self.cron_stock_fifo_details()
#         self.env.cr.commit()
        #kiet: FIFO HCM-> Customer
#         self.cron_stock_hcm_cus_fifo()
        
        return True
        #Kiet: Query nghệp vụ xuất kho.
        