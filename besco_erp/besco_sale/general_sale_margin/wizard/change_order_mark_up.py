# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError

class change_order_mark_up(models.TransientModel):
    _name = "change.order.markup"
    
    mark_up = fields.Float(string='Mark-up (%)', digits=(16,2), required=True)
    
    @api.multi
    def _check_mark_up(self):
        for data in self:
            if data.mark_up < 0:
                return False
        return True
     
    _constraints = [
        (_check_mark_up, 'Mark-up must be greater than 0', []),
 
    ]
    
    @api.multi
    def change_mark_up(self):
        context = dict(self._context or {})
        
        rec_id = context and context.get('active_id', False)
        active_model = context and context.get('active_model', False)
        assert rec_id, _('Active ID is not set in Context')
        assert active_model, _('Active Model is not set in Context')

        sale_order_pool = self.env['sale.order']
        sale_order_line_pool = self.env['sale.order.line']
        product_pool = self.env['product.product']
        
        if active_model == 'sale.order':
            sale_order_obj = sale_order_pool.browse(rec_id)
            for data in self:
                update_cost = False
                for line in sale_order_obj.order_line:
                    standard_price = line.purchase_price
                    if not standard_price and line.product_id:
                        standard_price = product_pool.browse(line.product_id.id).standard_price
                        update_cost = True
                    price_unit = round(standard_price + (standard_price * data.mark_up/100),3)
                    vals = {
                            'mark_up': data.mark_up,
                            'price_unit': price_unit,
                            }
                    if update_cost:
                        vals.update({'purchase_price':standard_price})
                    line.write(vals)
                    
        if active_model == 'sale.order.line':
            sale_order_line_obj = sale_order_line_pool.browse(rec_id)
            for data in self:
                update_cost = False
                standard_price = sale_order_line_obj.purchase_price
                if not standard_price and sale_order_line_obj.product_id:
                    standard_price = product_pool.browse(sale_order_line_obj.product_id.id).standard_price
                    update_cost = True
                price_unit = round(standard_price + (standard_price * data.mark_up/100),3)
                vals = {
                        'mark_up': data.mark_up,
                        'price_unit': price_unit,
                        }
                if update_cost:
                        vals.update({'purchase_price':standard_price})
                sale_order_line_obj.write(vals)
        
        return {'type': 'ir.actions.act_window_close'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: