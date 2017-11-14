# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from openerp import SUPERUSER_ID
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    

class SContract(models.Model):
    _inherit = "s.contract"
    
    @api.model
    def _default_crop_id(self):
        crop_ids = self.env['ned.crop'].search([('state', '=', 'current')], limit=1)
        return crop_ids
    
    
    
    crop_id = fields.Many2one('ned.crop', string='Crop', required=True, default=_default_crop_id)
    certificate_id = fields.Many2one(related='contract_line.certificate_id',  string='Certificate')
    packing_id = fields.Many2one(related='contract_line.packing_id',  string='Packing')
    incoterms_id = fields.Many2one('stock.incoterms', string='Term', required=False)
    # Kiet them
    status = fields.Selection([('Allocated', 'Allocated'), ('FOB', 'FOB'),('Factory', 'Factory'),('MBN', 'MBN'),('Pending', 'Pending')],
             string='Shipped By',  copy=False, index=True)
    
    shipment_date = fields.Date(string="Shipment Date")
    pss = fields.Boolean(String="PSS")
    differential = fields.Float(String="Differential")
    fob_delivery = fields.Date(string="FOB Delivery")
    buyer_ref = fields.Char(string='Buyer Ref')
    delivery_place_id = fields.Many2one('delivery.place', string='Delivery Place',
        required=False)
    
    Differential = fields.Float(string="Differential")
    date_pss = fields.Date(string="Date Pss")
    check_by_cont =fields.Boolean(string="Check by cont")
    si_id = fields.Many2one(related='shipping_ids.contract_id',  string='SI')
    
class SContractLine(models.Model):
    _inherit = "s.contract.line"
    
    packing_id = fields.Many2one('ned.packing', string='Packing')
    certificate_id = fields.Many2one('ned.certificate', string='Certificate')
    
    
class ShippingInstructionLine(models.Model):
    _inherit = "shipping.instruction.line"
    
    packing_id = fields.Many2one('ned.packing', string='Packing')
    certificate_id = fields.Many2one('ned.certificate', string='Certificate')
    
    @api.model
    def create(self, vals):
        result = super(ShippingInstructionLine, self).create(vals)
        return result

class AccountInvoice(models.Model):
    _inherit = "account.invoice"
    
    @api.multi
    def printf_commercial_invoice(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'printout_invoice_report',
                }
    @api.multi
    def printf_packing_list(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'printout_packing_list',
    }

    
class ShippingInstruction(models.Model):
    _inherit = "shipping.instruction"
    
    #v kiet them
    
    
#     @api.multi
#     def write(self, vals):
#         result = super(ShippingInstruction, self).write(vals)
#         if vals.get('status',False) and vals.get('status',False) == 'FOB':
#             sql ='''
#                 select id from sale_contract where scontract_id = %s
#             '''%(self.id)
#             self.env.cr.execute(sql)
#             for line in self.env.cr.dictfetchall():
#                 nvs = self.env['sale.contract'].browse(line['id'])
#                 if nvs and nvs.delivery_ids:
#                     raise 
#                 elif nvs.state =='invoice':
#                     raise
#                 else:
#                     nvs.unlink()
#                     
#         return result
    
    @api.depends('contract_ids.total_qty','contract_ids')
    def _allocated_qty(self):
        for order in self:
            allocated_qty = 0
            for nvs in order.contract_ids:
                allocated_qty += nvs.total_qty
            order.allocated = allocated_qty
            
    allocated = fields.Float(compute='_allocated_qty', digits=(12, 0) , string='Allocated',store= False)
    prodcompleted = fields.Date(string="Prod. completion est.",change_default=True,track_visibility='always')
    production_status = fields.Selection([('Pending', 'Pending'), ('Processing', 'Processing'),('Completed', 'Completed')],
             string='Processing status',  copy=False, index=True, change_default=True,track_visibility='always')
    
    status = fields.Selection([('Allocated', 'Allocated'), ('FOB', 'FOB'),('Factory', 'Factory'),('MBN', 'MBN'),('Pending', 'Pending')],
             string='Ship by',  copy=False, index=True,related='contract_id.status',store=True)
    
    date_sent = fields.Date(string="Date Sent")
    certificate_id = fields.Many2one(related='shipping_ids.certificate_id',  string='Certificate')
    packing_id = fields.Many2one(related='shipping_ids.packing_id',  string='Packing')
    pss_sent = fields.Boolean(String="PSS Sent")
    pss_approved = fields.Boolean(String="PSS Approved" ,change_default =True)
    shipment_date = fields.Date(string="Shipment Date", change_default=True)
    materialstatus = fields.Char(string="Material Status",size=256,change_default=True,track_visibility='always')
    
    fumigation_id = fields.Many2one('ned.fumigation', string='Fumigation')
    fumigation_date = fields.Date(string="Fumigation Date")
    shipped = fields.Boolean(String="Shipped" ,change_default =True)
    closing_time = fields.Datetime(string="Closing time")
    container_status = fields.Selection([('fcl/fcl', 'FCL/FCL'), ('lcl/fcl', 'LCL/FCL'), ('lcl/lcl', 'LCL/LCL')], string='Container Status',  index=True) 
    shipping_line_id = fields.Many2one('shipping.line', string='Shipping Line', copy=True, readonly=False)
    delivery_place_id = fields.Many2one('delivery.place', string='Delivery Place',
       domain="[('type', 'not in', ['purchase'])]")
    
    pss_condition = fields.Selection([('pss', 'Pss'), ('none-pss', 'None PSS')], string='Pss Condition')
    bill_no = fields.Char(string="B/L no.")
    bill_date = fields.Date(string="B/L date")
    
    vessel = fields.Char(string="Vessel")
    voyage = fields.Char(string="Voyage:")
    remarks = fields.Char(string="Important remarks")
    priority_by_month = fields.Char(string="Priority",change_default =True,track_visibility='always')
    pss_send_schedule = fields.Date(string="PSS sending schedule")
#     @api.multi
#     @api.onchange('contract_id')
#     def onchange_contract_id(self):
#         if not self.contract_id:
#             values = { 'final_destination': False, 'port_of_loading': False, 'port_of_discharge': False, 'partner_id': False, 'shipping_ids': False}
#             self.update(values)
#         for contract in self.contract_id.contract_line:
#             vars.append((0, 0, {'name': contract.name or False, 'shipping_id': self.id or False,
#                        'tax_id': [(6, 0, [x.id for x in contract.tax_id])] or False,
#                        'price_unit': contract.price_unit or 0.0,
#                        'product_id': contract.product_id.id or False, 'product_qty': contract.product_qty or 0.0,
#                        'partner_id': self.partner_id.id or False, 'company_id': self.company_id.id or False,
#                        'product_uom': contract.product_uom.id or False, 'state': 'draft', 'certificate_id': contract.certificate_id.id or False}))
#         values = { 'final_destination': self.contract_id.partner_shipping_id.id or False, 'port_of_loading': self.contract_id.port_of_loading.id or False,
#             'port_of_discharge': self.contract_id.port_of_discharge.id or False, 'partner_id': self.contract_id.partner_id.id or False, 'shipping_ids': vars}
#         self.update(values)
    
    # The function below loads information of sales contract against corresponding SI.
    @api.multi
    def button_load_sc(self):
        if self.contract_id:
            name = 'SI-' + self.contract_id.name
            val ={
                  'name':name,
                  'port_of_loading':self.contract_id.port_of_loading and self.contract_id.port_of_loading.id or False,
                  'port_of_discharge':self.contract_id.port_of_discharge and self.contract_id.port_of_discharge.id or False,
                  'shipment_date':self.contract_id.shipment_date or False,
                  'incoterms_id':self.contract_id.incoterms_id.id  or False
                  }
            self.write(val)
            
            self.partner_id = self.contract_id.partner_id.id
            self.env.cr.execute('''DELETE FROM shipping_instruction_line WHERE shipping_id = %s''' % (self.id))
            for contract in self.contract_id.contract_line:
                var = {
                       'certificate_id':contract.certificate_id.id,
                       'packing_id': contract.packing_id.id,
                       'name': contract.name or False, 'shipping_id': self.id or False, 'partner_id': self.partner_id.id or False,
                       'tax_id': [(6, 0, [x.id for x in contract.tax_id])] or False, 'company_id': self.company_id.id or False,
                       'price_unit': contract.price_unit or 0.0, 'product_id': contract.product_id.id or False, 
                       'product_qty': contract.product_qty or 0.0,
                       'product_uom': contract.product_uom.id or False, 'state': 'draft', 
                       'certificate_id': contract.certificate_id.id or False}
                self.env['shipping.instruction.line'].create(var)
        return True

class DeliveryOrder(models.Model):
    _inherit = "delivery.order"
 
    @api.multi
    def button_approve(self):
        self.write({'state': 'approved', 'user_approve': self.env.uid,
                    'date_out':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   # 'received_date':received_date,
                     'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
#         if self.type == 'Transfer':
#             move = self.env['stock.move']
#             if self.warehouse_id.int_type_id:
#                 picking_type = self.warehouse_id.int_type_id
#                 names = self.name
#                 val={
#                         'name':'/',
#                         'picking_type_id':picking_type.id,
#                         'location_id':picking_type.default_location_src_id.id,
#                         'location_dest_id':picking_type.default_location_dest_id.id,
#                         'origin':names,
#                         'transfer':False,
#                         'state':'draft'
#                     }
#                 picking_id = self.env['stock.picking'].create(val)
#                 
#                 for line in self.delivery_order_ids:
#                     move_vals ={
#                                 'name':line.product_id.default_code,
#                                 'picking_id': picking_id.id, 
#                                 'product_id': line.product_id.id or False,
#                                 'product_uom': line.product_id.uom_id.id or False, 
#                                 'init_qty':line.product_qty or 0.0,
#                                 'product_uom_qty': line.product_qty or 0.0,
#                                 'price_unit': 0.0,
#                                 'picking_type_id': picking_type.id,
#                                 'location_id': picking_type.default_location_src_id.id or False,
#                                 'location_dest_id': picking_type.default_location_dest_id.id or False, 
#                                 'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False,
#                                 'type': picking_type.code or False,
# #                                 'packing_id':produced.packing_id.id,
#                                 'company_id': 1, 
#                                 'state':'draft', 'scrapped': False, 
#                                 'warehouse_id': self.warehouse_id.id or False
#                                 }
#                 
#                     move.create(move_vals)
#                 self.picking_id = picking_id.id
                                
    @api.model
    def _default_currency_id(self):
        self.env['res.users'].browse(self.env.uid).company_id.second_currency_id.id
        return self.env['res.users'].browse(self.env.uid).company_id.second_currency_id.id
    
    @api.multi
    def button_load_do(self):
        sql ='''
            SELECT '%s'::date +1 as date
        '''%(self.date)
        self.env.cr.execute(sql)
        for date in self.env.cr.dictfetchall():
            received_date = date['date'] or 0.0
        self.write({
                    'received_date':received_date})
        
        if self.contract_id: 
            
            self.env.cr.execute('''DELETE FROM delivery_order_line WHERE delivery_id = %s''' % (self.id))
            val ={
                  'partner_id':self.contract_id.partner_id and self.contract_id.partner_id.id or False,
                  'warehouse_id':self.contract_id.warehouse_id and self.contract_id.warehouse_id.id,
                  'reason': u'Vận chuyển nội bộ',
                  'delivery_place_id':self.contract_id.shipping_id.delivery_place_id and self.contract_id.shipping_id.delivery_place_id.id or False,
                  'markings':self.contract_id.shipping_id.marking or False
                  }
            self.write(val)
            product_qty = new_qty = 0.0
            for contract in self.contract_id.contract_line:
                for do in self.contract_id.delivery_ids:
                    if do.state != 'cancel':
                        for do_line in do.delivery_order_ids:
                            if do_line.product_id == contract.product_id:
                                product_qty += do_line.product_qty
                new_qty = contract.product_qty - product_qty 
                var = {'delivery_id': self.id, 'name': contract.name, 'product_id': contract.product_id.id,
                       'certificate_id':self.contract_id.shipping_id.certificate_id.id,
                       'packing_id': self.contract_id.shipping_id.packing_id.id,
                       
                       'product_qty': new_qty, 'product_uom': contract.product_uom.id, 'state': 'draft'}
                self.env['delivery.order.line'].create(var)
        return True
    
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True, required=True, states={'draft': [('readonly', False)]}, default=_default_currency_id)
    
    certificate_id = fields.Many2one(related='delivery_order_ids.certificate_id',  string='Certificate')
    packing_id = fields.Many2one(related='delivery_order_ids.packing_id',  string='Packing')
    delivery_place_id = fields.Many2one(related='contract_id.shipping_id.delivery_place_id', string='Delivery Place',
        required=False)
    
    shipping_id = fields.Many2one(related='contract_id.shipping_id',  string='SI No.',store=True)
    move_id = fields.Many2one('stock.move',string='Move')
    
    @api.depends('picking_id','picking_id.state','post_shippemnt_ids.post_line','post_shippemnt_ids','post_shippemnt_ids.post_line.bags','post_shippemnt_ids.post_line.shipped_weight')
    def _factory_qty(self):
        for order in self:
            weight = bagsfactory  = 0
            for pick in order.picking_id:
                if pick.state == 'done':
                    for line in pick.move_lines:
                        bagsfactory += line.bag_no or 0.0
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
    
    storing_loss  = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Storing Loss',store =True)
    transportation_loss  = fields.Float(compute='_factory_qty', digits=(12, 0) , string='Transportation Loss',store =True)
    bags = fields.Float(compute='_factory_qty', digits=(12, 0) , string='BagsHCM',store =True)
    shipped_weight = fields.Float(compute='_factory_qty', digits=(12, 0) , string='WeightHCM',store =True)
    
class DeliveryOrderLine(models.Model):
    _inherit = "delivery.order.line"
    
    packing_id = fields.Many2one('ned.packing', string='Packing')
    certificate_id = fields.Many2one('ned.certificate', string='Certificate')

class PostShipMent(models.Model):
    _inherit = "post.shipment"
    
    
    packing_id = fields.Many2one('ned.packing', string='Packing')
    
    @api.multi
    def button_load(self):
        if self.do_id:
            self.env.cr.execute('''DELETE FROM post_shipment_line WHERE post_id = %s''' % (self.id))
            val ={
                  'nvs_nls_id':self.do_id.contract_id and self.do_id.contract_id.id or False,
                  'delivery_place_id':self.do_id.delivery_place_id and self.do_id.delivery_place_id.id or False,
                  'truck_plate':self.do_id.trucking_no or False,
                  'packing_id':self.do_id.packing_id and self.do_id.packing_id.id or False
                  }
            self.write(val)
#             if not self.do_id.move_id:
#                 for line in self.do_id.delivery_order_ids:
#                     if self.do_id.picking_id:
#                         location_id = self.do_id.picking_id.picking_type_id.default_location_dest_id.id
#                         location_dest_id = self.env['stock.location'].search([('usage','=','customer')])
#                         data = {
#                                 'product_uom_qty':line.product_qty,
#                                 'price_unit':0,
#                                 'location_id':location_id,
#                                 'name': self.do_id.name +' - ' + line.product_id.default_code, 
#                                 'date': time.strftime(DATETIME_FORMAT),
#                                 'product_id': line.product_id.id,
#                                 'product_uom': line.product_id.uom_id.id, 
#                                 'location_dest_id': location_dest_id.id, 
#                                 'company_id': 1,
#                                 'origin': self.do_id.name, 
#                                 'state': 'done'}
#                         new_id = self.env['stock.move'].create(data)
#                         self.do_id.move_id = new_id.id
#                     else:
#                         raise UserError(_('Chưa xuất GDN ra khỏi nhà máy'))
            
            
        return True

class PostShipMentLine(models.Model):
    _inherit = "post.shipment.line"
    
    bl_date = fields.Date(string='B/L date',related='post_id.nvs_nls_id.shipping_id.bill_date',readonly=True)
    bl_no = fields.Char(string ='B/L no.',size =128,related='post_id.nvs_nls_id.shipping_id.bill_no',readonly=True)
    
        
