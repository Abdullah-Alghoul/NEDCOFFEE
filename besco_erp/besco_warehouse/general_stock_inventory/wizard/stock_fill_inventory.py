# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp.tools import mute_logger
import time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class stock_fill_inventory(osv.osv_memory):
    _inherit = "stock.fill.inventory"
    
    _defaults = {
         'recursive': True
    }
    
    def fill_inventory(self, cr, uid, ids, context=None):
        """ To Import stock inventory according to products available in the selected locations.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        @return:
        """
#         if context is None:
#             context = {}
#  
#         inventory_line_obj = self.pool.get('stock.inventory.line')
#         location_obj = self.pool.get('stock.location')
#         move_obj = self.pool.get('stock.move')
#         uom_obj = self.pool.get('product.uom')
#         if ids and len(ids):
#             ids = ids[0]
#         else:
#             return {'type': 'ir.actions.act_window_close'}
#         fill_inventory = self.browse(cr, uid, ids, context=context)
#         res = {}
#         res_location = {}
#  
#         if fill_inventory.recursive:
#             location_ids = location_obj.search(cr, uid, [('location_id',
#                              'child_of', [fill_inventory.location_id.id])], order="id",
#                              context=context)
#         else:
#             location_ids = [fill_inventory.location_id.id]
#  
#         res = {}
#         flag = False
#  
#         for location in location_ids:
#             datas = {}
#             res[location] = {}
#             move_ids = move_obj.search(cr, uid, ['|',('location_dest_id','=',location),('location_id','=',location),('state','=','done')], context=context)
#             local_context = dict(context)
#             local_context['raise-exception'] = False
#             for move in move_obj.browse(cr, uid, move_ids, context=context):
#                 lot_id = move.prodlot_id.id
#                 prod_id = move.product_id.id
#                 if move.location_dest_id.id != move.location_id.id:
#                     if move.location_dest_id.id == location:
#                         qty = uom_obj._compute_qty_obj(cr, uid, move.product_uom,move.product_qty, move.product_id.uom_id, context=local_context)
#                     else:
#                         qty = -uom_obj._compute_qty_obj(cr, uid, move.product_uom,move.product_qty, move.product_id.uom_id, context=local_context)
#  
#  
#                     if datas.get((prod_id, lot_id)):
#                         qty += datas[(prod_id, lot_id)]['product_qty']
#  
#                     datas[(prod_id, lot_id)] = {'product_id': prod_id, 'location_id': location, 'product_qty': qty, 'product_uom': move.product_id.uom_id.id, 'prod_lot_id': lot_id}
#  
#             if datas:
#                 flag = True
#                 res[location] = datas
#  
#         if not flag:
#             raise osv.except_osv(_('Warning!'), _('No product in this location. Please select a location in the product form.'))
#  
#         for stock_move in res.values():
#             for stock_move_details in stock_move.values():
#                 stock_move_details.update({'inventory_id': context['active_ids'][0]})
#                 domain = []
#                 for field, value in stock_move_details.items():
#                     if field == 'product_qty' and fill_inventory.set_stock_zero:
#                         domain.append((field, 'in', [value,'0']))
#                         continue
#                     domain.append((field, '=', value))
#  
#                 if fill_inventory.set_stock_zero:
#                     stock_move_details.update({'product_qty': 0})
#  
#                 line_ids = inventory_line_obj.search(cr, uid, domain, context=context)
#  
#                 if not line_ids:
#                     inventory_line_obj.create(cr, uid, stock_move_details, context=context)
        
        #Thanh: Should not use loading stock by orm object (stock.move) => Hide above original code
        #Thanh: Must use sql query to optimize the performance
        context = context or None
        inventory_obj = self.pool.get('stock.inventory')
        location_obj = self.pool.get('stock.location')
        categ_obj = self.pool.get('product.category')
        if ids and len(ids):
            ids = ids[0]

        inventory = inventory_obj.browse(cr, uid, context['active_id'])
        
        #Thanh: Delete Inventory Line and Relate Moves Firstly
        cr.execute('''DELETE FROM stock_inventory_line where inventory_id=%s;
                      DELETE FROM stock_inventory_move_rel where inventory_id=%s;
                      commit;
        '''%(inventory.id,inventory.id))
        
        if inventory.group_type != 'manual':
            #Thanh: Load inventory line from wizard location and its childrens
            fill_inventory = self.browse(cr, uid, ids, context=context)
            if fill_inventory.recursive:
                location_ids = location_obj.search(cr, uid, [('location_id',
                                 'child_of', [fill_inventory.location_id.id])], order="id",
                                 context=context)
            else:
                location_ids = [fill_inventory.location_id.id]
            
            where_group_type = ''
            if inventory.group_type == 'product':
                product_ids = [x.id for x in inventory.product_ids]
                where_group_type = ' and stm.product_id in (%s)'%(','.join(map(str, product_ids)))
            if inventory.group_type == 'cat':
                categ_ids = categ_obj.search(cr, uid, [('id',
                                 'child_of', [x.id for x in inventory.categ_ids])], order="id",
                                 context=context)
                where_group_type = ' and pt.categ_id in (%s)'%(','.join(map(str, categ_ids)))
            
            sql = '''
                INSERT INTO stock_inventory_line(inventory_id, location_id, product_id, prod_lot_id, product_uom, product_qty, freeze_cost, company_id)
                SELECT %(inventory_id)s, location_id, product_id, prodlot_id, uom_id, onhand_qty, 
                    case when onhand_qty > 0
                    then onhand_value/onhand_qty
                    else 0.0
                    end,
                    %(company_id)s
                FROM
                (
                    SELECT location_id, product_id, prodlot_id, uom_id, onhand_qty, onhand_value
                    
                    FROM stock_quant
                    
                    WHERE 
                    
                    GROUP BY foo.location_id, foo.prodlot_id, foo.product_id, foo.uom_id ,foo.location_name
                        
                    HAVING coalesce(sum(onhand_qty),0) != 0
                    
                    ORDER BY foo.location_name
                )
            '''%({'company_id': inventory.company_id.id,
                  'inventory_id': inventory.id,
                  'location_ids': ','.join(map(str, location_ids)),
                  'freeze_date': inventory.freeze_date,
                  'where_group_type': where_group_type})
            cr.execute(sql)
        return {'type': 'ir.actions.act_window_close'}

stock_fill_inventory()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
