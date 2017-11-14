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
from _ast import Store
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp.tools.float_utils import float_compare, float_round

class request_materials_scale(models.Model):
    _name = 'request.materials.scale'
    
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved')], string='Status',
                     readonly=True, copy=False, index=True, default='draft')
    request_id = fields.Many2one('request.materials',string="Request materials")
    stack_id = fields.Many2one('stock.stack',string="Stack")
    product_id = fields.Many2one('product.product',string="Product")
    product_qty = fields.Float(string="Qty scale")
    date_scale = fields.Date(string="Date",default=fields.Datetime.now)

class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    wh_npe_id = fields.Many2one('stock.location', 'NPE')
    wh_nvp_id =fields.Many2one('stock.location', 'NVP')
    
    

class mrp_bom(models.Model):
    _inherit = 'mrp.bom'
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('code', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('code', operator, name)] + args, limit=limit)
        return recs.name_get()
    

class NvpConsignmentAllocation(models.Model):
    _name ="nvp.consignment.allocation"
    _order = 'id desc' 
    
    qty_allocation = fields.Float(string='Qty Allocation',digits=(12, 0))
    consignment_id = fields.Many2one('consignment.goods.to.processing', string='Consignment',
       readonly=False, states={'draft': [('readonly', False)]}, required=False,)
    qty_consignment = fields.Float(related='consignment_id.total_qty',string='Consignment Qty')
    price_unit = fields.Monetary(related='consignment_id.price_unit',string='Consignment Price',currency_field='second_currency_id')
    product_id = fields.Many2one(related='consignment_id.product_id',string='Product')
    product_uom = fields.Many2one(related='consignment_id.product_id.uom_id',string='UoM')
    qty_contract = fields.Float(related='contract_id.total_qty',string='Contract Qty',store=True)
    price_contract = fields.Float(related='contract_id.price_unit',string='Fix Price',store=True)
    date_contract = fields.Date(related='contract_id.date_order',string='Date Contract')
    contract_id = fields.Many2one('purchase.contract',string="NVP",readonly=True)
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    second_currency_id = fields.Many2one('res.currency',related='company_id.second_currency_id', string="2rd Currency",store=True, readonly=True)
    move_ids = fields.Many2many('account.move','consignment_account_move_ref','move_id','consignment_id','Entries')
    
    def _remain_qty(self):
        for this in self:
            allocation = 0.0
            sql = '''
                SELECT sum (qty_allocation) qty_allocation
            FROM nvp_consignment_allocation
            WHERE consignment_id = %s
            '''%(this.consignment_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                allocation = line['qty_allocation']
            this.remain_qty = this.consignment_id.total_qty - allocation
    
    remain_qty = fields.Float(compute='_remain_qty',digits=(12,0))
    
class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
    
    nvl_consignment_ids = fields.One2many('nvp.consignment.allocation', 'contract_id', string='Consignment Allocation')
    
    @api.depends('nvl_consignment_ids.qty_allocation','nvl_consignment_ids')
    def _remain_consignment_qty(self):
        for this in self:
            allocation = 0.0
            for lines in this.nvl_consignment_ids:
                allocation += lines.qty_allocation or 0.0
            this.remain_consignment_qty = this.total_qty -allocation
    
    remain_consignment_qty = fields.Float(compute='_remain_consignment_qty',digits=(16,0),store = True)
    
    
    def _prepare_move_line(self,line, qty, price_unit, credit_account_id, debit_account_id):
        """
        Generate the account.move.line values to post to track the stock valuation difference due to the
        processing of the given quant.
        """
        company_currency_id = self.env['res.users'].browse(self.env.uid).company_id.currency_id
        second_currency_id = self.env['res.users'].browse(self.env.uid).company_id.second_currency_id
        #valuation_amount = currency_obj.round(line.contract_id.company_id.currency_id, valuation_amount * qty)
        valuation_amount = price_unit * line.qty_consignment
        
        second_ex_rate = 0.0
        sql ='''
            SELECT rate
            FROM res_currency_rate
            where currency_id = %s
            and date(timezone('UTC', name::timestamp)) =  date(timezone('UTC', '%s'::timestamp))
        '''%(second_currency_id.id,line.contract_id.date_order)
        self.env.cr.execute(sql)
        for records in self.env.cr.dictfetchall():
            second_ex_rate = records['rate']
        
        debit = second_currency_id.with_context(date=line.contract_id.date_order).compute(valuation_amount,company_currency_id)
        partner_id = (self.partner_id and self.pool.get('res.partner')._find_accounting_partner(self.partner_id).id) or False
        debit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': line.contract_id and line.contract_id.name or False,
            'partner_id': partner_id,
            'debit': debit or 0.0,
            'credit': 0 or 0.0,
            'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency':valuation_amount,
            'account_id': debit_account_id,
            'currency_id': second_currency_id.id
        }
        credit_line_vals = {
            'name': line.product_id.name,
            'product_id': line.product_id.id,
            'quantity': qty,
            'product_uom_id': line.product_id.uom_id.id,
            'ref': line.contract_id and line.contract_id.name or False,
            'partner_id': partner_id,
            'debit': 0.0,
            'credit': debit or 0.0,
            'second_ex_rate':second_ex_rate or 0.0,
            'amount_currency': (-1) * valuation_amount,
            'account_id': credit_account_id,
            'currency_id': second_currency_id.id
        }
        return [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]
    
    @api.multi
    def entries_adjus(self):
        for this in self:
            move_obj = self.env['account.move']
            nvp_price = this.price_unit
            price_unit = 0.0
            consignment_price =0.0
            for consignment in this.nvl_consignment_ids:
                journal_id = consignment.product_id.categ_id.property_stock_journal.id
                for cos in consignment.consignment_id.processing_line:
                    consignment_price = cos.price_unit
                if nvp_price > consignment_price:
                    acc_dest = this.partner_id.property_account_payable_id.id
                    acc_src = consignment.product_id.categ_id.property_stock_account_tem_categ.id
                    price_unit = nvp_price
                    #But toan từ 331104 -> 331102
                    move_lines = self._prepare_move_line(consignment, consignment.qty_allocation, price_unit, acc_src, acc_dest)
                    new_move_id = move_obj.create({'journal_id': journal_id,
                      'line_ids': move_lines,
                      'date': this.date_order,
                      'ref': consignment.consignment_id.name +';'+ this.name,
                      'narration':consignment.consignment_id.name +';'+ this.name})
                    new_move_id.post()
                    consignment.write({'move_ids': [(4, new_move_id.id)]})
                    #But toan từ 6321 -> 331104
                    acc_dest = consignment.product_id.categ_id.property_stock_account_tem_categ.id
                    acc_src = consignment.product_id.categ_id.property_stock_cogs_export.id
                    price_unit = nvp_price - consignment_price
                    move_lines = self._prepare_move_line(consignment, consignment.qty_allocation, price_unit, acc_src, acc_dest)
                    new_move_id = move_obj.create({'journal_id': journal_id,
                      'line_ids': move_lines,
                      'date': this.date_order,
                      'ref': consignment.consignment_id.name +';'+ this.name,
                      'narration':consignment.consignment_id.name +';'+ this.name})
                    new_move_id.post()
                    consignment.write({'move_ids': [(4, new_move_id.id)]})
                    
                elif nvp_price <consignment.price_unit:
                    acc_dest = consignment.product_id.categ_id.property_stock_cogs_export.id
                    acc_src = this.partner_id.property_account_payable_id.id
                    date = this.date_order
                    price_unit = consignment_price - nvp_price 
                    move_lines = self._prepare_move_line(consignment, consignment.qty_allocation, price_unit, acc_src, acc_dest)
                    new_move_id = move_obj.create({'journal_id': journal_id,
                      'line_ids': move_lines,
                      'date': date,
                      'ref': consignment.consignment_id.name +';'+ this.name,
                      'narration':consignment.consignment_id.name +';'+ this.name})
                    new_move_id.post()
                    consignment.write({'move_ids': [(4, new_move_id.id)]})
                else:
                    return
                
    @api.multi
    def btt_consignment_allocation(self):
        for this in self:
            product_qty = this.total_qty
            allocation = 0.0
            for lines in this.nvl_consignment_ids:
                allocation += lines.qty_allocation
            if product_qty <= allocation:
                continue
            while product_qty !=0:
                flag = False
                
                sql ='''
                    SELECT id,qty_allocation FROM 
                        consignment_goods_to_processing 
                    WHERE state not in('draft','done') 
                        and coalesce(qty_allocation,0) != total_qty
                        and total_qty != 0
                    order by approved_date,id
                '''
                self.env.cr.execute(sql)
                for line in self.env.cr.dictfetchall():
                    flag = True
                    consignment = self.env['consignment.goods.to.processing'].browse(line['id'])
                    receive_qty = consignment.total_qty - (consignment.qty_allocation or 0.0)
                    
                    if receive_qty == 0:
                        continue
                    if product_qty > receive_qty:
                        val ={
                              'consignment_id':line['id'],
                              'contract_id':this.id,
                              'qty_allocation':receive_qty
                        }
                        self.env['nvp.consignment.allocation'].create(val)
                        consignment.qty_allocation += receive_qty
                        product_qty -= receive_qty
                    else:
                        val ={
                                  'consignment_id':line['id'],
                                  'contract_id':this.id,
                                  'qty_allocation':product_qty
                            }
                        self.env['nvp.consignment.allocation'].create(val)
                        consignment.qty_allocation += product_qty
                        product_qty = 0
                if not flag:
                    break
        for this in self:
            for line in this.nvl_consignment_ids:
                for move in line.move_ids:
                    move.button_cancel()
                    move.unlink()
                    
            this.entries_adjus()
    
    
class ConsignmentGoodsToProcessing(models.Model):
    _name ="consignment.goods.to.processing"
    _order = 'id desc'
     
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('consignment.goods.to.processing') 
        result = super(ConsignmentGoodsToProcessing, self).create(vals)
        return result
    
    @api.multi
    def btt_approved(self):
        for this in self:
            this.approved_user_id = self.env.user.id
            if not this.approved_date:
                this.approved_date = time.strftime('%Y-%m-%d')
            warehouse_id = self.env['stock.warehouse'].search([], limit=1)
            for line in this.processing_line:
                price_unit = self.env.user.company_id.second_currency_id.with_context(date=this.approved_date).compute(line.price_unit, 
                                                                                                 self.env.user.company_id.currency_id)
                vals = {
                    'origin':this.name or '', 
                    'name': line.product_id.name or '', 
                    'product_id': line.product_id.id or False, 
                    'price_unit': price_unit,
                    'price_currency':line.price_unit or 0.0,
                    'product_uom': line.product_id.uom_id.id or False, 
                    'product_uom_qty': line.product_qty or 0.0,
                    'product_qty':line.product_qty or 0.0,
                    'location_id': warehouse_id.other_location_loc_id.id or False, 
                    'location_dest_id': warehouse_id.wh_raw_material_loc_id.id or False, 
                    'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 
                    'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                    'company_id': self.env.user.company_id.id, 
                    'state':'draft', 
                    'scrapped': False, 
                    'warehouse_id': warehouse_id.id or False,
                    'consignment_id':this.id,
                }
            #Tao stock move 
            new_move_id = self.env['stock.move'].create(vals)
            new_move_id.action_done()
            this.state= 'approved'
    
    @api.model
    @api.multi
    def _total_qty(self):
        for this in self:
            total_qty = 0
            for line in this.processing_line:
                total_qty +=line.product_qty
            this.total_qty = total_qty
            
    total_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Consignment Qty',store=True)
    product_id = fields.Many2one(related='processing_line.product_id',  string='Product',store= False)
    price_unit = fields.Monetary(related='processing_line.price_unit',  string='Product',store= False,currency_field='second_currency_id')
    
    
    name = fields.Char(string="Name")
    date = fields.Date(string="Create Date",default=fields.Datetime.now)
    request_user_id = fields.Many2one('res.users',string="Request Users",readonly=True)
    approved_user_id = fields.Many2one('res.users',string="Approved Users",readonly=True)
    approved_date = fields.Date(string="Approved Date")
    processing_line = fields.One2many('consignment.goods.to.processing.line','consignment_id',string="Line",readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('cancel', 'Cancelled')], string='Status',
                     readonly=True, copy=False, index=True, default='draft')
    request_material_id = fields.Many2one('request.materials',string="Request Materials",readonly=True)
    company_id  = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    second_currency_id = fields.Many2one('res.currency',related='company_id.second_currency_id', string="2rd Currency",store=True, readonly=True)
    qty_allocation = fields.Float(string="Qty Allcation",digits=(16,0))
    
    
class ConsignmentGoodsToProcessingLine(models.Model):
    _name ="consignment.goods.to.processing.line"
    _order = 'id desc'
     
    consignment_id = fields.Many2one('consignment.goods.to.processing',string="consignment Line",ondelete='cascade',)
    purchase_id = fields.Many2one('purchase.contract',string="NPE", ondelete='cascade',domain="[('qty_received', '!=',0),('type', '!=','purchase'),('state', 'not in',('draft','cancel'))]") 
    price_unit = fields.Monetary(string="Provisional Price",currency_field='second_currency_id')
    #product_qty = fields.Float(related='stack_id.remaining_qty',string = 'Qty')
    product_qty = fields.Float(string = 'Qty',digits=(16,0))
    product_id = fields.Many2one('product.product',string="Product",ondelete='cascade')
    product_uom = fields.Many2one(related='product_id.uom_id',string="UoM")
    second_currency_id = fields.Many2one('res.currency',related='consignment_id.company_id.second_currency_id', string="2rd Currency",store=True, readonly=True)
    
    def _remain_qty(self):
        for this in self:
            allcation_qty = 0.0
            for relation in self.env['npe.nvp.relation'].search([('npe_contract_id','=',this.purchase_id.id)]):
                allcation_qty += relation.product_qty
            this.remain_qty =  this.origin_qty - allcation_qty
            
    remain_qty = fields.Float(compute='_remain_qty',string = 'Remain Qty',digits=(16,0))
    
    @api.multi
    def btt_approve(self):
        npe_nvp_relation = self.env['npe.nvp.relation']
        for this in self:
            if this.product_qty > this.remain_qty:
                raise UserError(_('Qty Allocation < Remain Qty !!!') )
            allocation_qty = this.product_qty
            while allocation_qty >0:
                for stack in this.consignment_id.stack_ids:
                    if stack.total_remain ==0:
                        continue
                    if allocation_qty < stack.remaining_qty:
                        
                        ## tạo npe_nvp_relation
                        new_id = this.purchase_id.copy({'name': 'New','nvp_ids':[],
                       'contract_line':[], 'type':'purchase', 'npe_contract_id':this.purchase_id.id})
                        npe_line = this.purchase_id.contract_line[0]
                        # ràng buộc dữ liệu.
                        
                        vals ={
                                'npe_contract_id':this.purchase_id.id,
                                'contract_id':new_id.id,
                                'product_qty':allocation_qty or 0.0,
                                'type':'temporary'
                                }
                        npe_nvp_relation.create(vals)
                                     
                        npe_line.copy({'product_qty':allocation_qty,'price_unit':this.price_unit,'contract_id':new_id.id})
                        new_id.qty_received = allocation_qty
 
                        # Tạo lien kết stock Stack
                        vals ={
                                'stack_id':stack.id,
                                'contract_id':new_id.id,
                                'product_qty':allocation_qty
                                }
                        self.env['stack.nvp.relation'].create(vals)
                        # Stop While
                        allocation_qty = 0.0
                        break;
                    else:
                         
                        allocation_qty =  allocation_qty - stack.remaining_qty 
                        ## tạo npe_nvp_relation
                        new_id = this.purchase_id.copy({'name': 'New','nvp_ids':[],
                        'contract_line':[], 'type':'purchase', 'npe_contract_id':this.purchase_id.id})
                        npe_line = this.purchase_id.contract_line[0]
                        # ràng buộc dữ liệu.
                         
                        vals ={
                                'npe_contract_id':this.purchase_id.id,
                                'contract_id':new_id.id,
                                'product_qty':stack.remaining_qty or 0.0,
                                'type':'temporary'
                                }
                        npe_nvp_relation.create(vals)
                                     
                        npe_line.copy({'product_qty':stack.remaining_qty,'price_unit':this.price_unit,'contract_id':new_id.id})
                        new_id.qty_received = stack.remaining_qty
 
                        #Tạo lien kết stock Stack
                        vals ={
                                'stack_id':stack.id,
                                'contract_id':new_id.id,
                                'product_qty':stack.remaining_qty
                                }
                        self.env['stack.nvp.relation'].create(vals)




    
    

class RequestMaterialsLine(models.Model):
    _inherit = "request.materials.line"
    _description = "Request Materials Line"
    
    stack_id = fields.Many2one('stock.stack',string ='Stack')
    
    @api.model
    def _get_balance_qty(self):
        for line in self:
            if line.stack_id:
                line.qty_stack = line.stack_id.init_qty or 0.0
            else:
                line.qty_stack = 0
            
    qty_stack = fields.Float(compute='_get_balance_qty',  string='Qty Stack', digits=(12, 0),)

class ShippingInstruction(models.Model):
    _inherit = "shipping.instruction"
     
    mrp_result_ids = fields.One2many('mrp.operation.result.produced.product','si_id')
    
    @api.depends('mrp_result_ids.product_qty','mrp_result_ids.state_kcs','mrp_result_ids.picking_id','mrp_result_ids.picking_id.state')
    def _total_qty(self):
        for order in self:
            qty_mrp = 0
            for line in order.mrp_result_ids:
                if line.picking_id and line.state_kcs == 'approved' and line.picking_id.state== 'done':
                    qty_mrp +=line.product_qty
            order.qty_mrp = qty_mrp
            
    qty_mrp = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Qty Mrp',store=True)
    
    
class MrpOperationResultProducedProduct(models.Model):
    _inherit = 'mrp.operation.result.produced.product'
    
#     @api.depends('packing_id','product_qty')
#     def _compute_qty_bags(self):
#         for order in self:
#             qty_bags = 0
#             if order.packing_id:
#                 qty_bags += order.packing_id.capacity and order.product_qty / order.packing_id.capacity or 0.0
#             order.qty_bags = qty_bags
            
    qty_bags = fields.Float(digits=(12, 0) , string='Bags',)
    si_id = fields.Many2one('shipping.instruction', 'SI')
    
    @api.multi
    def create_kcs(self):
        produced = self
        warehouse_obj = produced.operation_result_id.operation_id.production_id.warehouse_id
        result = produced.operation_result_id
        production_obj = produced.operation_result_id.operation_id.production_id
        product_qty = 0
        company_id = production_obj.company_id.id or False
        move = self.env['stock.move']
        operation_produce = self.env['mrp.production.workcenter.product.produce']
        operation_consumed = self.env['mrp.production.workcenter.consumed.produce']
        if produced.picking_id:
            return
        if produced.product_qty > 0: 
         
            picking_type_id = warehouse_obj.production_in_type_id.id or False
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
             
            if not produced.product_id.property_stock_production.id:
                error = "Production Locations  does not exist."
                raise UserError(_(error))
            location_id = produced.product_id.property_stock_production.id 
            if not warehouse_obj.wh_production_loc_id.id:
                error = "Location Destination does not exist."
                raise UserError(_(error))
            #location_dest_id = warehouse_obj.wh_production_loc_id.id
            location_dest_id = warehouse_obj.wh_finished_good_loc_id.id
            for bom_material in result.operation_id.production_id.bom_id.bom_stage_lines.bom_stage_material_line:
                val ={
                    'product_id':bom_material.product_id.id,
                    'product_uom':bom_material.product_uom.id,
                    'date_consumed':time.strftime('%Y-%m-%d'),
                    'operation_result_id':result.id,
                    'check_kcs':False,
                    'product_qty':0.0,
                    'finished_id':produced.id
                    }
                self.env['mrp.operation.result.consumed.product'].create(val)
             
         
            product_qty += produced.product_qty
            # Kiệt: Create nhập kho Thành phẩm Thêm Picking để KCS NED
            var = {
                'name':produced.pending_grn or False,
                'picking_type_id': picking_type_id,
                'partner_id': False,
                'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                'date_sent': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                'origin': produced.pending_grn or False,
                'location_dest_id': location_dest_id,
                'location_id': 7,
                'state':'draft',
                'production_id':production_obj.id,
                'operation_id':result.operation_id.id,
                'result_id':result.id,
                'note':produced.notes
            }
            picking_id = self.env['stock.picking'].create(var)
            move.create({'picking_id': picking_id.id, 'name': produced.product_id.name or '', 'product_id': produced.product_id.id or False,
                'product_uom': produced.product_uom.id or False, 
                'init_qty':produced.product_qty or 0.0,
                'product_uom_qty': produced.product_qty or 0.0, 'price_unit': 0.0,
                'picking_type_id': picking_type_id or False, 'location_id': location_id or False, 'production_id': production_obj.id,
                'location_dest_id': location_dest_id or False, 'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                'date': time.strftime('%Y-%m-%d %H:%M:%S') or False, 'type': picking_type.code or False, 'result_id': result.id,
                'zone_id':produced.zone_id and produced.zone_id.id or False,
                'packing_id':produced.packing_id.id,
                'bag_no':produced.qty_bags or 0.0,
                'company_id': company_id, 'state':'draft', 'scrapped': False, 'warehouse_id': warehouse_obj.id or False})
            picking_id.action_confirm()
             
            produced.picking_id = picking_id.id
            #self.env['mrp.operation.result.produced.product'].write(produced.id,{'picking_id':picking_id.id})
            operation_produce_id = operation_produce.search([('operation_id','=',result.operation_id.id),('product_id','=',produced.product_id.id)])
            if operation_produce_id:
                operation_produce_id.check_kcs =False
            else:
                operation_produce.create({'check_kcs':False,'product_id': produced.product_id.id or False, 'product_uom': produced.product_uom.id or False,
                    'operation_id': result.operation_id.id})
             
        #     Kiet: Tạo nguyên vật liệu tiêu hao       
        for bom_material in result.operation_id.production_id.bom_id.bom_stage_lines.bom_stage_material_line:
            operation_consumed_id = operation_consumed.search([('operation_id','=',result.operation_id.id),('product_id','=',bom_material.product_id.id)])
            if operation_consumed_id:
                operation_consumed_id.check_kcs =False
            else:
                val = {
                    'product_id':bom_material.product_id.id,
                    'product_uom':bom_material.product_uom.id,
                    'operation_id':result.operation_id.id,
                    'check_kcs':False,
                    'product_qty':0
                }
                operation_consumed.create(val)
    
    @api.multi
    @api.onchange('packing_id','product_qty')
    def onchange_packing(self):
        if not self.packing_id:
            self.update({'qty_bags':0.0})
        else:
            qty_bags = self.packing_id.capacity and self.product_qty / self.packing_id.capacity or 0.0
            self.update({'qty_bags':qty_bags})
            

class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _order = 'id desc'
    
    @api.multi
    def set_to_production_started(self):
        mrp = self
        for move in mrp.move_lines2:
            move.state= 'draft'
            move.unlink()
        mrp.state ='in_production'
    
    def get_datetime(self, date):
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y')
    
    @api.depends('date_planned')
    def _compute_date(self):
        for line in self:
            if line.date_planned:
                line.day_tz = line.date_planned
                line.year_tz = self.get_datetime(line.date_planned)
            else:
                line.day_tz = False
                line.year_tz = False
    
    day_tz = fields.Date(compute='_compute_date',string = "Day tz", store=True)
    year_tz = fields.Char(compute='_compute_date',string = "Year tz", store=True)
    
    @api.model
    def default_get(self, fields):
        rec = super(MrpProduction, self).default_get(fields)
        return rec

    @api.model
    def create(self, vals):
        result = super(MrpProduction, self).create(vals)
        return result
    
    @api.depends('move_lines','move_lines.state','move_lines.product_uom_qty','move_lines.init_qty','move_lines2',
                 'move_lines2.product_uom_qty','move_created_ids2','move_created_ids2.product_uom_qty','move_created_ids2.state',
                 'move_created_ids2.init_qty')
    def _compute_qty(self):
        for production in self:
            product_issued = 0.0
            product_basis_issued =0.0
            product_received =0.0
            for consumed in production.move_lines:
                if consumed.state !='done':
                    continue
                product_issued += consumed.init_qty or 0.0
                product_basis_issued += consumed.product_qty or 0.0
                    
            for produced in production.move_created_ids2:
                product_received += produced.init_qty or 0.0
            
            production.product_basis_issued  = product_basis_issued
            production.product_issued = product_issued
            production.product_received =product_received
            production.product_balance = product_issued - (product_received )
            
    product_issued = fields.Float(compute='_compute_qty', string='Issue', store= True, digits=(12, 0))
    product_basis_issued = fields.Float(compute='_compute_qty',store= True, string='Basis Issue', digits=(12, 0))
    product_received = fields.Float(compute='_compute_qty', store= True, string='Received', digits=(12, 0))
    product_balance = fields.Float(compute='_compute_qty', store= True, string='Balance',digits=(12, 0))
    
    npe_nvp_consume_ids = fields.Many2many('stock.move', 'mrp_npe_nvp_consume_ids', 'production_id', 'move_id', 'NPE NVP consume',
            readonly=True, states={'draft':[('readonly', False)]})
    
    npe_nvp_produced_ids = fields.Many2many('stock.move', 'mrp_npe_nvp_produced_ids', 'production_id', 'move_id', 'NPE NVP produced',
            readonly=True, states={'draft':[('readonly', False)]})
            
    @api.multi
    def action_done(self):
         
        for production in self:
             
            new_ids = []
            for line in production.move_lines:
                new_id = line.copy({'location_id':line.location_dest_id.id,'location_dest_id':line.product_id.property_stock_production.id,
                    'stack_id':False,'zone_id':False,'picking_id':False,'picking_type_id':False,'production_id':production.id,
                    'origin':line.picking_id.name,'note':production.name})
                new_ids.append(new_id.id)
                new_id.action_done()
            production.write({'move_lines2':[[6,0,new_ids]]})
#              
#             #work order
#             for work in production.workcenter_lines:
#                 work.action_done()
        production.date_finished = time.strftime('%Y-%m-%d')
        self.state ='done'
        #super(MrpProduction, models.Model).action_done()
       #self.allocationconsumed()
    
    def onhand_nvp_npe(self,product_id,location_id):
        onhand_qty =0.0
        sql = '''
            SELECT foo.product_id, 
            sum(start_onhand_qty) start_onhand_qty
            From
                (SELECT
                    stm.product_id,
                    case when loc1.usage != 'internal' and loc2.usage = 'internal' 
                        and loc2.id = (%(loc2)s)
                    then stm.product_qty
                    else
                    case when loc1.usage = 'internal' and loc2.usage != 'internal'
                        and loc1.id = (%(loc1)s)
                    then -1*stm.product_qty 
                    else 0.0 end
                    end start_onhand_qty
                     
                FROM stock_move stm 
                    join stock_location loc1 on stm.location_id=loc1.id
                    join stock_location loc2 on stm.location_dest_id=loc2.id
                WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
            GROUP BY foo.product_id
         '''%({
                'product_id': product_id,
                'loc2': location_id,
                'loc1': location_id,
            })
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            onhand_qty = i['start_onhand_qty'] or 0.0
        return onhand_qty
    
    def allocationconsumed(self):
        for production in self:
            nvp_location_id = production.warehouse_id.wh_nvp_id.id
            npe_location_id = production.warehouse_id.wh_npe_id.id
            proc_obj = self.env['procurement.order']
            procurement = proc_obj.search([('production_id', '=', production.id)])
            data = {}
            #Delete và đổ lại dữ liệu
            move_ids =[]
            for move in production.move_lines:
                falg = True
                for line in move_ids:
                    if move.product_id.id == line['product_id']:
                        line['product_qty'] +=  move.product_uom_qty
                        line['init_qty'] +=  move.init_qty
                        falg =False
                if falg:
                    move_ids.append({
                        'product_id':move.product_id.id,
                        'product_qty':move.product_uom_qty,
                        'init_qty':move.init_qty,
                    })
                    
            for move in move_ids:
                product_id = self.env['product.product'].browse(move['product_id'])
                qty_onhand = self.onhand_nvp_npe(product_id.id, nvp_location_id)
                if move['product_qty'] < qty_onhand:
                    data.update({
                        'product_uom_qty':move['product_qty'],
                        'location_id':nvp_location_id,
                        'name': production.name, 
                        'date': production.date_planned,
                        'product_id': product_id.id,
                        'product_uom': product_id.uom_id.id, 
                        'picking_type_id': production.warehouse_id.production_out_type_id.id,
                        'group_id': procurement and procurement.group_id.id,
                        'location_dest_id': product_id.property_stock_production.id or False, 
                        'move_dest_id': production.move_prod_id.id,
                        'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                        'production_id': production.id, 'origin': production.name, 
                        'state': 'waiting'})
                    move_id = self.env['stock.move'].create(data)
                    move_id.action_done();
                    production.write({'npe_nvp_consume_ids': [(4, move_id.id)]})
                else:
                    if qty_onhand == 0:
                        data.update({
                            'product_uom_qty':move['product_qty'],
                            'location_id':npe_location_id,
                            'name': production.name, 
                            'date': production.date_planned,
                            'product_id': product_id.id,
                            'product_uom': product_id.uom_id.id,
                            'picking_type_id': production.warehouse_id.production_out_type_id.id,
                            'group_id': procurement and procurement.group_id.id,
                            'location_dest_id': product_id.property_stock_production.id or False, 
                            'move_dest_id': production.move_prod_id.id,
                            'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                            'production_id': production.id, 'origin': production.name, 
                            'type':'production_out',
                            'state': 'waiting'})
                        move_id = self.env['stock.move'].create(data)
                        move_id.action_done();
                        production.write({'npe_nvp_consume_ids': [(4, move_id.id)]})
                    else:
                        data.update({
                            'product_uom_qty':qty_onhand,
                            'location_id':nvp_location_id,
                            'name': production.name, 
                            'date': production.date_planned,
                            'product_id': product_id.id,
                            'product_uom': product_id.uom_id.id, 
                            'picking_type_id': production.warehouse_id.production_out_type_id.id,
                            'group_id': procurement and procurement.group_id.id,
                            'location_dest_id': product_id.property_stock_production.id or False, 
                            'move_dest_id': production.move_prod_id.id,
                            'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                            'production_id': production.id, 'origin': production.name, 
                            'type':'production_out',
                            'state': 'waiting'})
                        move_id = self.env['stock.move'].create(data)
                        move_id.action_done();
                        production.write({'npe_nvp_consume_ids': [(4, move_id.id)]})
                        
                        data.update({
                            'product_uom_qty':move['product_qty'] - qty_onhand,
                            'location_id':npe_location_id,
                            'name': production.name, 
                            'date': production.date_planned,
                            'product_id': product_id.id,
                            'product_uom': product_id.uom_id.id, 
                            'picking_type_id': production.warehouse_id.production_out_type_id.id,
                            'group_id': procurement and procurement.group_id.id,
                            'location_dest_id': product_id.property_stock_production.id or False, 
                            'move_dest_id': production.move_prod_id.id,
                            'procurement_id': procurement and procurement.id, 
                            'company_id': production.company_id.id,
                            'production_id': production.id, 'origin': production.name, 
                            'type':'production_out',
                            'state': 'waiting'})
                        move_id = self.env['stock.move'].create(data)
                        move_id.action_done();
                        production.write({'npe_nvp_consume_ids': [(4, move_id.id)]})
                ##npe_nvp_move_ids
            
            move_ids =[]
            for move in production.move_created_ids2:
                falg = True
                for line in move_ids:
                    if move.product_id.id == line['product_id']:
                        line['product_qty'] +=  move.product_uom_qty
                        line['init_qty'] +=  move.init_qty
                        falg =False
                if falg:
                    move_ids.append({
                        'product_id':move.product_id.id,
                        'product_qty':move.product_uom_qty,
                        'init_qty':move.init_qty,
                    })
                    
            qty_npe = 0
            qty_nvp =0
            for move in production.npe_nvp_consume_ids:
                if move.location_id.id == production.warehouse_id.wh_nvp_id.id:
                    qty_nvp += move.product_uom_qty
                else:
                    qty_npe += move.product_uom_qty
            
            
            for move in move_ids:
                product_id = self.env['product.product'].browse(move['product_id'])
                
                product_qty_nvp = move['product_qty'] * qty_nvp / (qty_npe + qty_nvp)
                product_qty_npe = move['product_qty'] * qty_npe / (qty_npe + qty_nvp)
                
                if product_qty_nvp:
                    data={}
                    data.update({
                        'product_uom_qty':product_qty_nvp,
                        'location_id':nvp_location_id,
                        'name': production.name, 
                        'date': production.date_planned,
                        'product_id': product_id.id,
                        'product_uom': product_id.uom_id.id, 
                        'picking_type_id': production.warehouse_id.production_in_type_id.id,
                        'group_id': procurement and procurement.group_id.id,
                        'location_dest_id': product_id.property_stock_production.id or False, 
                        'move_dest_id': production.move_prod_id.id,
                        'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                        'production_id': production.id, 'origin': production.name, 
                        'state': 'waiting'})
                    move_id = self.env['stock.move'].create(data)
                    move_id.action_done();
                    production.write({'npe_nvp_produced_ids': [(4, move_id.id)]})
                
                if product_qty_npe:
                    data={}
                    data.update({
                        'product_uom_qty':product_qty_npe,
                        'location_id':npe_location_id,
                        'name': production.name, 
                        'date': production.date_planned,
                        'product_id': product_id.id,
                        'product_uom': product_id.uom_id.id, 
                        'picking_type_id': production.warehouse_id.production_in_type_id.id,
                        'group_id': procurement and procurement.group_id.id,
                        'location_dest_id': product_id.property_stock_production.id or False, 
                        'move_dest_id': production.move_prod_id.id,
                        'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                        'production_id': production.id, 'origin': production.name, 
                        'state': 'waiting'})
                    move_id = self.env['stock.move'].create(data)
                    move_id.action_done();
                    production.write({'npe_nvp_produced_ids': [(4, move_id.id)]})
    
class MrpProductionWorkcenterConsumedProduce(models.Model):
    _name = 'mrp.production.workcenter.consumed.produce'
    
    @api.depends('check_kcs')
    def _product_qty(self):
        for result in self:
            if not result.operation_id:
                continue
            if result.check_kcs:
                continue
            sql ='''
                SELECT sum(morpp.product_qty) product_qty
                FROM mrp_operation_result mor 
                    join mrp_operation_result_produced_product morpp on mor.id = morpp.operation_result_id
                    join mrp_production_workcenter_line mpwl on mpwl.id = mor.operation_id
                    join stock_picking sp on morpp.picking_id = sp.id
                WHERE mpwl.id= %s
                    and sp.state_kcs !='rejected'
            '''%(result.operation_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                result.product_qty = line['product_qty'] or 0.0
                result.check_kcs = True
                
    product_id =fields.Many2one('product.product', 'Product', required=False)
    product_uom = fields.Many2one('product.uom', 'Uom', required=False)
    operation_id = fields.Many2one('mrp.production.workcenter.line', 'Operation')
    product_qty = fields.Float(compute='_product_qty',string ='Product Qty',digits=(12, 0),store = True)
    check_kcs = fields.Boolean(string='Check Update Qty Kcs',default=False)


class MrpOperationResultConsumedProduct(models.Model):
    _inherit = 'mrp.operation.result.consumed.product'

    @api.depends('check_kcs')
    def _product_qty(self):
        for result in self:
            if result.check_kcs:
                continue
            if not result.operation_result_id:
                continue
            
            for lines in result.operation_result_id.produced_products:
                if lines.picking_id.state_kcs !='rejected' and lines.id == result.finished_id.id:
                    result.product_qty = lines.product_qty
            
            result.check_kcs =True
                    
    product_qty = fields.Float(compute='_product_qty',string ='Product Qty',digits=(12, 0),store = True)
    check_kcs = fields.Boolean(string='Check Update Qty Kcs',default=False)
    finished_id =fields.Many2one('mrp.operation.result.produced.product',string="Finish Good")
    
class MrpProductionWorkcenterProductProduce(models.Model):
    _inherit = 'mrp.production.workcenter.product.produce'
    
    @api.depends('check_kcs')
    def _product_qty_ned(self):
        for result in self:
            if result.check_kcs:
                continue
            sql ='''
                SELECT sum(morpp.product_qty) product_qty
                FROM mrp_operation_result mor 
                    join mrp_operation_result_produced_product morpp on mor.id = morpp.operation_result_id
                    join mrp_production_workcenter_line mpwl on mpwl.id = mor.operation_id
                    join stock_picking sp on morpp.picking_id = sp.id
                WHERE mpwl.id= %s
                    and sp.state_kcs !='rejected'
                    and morpp.product_id = %s
            '''%(result.operation_id.id,result.product_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                result.product_qty = line['product_qty'] or 0.0
                result.check_kcs = True
                
    product_qty = fields.Float(compute='_product_qty_ned',string ='Product Qty',digits=(12, 0),store = True)
    check_kcs = fields.Boolean(string='Check Update Qty Kcs',default=False)
    

class StockMove(models.Model): 
    _inherit = "stock.move"
    
    #Kiet: Liên kết picking thành phẩm với stock move xuất kho NVL để tiêu thụ
    picking_finished_id = fields.Many2one('stock.picking', string='Picking finished', ondelete='cascade', index=True, copy=False)
    #Kiet: Lien ket muon hang cua stock move
    consignment_id = fields.Many2one('consignment.goods.to.processing', string='Consignment', ondelete='cascade', index=True, copy=False)
    
    npe_nvp_move_ids = fields.Many2many('stock.move','move_production_ref','move_id','mrp_move_ids','Move',readonly=True)
    
    @api.multi
    def action_done(self):
        #:Kiet Nghiệp vụ nhập hàng vào hopper hệ thống tự động tạo ra 1 phiếu request
        for move in self:
            if move.product_id.flag_standard_cost == True and move.zone_id.name =='HOPPER':
                val ={
                      'name':'/',
                      'origin':move.picking_id.name,
                      'state':'draft'
                      }
                request_id = self.env['request.materials'].create(val)
                val ={
                        'product_id':move.product_id.id,
                        'product_uom':move.product_id.uom_id.id,
                        'product_qty':move.init_qty,
                        'stack_id':move.stack_id.id,
                        'request_id':request_id.id
                      }
                self.env['request.materials.line'].create(val)
        return super(StockMove,self).action_done()
        
        
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    #Kiet: Lien ket muon hang cua stock picking với phiếu mượn hàng
    consignment_id = fields.Many2one('consignment.goods.to.processing','Consignment goods')
    real_mc = fields.Float(string="Real MC",digits=(12, 2))
    real_weight = fields.Float(string="Real Wweight",digits=(12, 0))
    
    @api.multi
    def action_request_materials(self):
        for pick in self:
            start_onhand_qty =0.0
            if pick.picking_type_id.code == 'production_out' and pick.location_id.usage == 'internal':
                if pick.consignment_id:
                    raise UserError(_('Request for %s: %s was exist.')%(pick.name,pick.consignment_id.name))
                #Kiệt: Kiểm tra tồn kho để xuất NVl vào sản xuất 
                for move in pick.move_lines:
                    sql = '''
                        SELECT foo.product_id, 
                        sum(start_onhand_qty) start_onhand_qty
                        From
                            (SELECT
                                stm.product_id,
                                case when loc1.usage != 'internal' and loc2.usage = 'internal' 
                                    and loc2.id = (%(loc2)s)
                                then stm.product_qty
                                else
                                case when loc1.usage = 'internal' and loc2.usage != 'internal'
                                    and loc1.id = (%(loc1)s)
                                then -1*stm.product_qty 
                                else 0.0 end
                                end start_onhand_qty
                                 
                            FROM stock_move stm 
                                join stock_location loc1 on stm.location_id=loc1.id
                                join stock_location loc2 on stm.location_dest_id=loc2.id
                            WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
                        GROUP BY foo.product_id
                     '''%({
                            'product_id': move.product_id.id,
                            'loc2': move.location_id.id,
                            'loc1': move.location_id.id,
                        })
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        start_onhand_qty = i['start_onhand_qty'] or 0.0
            if move.product_qty > start_onhand_qty:
                vals ={
                        'date': time.strftime('%Y-%m-%d %H:%M:%S') ,
                        'request_user_id': self.env.uid,
                        'request_material_id':pick.request_materials_id.id
                   }
                consignment_id = self.env['consignment.goods.to.processing'].create(vals)
                pick.consignment_id = consignment_id.id
                for move in pick.move_lines:
                    vals={
                          'product_id':move.product_id.id,
                          'product_qty': move.product_qty - start_onhand_qty,
                          'consignment_id':consignment_id.id
                          }
                    self.env['consignment.goods.to.processing.line'].create(vals)
            else:
                raise UserError(_(u'Đã có hàng trong kho'))
            
    @api.multi
    def action_revert_done(self):
        for pick in self:
            #Kiet delete các stock move của NVL tiêu hao khi Reopen các thành phẩm
            move_ids = self.env['stock.move'].search([('picking_finished_id','=',pick.id)])
            if move_ids:
                move_ids.unlink()
        super(StockPicking,self).action_revert_done()
    
    def onhand_nvp_npe(self,product_id,location_id):
        start_onhand_qty =0.0
        sql = '''
            SELECT foo.product_id, 
            sum(start_onhand_qty) start_onhand_qty
            From
                (SELECT
                    stm.product_id,
                    case when loc1.usage != 'internal' and loc2.usage = 'internal' 
                        and loc2.id = (%(loc2)s)
                    then stm.product_qty
                    else
                    case when loc1.usage = 'internal' and loc2.usage != 'internal'
                        and loc1.id = (%(loc1)s)
                    then -1*stm.product_qty 
                    else 0.0 end
                    end start_onhand_qty
                     
                FROM stock_move stm 
                    join stock_location loc1 on stm.location_id=loc1.id
                    join stock_location loc2 on stm.location_dest_id=loc2.id
                WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
            GROUP BY foo.product_id
         '''%({
                'product_id': product_id,
                'loc2': location_id,
                'loc1': location_id,
            })
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            start_onhand_qty = i['start_onhand_qty'] or 0.0
        return start_onhand_qty
    
#     @api.multi
#     def action_done(self):
#         super(StockPicking,self).action_done()
#         location_dest_id = self.env['stock.location'].search([('usage','=','inventory'),('scrap_location','=',False)])
#         for picking in self:
#             qty_onhand = 0.0
#             if picking.picking_type_id.code == 'production_in' and picking.location_dest_id.usage == 'internal':
#                 #Kiet. Tạo Cắt kho NVP.
#                 nvp_location_id = picking.picking_type_id.picking_type_nvp_id.default_location_src_id.id
#                 npe_location_id = picking.picking_type_id.picking_type_npe_id.default_location_src_id.id
#                 #for move in picking.move_lines:
#                     #Kiet: kiem tra ton kho NVP
# #                     qty_onhand = self.onhand_nvp_npe(move.product_id.id, nvp_location_id)
# #                     if not qty_onhand:
# #                         qty_onhand = self.onhand_nvp_npe(move.product_id.id, npe_location_id)
# #                         if not  qty_onhand:
# #                             raise
#                     
#                 
#                 
#                 
#                 
#                 #Kiet:Tao mat mat 
#                 qty_los = 0.0
#                 total_basis =0
#                 consumed_qty =0.0
#                 qty = 0.0
#                 for move in picking.production_id.move_lines:
#                     for los in  move.stack_id.loss_ids:
#                         if los.second_bassis_qty < los.fist_bassis_qty:
#                             qty_los += los.loss_qty
#                     total_basis += move.product_qty
#                 
#                 for move in picking.move_lines:
#                     consumed_qty +=move.product_qty
#                 
#                 if qty_los and total_basis:
#                     qty = consumed_qty * qty_los / total_basis
#                 
#                 if not qty:
#                     continue
#                 vals = {'name': move.product_id.name or '', 
#                         'product_id': move.product_id.id or False, 
#                         'product_uom': move.product_uom.id or False, 
#                         'product_uom_qty': qty or 0.0,
#                         'product_qty': qty or 0.0,
#                         'location_id': move.location_id.id or False, 
#                         'production_id': picking.production_id.id or False,
#                         'location_dest_id': location_dest_id and location_dest_id.id or False, 
#                         'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 
#                         'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
#                         'company_id': picking.production_id.company_id.id, 
#                         'state':'done', 
#                         'stack_id':move.stack_id.id,
#                         'scrapped': False, 
#                         'warehouse_id': picking.production_id.warehouse_id.id or False,
#                         }
#                 
#                 new_move_id = self.env['stock.move'].create(vals)
#                 picking.production_id.move_loss_ids= [(4, new_move_id.id)]
#                 new_move_id.action_done()
    
    
        
#     @api.multi
#     def do_transfer(self):
#         super(StockPicking, self).do_transfer()
#         for picking in self:
#             if picking.production_id:
#                 start_onhand_qty =0.0
#                 if picking.picking_type_id.code == 'production_out' and picking.location_id.usage == 'internal':
#                     #Kiệt: Kiểm tra tồn kho để xuất NVl vào sản xuất 
#                     for move in picking.move_lines:
#                         sql = '''
#                             SELECT foo.product_id, 
#                             sum(start_onhand_qty) start_onhand_qty
#                             From
#                                 (SELECT
#                                     stm.product_id,
#                                     case when loc1.usage != 'internal' and loc2.usage = 'internal' 
#                                         and loc2.id = (%(loc2)s)
#                                     then stm.product_qty
#                                     else
#                                     case when loc1.usage = 'internal' and loc2.usage != 'internal'
#                                         and loc1.id = (%(loc1)s)
#                                     then -1*stm.product_qty 
#                                     else 0.0 end
#                                     end start_onhand_qty
#                                      
#                                 FROM stock_move stm 
#                                     join stock_location loc1 on stm.location_id=loc1.id
#                                     join stock_location loc2 on stm.location_dest_id=loc2.id
#                                 WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
#                             GROUP BY foo.product_id
#                          '''%({
#                                 'product_id': move.product_id.id,
#                                 'loc2': move.location_id.id,
#                                 'loc1': move.location_id.id,
#                             })
#                         self.env.cr.execute(sql)
#                         for i in self.env.cr.dictfetchall():
#                             start_onhand_qty = i['start_onhand_qty'] or 0.0
                    
                        #Kiệt: Không cho xuất khi NVL không có hàng
#                         if move.product_qty > start_onhand_qty:
#                             chuoi = u'''%s - của sản phầm %s  tồn kho : %s, Còn thiếu: %s'''%(move.location_id.name,move.product_id.name,
#                                                                                                   move.product_qty,move.product_qty - start_onhand_qty)
#                             raise UserError(_('%s') % (chuoi))
                    
                    #Kiet:Tao mat mat 
#                     for move in picking.production_id.move_lines:
#                         location_dest_id = self.env['stock.location'].search([('usage','=','inventory'),('scrap_location','=',False)])
#                         for loss in move.stack_id.loss_ids:
#                             move_loss = self.env['stock.move'].search([('production_id','=',picking.production_id.id),('stack_id','=',move.stack_id.id),('location_id','=',move.location_id.id),('location_dest_id','=',location_dest_id.id)])
#                             if move_loss:
#                                 continue
#                             vals = {'name': move.product_id.name or '', 
#                                     'product_id': move.product_id.id or False, 
#                                     'product_uom': move.product_uom.id or False, 
#                                     'product_uom_qty': loss.loss_qty or 0.0,
#                                     'product_qty': loss.loss_qty or 0.0,
#                                     'location_id': move.location_id.id or False, 
#                                     'production_id': picking.production_id.id or False,
#                                     'location_dest_id': location_dest_id and location_dest_id.id or False, 
#                                     'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 
#                                     'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
#                                     'company_id': picking.production_id.company_id.id, 
#                                     'state':'done', 
#                                     'scrapped': False, 
#                                     'warehouse_id': picking.production_id.warehouse_id.id or False,
#                                     }
#                          
#                             new_move_id = self.env['stock.move'].create(vals)
#                             picking.production_id.move_loss_ids= [(4, new_move_id.id)]
#                             new_move_id.action_done()
                        
                #Kiet: tốn NVL tiêu hao khi nhập thành phẩm
#                 if picking.picking_type_id.code == 'production_in' and picking.location_dest_id.usage == 'internal':
#                     for move in picking.move_lines:
#                         product_qty = move.product_qty
# #                         while product_qty !=0:
#                             sql ='''
#                                 SELECT sum(product_qty) product_qty,sm.product_id
#                                     FROM stock_move sm join mrp_production_move_ids refs on sm.id = refs.move_id
#                                     WHERE refs.production_id = %s
#                                     group by sm.product_id
#                                     order by sm.product_id
#                             '''%(picking.production_id.id)
#                             self.env.cr.execute(sql)
#                             for nvl in self.env.cr.dictfetchall():
#                                 sql ='''
#                                     SELECT sum(product_qty) product_qty
#                                         FROM stock_move sm join mrp_production_consumed_products_move_ids refs on sm.id = refs.move_id
#                                         WHERE refs.production_id = %s
#                                             and sm.product_id = %s
#                                 '''%(picking.production_id.id,nvl['product_id'])
#                                 self.env.cr.execute(sql)
#                                 for consumed in self.env.cr.dictfetchall():
#                                     consumed = consumed['product_qty'] or 0.0
#                                      
#                                 if nvl['product_qty'] > consumed:
#                                     qty = nvl['product_qty'] - consumed
#                                     product = self.env['product.product'].browse(nvl['product_id'])
#                                     if qty > product_qty:
#                                          
#                                         vals = {'name': product.name or '', 
#                                                 'product_id': product.id or False, 
#                                                 'price_unit': 0.0,
#                                                 'product_uom': product.uom_id.id or False, 
#                                                 'product_uom_qty': product_qty or 0.0,
#                                                 'product_qty':product_qty or 0.0,
#                                                 'location_id': picking.production_id.wh_production_loc_id.id or False, 
#                                                 'production_id': picking.production_id.id or False,
#                                                 'location_dest_id': move.product_id.property_stock_production.id or False, 
#                                                 'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 
#                                                 'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
#                                                 'company_id': picking.production_id.company_id.id, 'state':'done', 'scrapped': False, 
#                                                 'warehouse_id': picking.production_id.warehouse_id.id or False,
#                                                 'picking_finished_id':picking.id
#                                         }
#                                         product_qty = 0
#                                     else:
#                                         vals = {'name': product.name or '', 
#                                                 'product_id': product.id or False, 
#                                                 'price_unit': 0.0,
#                                                 'product_uom': product.uom_id.id or False, 
#                                                 'product_uom_qty': qty or 0.0,
#                                                 'product_qty':qty or 0.0,
#                                                 'location_id': picking.production_id.wh_production_loc_id.id or False, 
#                                                 'production_id': picking.production_id.id or False,
#                                                 'location_dest_id': move.product_id.property_stock_production.id or False, 
#                                                 'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False, 
#                                                 'date': time.strftime('%Y-%m-%d %H:%M:%S') or False,
#                                                 'company_id': picking.production_id.company_id.id, 'state':'done', 'scrapped': False, 
#                                                 'warehouse_id': picking.production_id.warehouse_id.id or False,
#                                                 'picking_finished_id':picking.id
#                                         }
#                                         product_qty = product_qty - qty
#                                     #Tao stock move Tieu 
#                                     new_move_id = self.env['stock.move'].create(vals)
#                                     picking.production_id.write({'move_lines2': [(4, new_move_id.id)]})
#                                     new_move_id.action_done()
#                                 else:
#                                     chuoi = u''' Hết NVL vào sản xuất, Đề nghị xuất thêm''',
#                                     raise UserError(_('%s') % (chuoi))
                                        
                                
                                
                        
                        
                        #Kiet: Nhập kho thành phẩm, Sẽ tạo 1 dòng Stock Move xuất NVL ra ngoài.
                        
class mrp_operation_result(models.Model):
    _inherit = 'mrp.operation.result'
    
    @api.multi
    @api.depends('produced_products')
    def _total_qty(self):
        print "=========vao ham"
        for i in self:
            total_qty = 0
            total_bag = 0
            for line in i.produced_products:
                total_qty += line.product_qty
                total_bag += line.qty_bags
            i.total_qty = total_qty
            i.total_bag = total_bag
            
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty',store=True)
    total_bag = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Bag',store=True)
            