# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from lxml import etree
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    receive_address = fields.Char(string='Receive Address', size=500)
    receive_date = fields.Datetime(string='Receive Date')
    shipping_status = fields.Selection([
            ('none','None'),
            ('shipping', 'Shipping'),
            ('done', 'Done'),
            ('fail', 'Fail'),
            ('cancel', 'Cancelled'),
        ], string='Shipping Status', readonly=False, default='none',
        track_visibility='onchange', copy=False)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
        res = super(StockPicking, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        
        if view_type in ['tree','form']:
            doc = etree.XML(res['arch'])
            #Thanh: Filter partner_id in Picking Form
            picking_type_id = context.get('search_default_picking_type_id', False)
            is_outgoing = context.get('context_is_outgoing', False)
            if picking_type_id or is_outgoing:
                if picking_type_id:
                    picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                    if picking_type.code in ['outgoing']:
                        is_outgoing = True
                if is_outgoing:
                    for node in doc.xpath("//field[@name='receive_address']"):
                        node.set('invisible', "0")
                        node.set('required', "1")
                    for node in doc.xpath("//field[@name='receive_date']"):
                        node.set('invisible', "0")
                        node.set('required', "1")
                    for node in doc.xpath("//field[@name='shipping_status']"):
                        node.set('invisible', "0")
                        node.set('required', "1")
                    
                    xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
                    res['arch'] = xarch
                    res['fields'] = xfields
        return res
    
#     @api.model
#     def create(self, vals):
#         if vals.get('sale_id',False):
#             sale = self.env['sale.order'].browse(vals['sale_id'])
#             vals.update({''})
#         return super(StockPicking, self.with_context(mail_create_nolog=True)).create(vals)
    
class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    receive_address = fields.Char(string='Receive Address', size=500)
    receive_date = fields.Datetime(string='Receive Date')
    
    @api.multi
    def action_confirm(self):
        super(SaleOrder, self).action_confirm()
        for order in self:
            if order.picking_ids:
                order.picking_ids.write({'receive_address': order.receive_address, 
                                         'min_date': order.receive_date})
            
#     def _validate_data(self):
#         for dates in self:
#             if dates.return_date < dates.delivery_date:
#                 return False            
#             else:
#                 return True
#     
#     _constraints = [(_validate_data,'Error: Invalid return date', ['delivery_date','return_date'])]

#     _sql_constraints = [
#         ('check_return_date', 'CHECK (return_date > delivery_date)', 'Error: Invalid return date!'),
#     ]
    
    @api.model
    def create(self, vals):
        if not vals.get('receive_address',False):
            partner = self.env['res.partner'].browse(vals['partner_id'])
            vals.update({'receive_address': partner.street})
        return super(SaleOrder, self.with_context(mail_create_nolog=True)).create(vals)

class StockShippingBatch(models.Model):
    _name = "stock.shipping.batch"
    
    name = fields.Char(string='Reference', required=True, default='/', readonly=False, states={'done': [('readonly', True)]})
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type',
                                      domain="[('code','=','outgoing')]",
                                       required=True, readonly=True,
                                       ondelete='restrict', states={'draft': [('readonly', False)]})
    fleet_vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True, readonly=True,
                                       ondelete='restrict', states={'draft': [('readonly', False)]})
    emp_driver_id = fields.Many2one('hr.employee', string='Driver', required=True, ondelete='restrict',
                                    readonly=True, states={'draft': [('readonly', False)]})
    depart_at = fields.Datetime('Depart at', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                default=time.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    finished_at = fields.Datetime('Finished at', required=False, readonly=False, states={'done': [('readonly', True)]})
    
    state = fields.Selection([
            ('draft','Draft'),
            ('shipping', 'Shipping'),
            ('done', 'Done'),
            ('cancel', 'Cancelled'),
        ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False)
    
    delivery_order_ids = fields.Many2many('stock.picking', 'stockshippingbatch_picking_rel', 'batch_id', 'picking_id',
                                          domain="[('picking_type_id', '=', picking_type_id)]", 
                                          string="Delivery Orders", copy=False, readonly=False, 
                                          states={'done': [('readonly', True)]})
    
    @api.multi
    def action_load_orders(self):
        for this in self:
            self._cr.execute('''
            SELECT id
            FROM stock_picking
            WHERE picking_type_id=%s and date(timezone('UTC',min_date::timestamp)) = '%s'
            and state not in ('done', 'cancel')
            '''%(this.picking_type_id.id, this.depart_at.split(' ')[0]))
            order_ids = [x[0] for x in self._cr.fetchall()]
            this.write({'delivery_order_ids': [(6,0,order_ids)]})
        return True
    
    @api.multi
    def action_shipping(self):
        for this in self:
            for order in this.delivery_order_ids:
                order.write({'shipping_status': 'shipping'})
        return self.write({'state': 'shipping'})
    
    @api.multi
    def action_done(self):
        return self.write({'state': 'done'})
    
    @api.multi
    def action_cancel(self):
        return self.write({'state': 'cancel'})
# class stock_shipping_batch(osv.osv):
#     _name = 'stock.shipping.batch'
#     _columns = {
#              'sale_order_id':fields.many2one(obj='sale.order', string='Sale Order',
#                                             ondelete='cascade'),
#              'sales_date': fields.date(string='Sales Date'),             
#              'partner_departure_id': fields.many2one(obj='res.partner', string='From'),
#              'partner_destination_id': fields.many2one(obj='res.partner', string='To'),
#              'delivery_date': fields.date(string='Delivery Date',
#                                           help='The date that will start to transport'),       
#              'return_date': fields.date(string='Return Date',
#                                         help='The expected date to finish all the transport'),
#              'fleet_vehicle_id': fields.many2one(obj='fleet.vehicle', string='Vehicle', required=True,
#                                               ondelete='restrict'),             
#              'license_plate': fields.char('License Plate', size=64, required=False, store=True),            
#              'internal_number': fields.integer('Number'),
#              'employee_driver_id':fields.many2one(obj='hr.employee', string='Driver', required=True,
#                                                ondelete='restrict'),
#              'employee_helper_id':fields.many2one(obj='hr.employee', string='helper', required=False,
#                                                ondelete='restrict'),
#              'fleet_trailer_id': fields.many2one(obj='fleet.vehicle', string='Trailer',
#                                                ondelete='restrict', required=True),
#              'trailer_license_plate': fields.char(string='Trailer License Plate', size=64, required=False, store=True),
#              'cargo_ids':fields.one2many(obj='sale.order.cargo', fields_id='sale_order_fleet_id', 
#                                          string='Cargo', required=True,
#                                          help=_('All sale order transported cargo')),                                
#                 }
#     
#     def fleet_trailer_id_change(self, cr, uid, ids,fleet_trailer_id):
#         result={}
#         
#         if not fleet_trailer_id:
#             return {'value':result}
#         
#         trailer = self.pool.get('fleet.vehicle').browse(cr,uid,fleet_trailer_id)
#         
#         if trailer:
#             result['trailer_license_plate'] = trailer.license_plate
#             
#         return {'value':result}
#     
#     def fleet_vehicle_id_change(self, cr, uid, ids,fleet_vehicle_id,context):
#         result={}
#         
#         if not fleet_vehicle_id:
#             return {'value':result}
#                             
#         vehicle = self.pool.get('fleet.vehicle').browse(cr,uid,fleet_vehicle_id)                           
#         sale_order = self.pool.get('sale.order').browse(cr,uid,context.get('sale_order_id')) 
#                            
#         if vehicle:
#             result['license_plate'] =  vehicle.license_plate
#             result['employee_driver_id'] = vehicle.employee_driver_id.id            
#             result['internal_number']=vehicle.internal_number
#         
#         print sale_order
#         
#         if sale_order:
#             #print "sale_date=" + sale_order.date_order
#             result['sales_date'] =  sale_order.date_order
#             #print "sale departure id=" + sale_order.partner_departure_id.id
#             result['partner_departure_id'] =  sale_order.partner_departure_id.id
#             #print "sale shipping id=" + sale_order.partner_shipping_id.id
#             result['partner_destination_id'] =  sale_order.partner_shipping_id.id
#             #print "deli date=" + sale_order.delivery_date 
#             result['delivery_date'] =  sale_order.delivery_date
#             #print "deli date=" + sale_order.return_dae
#             result['return_date'] =  sale_order.return_date    
# 
#         return {'value':result}
#     
#     def copy(self, cr, uid, _id, default=None, context=None):
#         
#         if not default:
#             default = {}
# #         default.update({            
# #             'state': 'draft',            
# #         })
#         return super(sale_order_fleet_vehicle, self).copy(cr, uid, _id, default, context=context)
#         
#         
# #     _sql_constraints = [('vehicle_uniq', 'unique(fleet_vehicle_id,sale_order_id)',
# #                          'Vehicle must be unique per sale order! Remove the duplicate vehicle'),
# #                         ('employee_unique','unique(employee_driver_id,sale_order_id)',
# #                          'A driver must be unique per sale order! Remove the duplicate driver'),]  
#          
# sale_order_fleet_vehicle()
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
