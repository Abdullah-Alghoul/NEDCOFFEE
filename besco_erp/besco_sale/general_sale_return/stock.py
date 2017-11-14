# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
        'sale_return_line_id': fields.many2one('sale.return.line','Sale Return Line', ondelete='set null', select=True,readonly=True),
    }
    
    def get_price_unit(self, cr, uid, move, context=None):
        """ Returns the unit price to store on the quant """
        if move.purchase_line_id:
            return move.price_unit
        if move.purchase_return_line_id:
            return move.price_unit
        if move.sale_return_line_id:
            return move.price_unit
        return super(stock_move, self).get_price_unit(cr, uid, move, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        context = context or {}
        if not default.get('split_from'):
            #we don't want to propagate the link to the purchase order line except in case of move split
            default['purchase_line_id'] = False
            default['purchase_return_line_id'] = False
            default['sale_return_line_id'] = False
        return super(stock_move, self).copy(cr, uid, id, default, context)