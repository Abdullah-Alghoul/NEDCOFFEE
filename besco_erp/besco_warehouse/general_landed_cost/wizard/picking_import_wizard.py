# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# from openerp import models, fields, api
from openerp.osv import fields, osv

class PickingImportWizard(osv.osv_memory):
    _name = "picking.import.wizard"
    _description = "Import incoming shipment"

#     @api.model
#     def default_get(self, field_list):
#         """Get pickings previously imported."""
#         res = super(PickingImportWizard, self).default_get(field_list)
#         if self.env.context.get('active_id') and 'prev_pickings' in field_list:
#             distribution = self.env['purchase.cost.distribution'].browse(
#                 self.env.context['active_id'])
#             res['prev_pickings'] = [(6, 0, [x.picking_id.id for x in
#                                             distribution.cost_lines])]
#         return res

    _columns = {
        'supplier': fields.many2one('res.partner', string='Supplier', required=True,
            domain="[('supplier',  '=', True)]"),
                
        'pickings': fields.many2many('stock.picking',
            'distribution_import_picking_rel', 'wizard_id', 'picking_id', string='Incoming shipments',
            domain="[('partner_id', 'child_of', supplier),"
                   "('location_id.usage', '=', 'supplier'),"
                   "('state', '=', 'done'),"
                   "('is_landed_cost', '!=', True)],", required=True),
                
        'prev_pickings': fields.many2many('stock.picking'),
    }
    
    def default_get(self, cr, uid, fields, context=None):
        """Get pickings previously imported."""
        context = context or {}
        res = super(PickingImportWizard, self).default_get(cr, uid, fields, context=context)

        if context.get('active_id') and 'prev_pickings' in fields:
            distribution = self.pool.get('purchase.cost.distribution').browse(cr, uid, context['active_id'])
            res['prev_pickings'] = [(6, 0, [x.picking_id.id for x in
                                            distribution.cost_lines])]
        return res
    
    def _prepare_distribution_line(self, move, context=None):
        context = context or {}
        return {
            'distribution': context['active_id'],
            'move_id': move.id,
        }

#     @api.multi
#     def action_import_picking(self):
#         self.ensure_one()
#         for picking in self.pickings:
#             for move in picking.move_lines:
#                 self.env['purchase.cost.distribution.line'].create(
#                     self._prepare_distribution_line(move))
    def action_import_picking(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        for picking in this.pickings:
            for move in picking.move_lines:
                self.pool.get('purchase.cost.distribution.line').create(cr, uid, 
                    self._prepare_distribution_line(move, context=context))
