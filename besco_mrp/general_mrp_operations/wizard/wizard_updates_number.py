# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError, RedirectWarning
from lxml import etree

class updates_number(osv.osv_memory):
    _name = "updates.number"
    _columns = {
        'operation_id': fields.many2one('mrp.production.workcenter.line', 'Operation'),
        'updates_number_lines': fields.one2many('updates.number.line', 'updates_number_id', 'Updates Number Line' , ondelete='cascade'),
        }

    def default_get(self, cr, uid, fields, context=None):
        updates_number_lines = []
        if context is None:
            context = {}
       
        res = super(updates_number, self).default_get(cr, uid, fields, context=context)
        workcenter = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, context['active_id'], context=context)
        for consumed in workcenter.consumed_product:
            updates_number_lines.append((0, 0, {'product_id': consumed.product_id.id or False, 'received_qty': consumed.received_qty or 0,
             'actual_qty': consumed.actual_qty or 0, 'consumed_id': consumed.id or False, 'product_uom': consumed.product_uom.id}))

        if 'operation_id' in fields:
            res.update({'operation_id': workcenter.id})
        if 'updates_number_lines' in fields:
            res.update({'updates_number_lines': updates_number_lines})
        return res
    
    def create_move(self, cr, uid, operation_id, context=None):
        location_id = False
        location_dest_id = False
        move = self.pool.get('stock.move')
        location_pool = self.pool.get('stock.location')
        
        if context is None:
            context = {}
            
        actual_qty = context['actual_qty'] or 0.0
        product_id = context['product_id'] or False
        product_uom = context['product_uom'] or False
        
        operation = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, operation_id)
        production_obj = self.pool.get('mrp.production').browse(cr, uid, operation.production_id.id)
        
        if not production_obj.warehouse_id:
            raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Thiếu thông tin Vị Trí Kho trong lệnh sản xuất!', 'utf8'))
        
        warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)

        if not warehouse_obj.wh_production_loc_id.id:
            error = "Thiếu thông tin Địa Điểm Sản Xuất tại kho (%s)." % (str(warehouse_obj.name))
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_id = warehouse_obj.wh_production_loc_id.id
        
        if not operation.product_id.property_stock_production.id:
            error = "Thiếu thông tin Địa Điểm Sản Xuất không tồn tại."
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_dest_id = operation.product_id.property_stock_production.id
        
        if product_id and actual_qty and product_uom:
            cr.execute('''DELETE FROM mrp_production_consumed_products_move_ids WHERE production_id = %(production_id)s
                        And move_id in (select stm.id FROM stock_move stm 
                        WHERE stm.production_id = %(production_id)s And stm.product_id = %(product_id)s);
                    DELETE FROM stock_move WHERE production_id = %(production_id)s And product_id = %(product_id)s;
            ''' % ({'production_id': operation.production_id.id, 'product_id': product_id}))
            
            var = {'name': str(operation.product_id.name), 'picking_id': False, 'operation_id': operation.id,
              'picking_type_id': warehouse_obj.production_out_type_id.id, 'production_id': operation.production_id.id,
              'product_id': product_id, 'date': time.strftime('%Y-%m-%d %H:%M:%S'),
              'product_uom_qty': actual_qty, 'product_uom': product_uom, 'state': 'done',
              'location_id': location_id, 'location_dest_id': location_dest_id}
            move_id = move.create(cr, uid, var)
            cr.execute('''INSERT INTO mrp_production_consumed_products_move_ids VALUES (%s, %s);''' % (operation.production_id.id, move_id))
        return True
    
    def button_update(self, cr, uid, ids, context=None):
        consumed_pool = self.pool.get('mrp.production.workcenter.product.consumed')
        for update in self.browse(cr, uid, ids):
            for line in update.updates_number_lines:
                consumed_obj = consumed_pool.browse(cr, uid, line.consumed_id.id)
                actual_qty_update = line.actual_qty + line.update_qty or 0.0
                received_qty_update = consumed_obj.received_qty - actual_qty_update or 0.0
                consumed_pool.write(cr, uid, [line.consumed_id.id], {'actual_qty': actual_qty_update, 'product_rest_actual': received_qty_update})
                context.update({'actual_qty': actual_qty_update, 'product_id': line.product_id.id, 'product_uom': line.product_uom.id})
#                 self.create_move(cr, uid, [update.operation_id.id], context=context)
        return True
updates_number()

class updates_number_line(osv.osv_memory):
    _name = "updates.number.line"
    _columns = {
        'product_id': fields.many2one('product.product', 'Material', readonly=True),
        'received_qty': fields.float('Quantity Received'),
        'actual_qty': fields.float('Quantity actual'),
        'update_qty': fields.float('Quantity Updates'),
        'product_uom': fields.many2one('product.uom', 'UoM'),
        'consumed_id': fields.many2one('mrp.production.workcenter.product.consumed', 'Product Consumed'),
        'updates_number_id': fields.many2one('updates.number', 'Updates Number'),
        }
    _defaults = {
                 'received_qty': 0.0,
                 'actual_qty': 0.0,
                 'update_qty': 0.0
                 } 
updates_number_line()
