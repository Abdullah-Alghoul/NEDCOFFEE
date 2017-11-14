# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from openerp.osv import fields, osv

class StockPicking(osv.osv):
    _inherit = 'stock.picking'
    _columns={
        'is_landed_cost':fields.boolean('Is Landed Cost')
      }
    _defaults = {
       'is_landed_cost':False,
    }
#     @api.multi
#     def action_open_landed_cost(self):
#         self.ensure_one()
#         line_obj = self.env['purchase.cost.distribution.line']
#         lines = line_obj.search([('picking_id', '=', self.id)])
#         if lines:
#             mod_obj = self.env['ir.model.data']
#             model, action_id = tuple(
#                 mod_obj.get_object_reference(
#                     'purchase_landed_cost',
#                     'action_purchase_cost_distribution'))
#             action = self.env[model].browse(action_id).read()[0]
#             ids = set([x.distribution.id for x in lines])
#             if len(ids) == 1:
#                 res = mod_obj.get_object_reference(
#                     'purchase_landed_cost', 'purchase_cost_distribution_form')
#                 action['views'] = [(res and res[1] or False, 'form')]
#                 action['res_id'] = list(ids)[0]
#             else:
#                 action['domain'] = "[('id', 'in', %s)]" % list(ids)
#             return action
    def action_open_landed_cost(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('purchase.cost.distribution.line')
        lines = line_obj.search(cr, uid, [('picking_id', '=', ids[0])])
        if lines:
            mod_obj = self.pool.get('ir.model.data')
            model, action_id = tuple(mod_obj.get_object_reference(
                    'general_landed_cost', 'action_purchase_cost_distribution'))
            
            action = self.pool.get(model).browse(action_id).read()[0]
            ids = set([x.distribution.id for x in lines])
            if len(ids) == 1:
                res = mod_obj.get_object_reference(
                    'general_landed_cost', 'purchase_cost_distribution_form')
                action['views'] = [(res and res[1] or False, 'form')]
                action['res_id'] = list(ids)[0]
            else:
                action['domain'] = "[('id', 'in', %s)]" % list(ids)
            return action
        return True