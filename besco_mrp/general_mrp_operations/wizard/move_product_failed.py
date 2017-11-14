# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp



class move_product_failed(osv.osv_memory):
    _name = "move.product.failed"

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, select=True),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'operation_id': fields.many2one('mrp.production.workcenter.line', 'Operation', required=True),
    }

    _defaults = {
                 'location_id': lambda *x: False
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(move_product_failed, self).default_get(cr, uid, fields, context=context)
        workcenter = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, context['active_id'], context=context)

        location_obj = self.pool.get('stock.location')
        location_id = location_obj.search(cr, uid, [('usage', '=', 'inventory')])
        
        if 'operation_id' in fields:
            res.update({'operation_id': workcenter.id})
        if 'product_id' in fields:
            res.update({'product_id': workcenter.product_id.id})
        if 'product_uom' in fields:
            res.update({'product_uom': workcenter.product_uom.id})
        if 'product_qty' in fields:
            res.update({'product_qty': workcenter.fail_qty})
        if 'location_id' in fields:
            if location_id:
                res.update({'location_id': location_id[0]})
            else:
                res.update({'location_id': False})
        return res

    def move(self, cr, uid, ids, context=None):
        location_id = False
        location_dest_id = False
        move = self.pool.get('stock.move')
        
        this = self.browse(cr, uid, ids[0])
        workcenter_obj = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, this.operation_id.id)
        production_id = workcenter_obj.production_id.id or False
        production_obj = self.pool.get('mrp.production').browse(cr, uid, production_id)
        
        if not production_obj.warehouse_id:
            raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Thiếu thông tin Vị Trí Kho trong lệnh sản xuất!', 'utf8'))
        
        warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)
        
        if not mrp_result.product_id.property_stock_production.id:
            error = "Thiếu thông tin Địa Điểm Sản Xuất trện sản phẩm (%s)." % (str(mrp_result.product_id.name))
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_id = mrp_result.product_id.property_stock_production.id
        
        if not warehouse_obj.wh_production_loc_id.id:
            error = "Thiếu thông tin Địa Điểm Đích trong Nhật Ký Sản Xuất (%s)." % (str(warehouse_obj.production_out_type_id.name))
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_dest_id = warehouse_obj.wh_production_loc_id.id
        
        var = {'name': unicode(this.product_id.name), 'picking_id': False, 'picking_type_id': warehouse_obj.production_in_type_id.id,
              'production_id': production_id, 'product_finished_goods': production_obj.product_id.id, 'product_id': this.product_id.id,
              'date': time.strftime('%Y-%m-%d %H:%M:%S'), 'product_uom_qty': this.product_qty, 'product_uom': this.product_uom.id,
              'location_id': location_id, 'location_dest_id': location_dest_id, 'state': 'draft', 'origin': this.operation_id.name}
            
        move_id = move.create(cr, uid, var)
        move.action_confirm(cr, uid, [move_id], context=context)[0]
        move.action_done(cr, uid, [move_id])
        
        return True
