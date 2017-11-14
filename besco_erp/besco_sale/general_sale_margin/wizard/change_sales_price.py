# -*- coding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
import time

class change_sales_price(osv.osv_memory):
    _name = "change.sales.price"
    _columns = {
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Product Price')),
    }
    
    _defaults = {
        'price_unit': 0.0,
    }
    
    def _check_price_unit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for data in self.browse(cr, uid, ids, context=context):
            if data.price_unit < 0:
                return False
        return True
    
    _constraints = [
        (_check_price_unit, 'Unit Price must be greater than 0', []),

    ]
    
    def change_price_unit(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        rec_id = context and context.get('active_id', False)
        active_model = context and context.get('active_model', False)
        assert rec_id, _('Active ID is not set in Context')
        assert active_model, _('Active Model is not set in Context')

        sale_order_line_pool = self.pool.get('sale.order.line')
        product_pool = self.pool.get('product.product')
        
        if active_model == 'sale.order.line':
            sale_order_line_obj = sale_order_line_pool.browse(cr, uid, rec_id, context=context)
            for data in self.browse(cr, uid, ids, context=context):
                standard_price = sale_order_line_obj.purchase_price
                if not standard_price and sale_order_line_obj.product_id:
                    standard_price = product_pool.browse(cr, uid, sale_order_line_obj.product_id.id).standard_price
                mark_up = standard_price and round((data.price_unit - standard_price) * 100 / standard_price, 2) or 0.0
                vals = {
                        'mark_up': mark_up,
                        'price_unit': data.price_unit,
                        }
                sale_order_line_pool.write(cr, uid, [rec_id], vals)
                
        return {'type': 'ir.actions.act_window_close'}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
