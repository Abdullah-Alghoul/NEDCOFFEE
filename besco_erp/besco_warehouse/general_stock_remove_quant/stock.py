# -*- coding: utf-8 -*-
from openerp.osv import fields, osv, orm
from openerp import SUPERUSER_ID, api, models
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
import time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def action_done(self, cr, uid, ids, context=None):
        """ Process completely the moves given as ids and if all moves are done, it will finish the picking.
        """
        context = context or {}
        picking_obj = self.pool.get("stock.picking")
        quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool.get("product.uom")
        todo = [move.id for move in self.browse(cr, uid, ids, context=context) if move.state == "draft"]
        if todo:
            ids = self.action_confirm(cr, uid, todo, context=context)
        pickings = set()
        procurement_ids = set()
        #Search operations that are linked to the moves
        operations = set()
        move_qty = {}
        for move in self.browse(cr, uid, ids, context=context):
            move_qty[move.id] = move.product_qty
            for link in move.linked_move_operation_ids:
                operations.add(link.operation_id)

        #Sort operations according to entire packages first, then package + lot, package only, lot only
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))

        for ops in operations:
            if ops.picking_id:
                pickings.add(ops.picking_id.id)
            entire_pack=False
            if ops.product_id:
                #If a product is given, the result is always put immediately in the result package (if it is False, they are without package)
                quant_dest_package_id  = ops.result_package_id.id
            else:
                # When a pack is moved entirely, the quants should not be written anything for the destination package
                quant_dest_package_id = False
                entire_pack=True
            lot_qty = {}
            tot_qty = 0.0
            for pack_lot in ops.pack_lot_ids:
                qty = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                lot_qty[pack_lot.lot_id.id] = qty
                tot_qty += pack_lot.qty
            if ops.pack_lot_ids and ops.product_id and float_compare(tot_qty, ops.product_qty, precision_rounding=ops.product_uom_id.rounding) != 0.0:
                raise UserError(_('You have a difference between the quantity on the operation and the quantities specified for the lots. '))
            
            #THANH: Dont use stock quant
#             quants_taken = []
#             false_quants = []
#             lot_move_qty = {}
            #Group links by move first
            move_qty_ops = {}
            for record in ops.linked_move_operation_ids:
                move = record.move_id
                if not move_qty_ops.get(move):
                    move_qty_ops[move] = record.qty
                else:
                    move_qty_ops[move] += record.qty
            
            #THANH: Dont use stock quant
            #Process every move only once for every pack operation
#             for move in move_qty_ops:
#                 main_domain = [('qty', '>', 0)]
#                 self.check_tracking(cr, uid, move, ops, context=context)
#                 preferred_domain = [('reservation_id', '=', move.id)]
#                 fallback_domain = [('reservation_id', '=', False)]
#                 fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
#                 if not ops.pack_lot_ids:
#                     preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
#                     quants = quant_obj.quants_get_preferred_domain(cr, uid, move_qty_ops[move], move, ops=ops, domain=main_domain,
#                                                         preferred_domain_list=preferred_domain_list, context=context)
#                     quant_obj.quants_move(cr, uid, quants, move, ops.location_dest_id, location_from=ops.location_id,
#                                           lot_id=False, owner_id=ops.owner_id.id, src_package_id=ops.package_id.id,
#                                           dest_package_id=quant_dest_package_id, entire_pack=entire_pack, context=context)
#                 else:
                    # Check what you can do with reserved quants already
#                     qty_on_link = move_qty_ops[move]
#                     rounding = ops.product_id.uom_id.rounding
#                     for reserved_quant in move.reserved_quant_ids:
#                         if (reserved_quant.owner_id.id != ops.owner_id.id) or (reserved_quant.location_id.id != ops.location_id.id) or \
#                                 (reserved_quant.package_id.id != ops.package_id.id):
#                             continue
#                         if not reserved_quant.lot_id:
#                             false_quants += [reserved_quant]
#                         elif float_compare(lot_qty.get(reserved_quant.lot_id.id, 0), 0, precision_rounding=rounding) > 0:
#                             if float_compare(lot_qty[reserved_quant.lot_id.id], reserved_quant.qty, precision_rounding=rounding) >= 0:
#                                 lot_qty[reserved_quant.lot_id.id] -= reserved_quant.qty
#                                 quants_taken += [(reserved_quant, reserved_quant.qty)]
#                                 qty_on_link -= reserved_quant.qty
#                             else:
#                                 quants_taken += [(reserved_quant, lot_qty[reserved_quant.lot_id.id])]
#                                 lot_qty[reserved_quant.lot_id.id] = 0
#                                 qty_on_link -= lot_qty[reserved_quant.lot_id.id]
#                     lot_move_qty[move.id] = qty_on_link
                
                if not move_qty.get(move.id):
                    raise UserError(_("The roundings of your Unit of Measures %s on the move vs. %s on the product don't allow to do these operations or you are not transferring the picking at once. ") % (move.product_uom.name, move.product_id.uom_id.name))
                move_qty[move.id] -= move_qty_ops[move]
            
            #THANH: Dont use stock quant
            #Handle lots separately
#             if ops.pack_lot_ids:
#                 self._move_quants_by_lot(cr, uid, ops, lot_qty, quants_taken, false_quants, lot_move_qty, quant_dest_package_id, context=context)
            
            #THANH: Dont use stock quant
            # Handle pack in pack
#             if not ops.product_id and ops.package_id and ops.result_package_id.id != ops.package_id.parent_id.id:
#                 self.pool.get('stock.quant.package').write(cr, SUPERUSER_ID, [ops.package_id.id], {'parent_id': ops.result_package_id.id}, context=context)
        #Check for remaining qtys and unreserve/check move_dest_id in
        move_dest_ids = set()
        for move in self.browse(cr, uid, ids, context=context):
            move_qty_cmp = float_compare(move_qty[move.id], 0, precision_rounding=move.product_id.uom_id.rounding)
            if move_qty_cmp > 0:  # (=In case no pack operations in picking)
                #THANH: Dont use stock quant
#                 main_domain = [('qty', '>', 0)]
#                 preferred_domain = [('reservation_id', '=', move.id)]
#                 fallback_domain = [('reservation_id', '=', False)]
#                 fallback_domain2 = ['&', ('reservation_id', '!=', move.id), ('reservation_id', '!=', False)]
#                 preferred_domain_list = [preferred_domain] + [fallback_domain] + [fallback_domain2]
                self.check_tracking(cr, uid, move, False, context=context)
                qty = move_qty[move.id]
                #THANH: Dont use stock quant
#                 quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain, preferred_domain_list=preferred_domain_list, context=context)
#                 quant_obj.quants_move(cr, uid, quants, move, move.location_dest_id, lot_id=move.restrict_lot_id.id, owner_id=move.restrict_partner_id.id, context=context)

            # If the move has a destination, add it to the list to reserve
            if move.move_dest_id and move.move_dest_id.state in ('waiting', 'confirmed'):
                move_dest_ids.add(move.move_dest_id.id)

            if move.procurement_id:
                procurement_ids.add(move.procurement_id.id)
            
            #THANH: Dont use stock quant
            #unreserve the quants and make them available for other operations/moves
#             quant_obj.quants_unreserve(cr, uid, move, context=context)
        # Check the packages have been placed in the correct locations
        self._check_package_from_moves(cr, uid, ids, context=context)
        #set the move as done
        self.write(cr, uid, ids, {'state': 'done', 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
        self.pool.get('procurement.order').check(cr, uid, list(procurement_ids), context=context)
        #assign destination moves
        if move_dest_ids:
            self.action_assign(cr, uid, list(move_dest_ids), context=context)
        #check picking state to set the date_done is needed
        done_picking = []
        for picking in picking_obj.browse(cr, uid, list(pickings), context=context):
            if picking.state == 'done' and not picking.date_done:
                done_picking.append(picking.id)
        if done_picking:
            picking_obj.write(cr, uid, done_picking, {'date_done': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
            
        #THANH: Update the same stock_move with date done of stock_picking
        for move in self.browse(cr, uid, ids):
            if move.picking_id and move.picking_id.date_done:
                sql = '''
                UPDATE stock_move stm
                SET date = '%s', costed = false
                WHERE stm.id = %s
                '''%(move.picking_id.date_done, move.id)
                cr.execute(sql)
                
            if move.inventory_id and move.inventory_id.date:
                sql = '''
                    UPDATE stock_move stm
                    SET date = '%s'
                    WHERE stm.id = %s
                '''%(move.inventory_id.date, move.id)
                cr.execute(sql)
        return True
    
    #THANH: Dont use stock quant
    @api.cr_uid_ids_context
    def do_unreserve(self, cr, uid, move_ids, context=None):
#         quant_obj = self.pool.get("stock.quant")
        for move in self.browse(cr, uid, move_ids, context=context):
            if move.state in ('done', 'cancel'):
                raise UserError(_('Cannot unreserve a done move'))
#             quant_obj.quants_unreserve(cr, uid, move, context=context)
            if self.find_move_ancestors(cr, uid, move, context=context):
                self.write(cr, uid, [move.id], {'state': 'waiting'}, context=context)
            else:
                self.write(cr, uid, [move.id], {'state': 'confirmed'}, context=context)
            
#    THANH: Dont use stock quant
    def action_assign(self, cr, uid, ids, no_prepare=False, context=None):
        """ Checks the product type and accordingly writes the state.
        """
        context = context or {}
        #quant_obj = self.pool.get("stock.quant")
        uom_obj = self.pool['product.uom']
        to_assign_moves = set()
        main_domain = {}
        todo_moves = []
        operations = set()
        #THANH: Dont use stock quant
#         self.do_unreserve(cr, uid, [x.id for x in self.browse(cr, uid, ids, context=context) if x.reserved_quant_ids and x.state in ['confirmed', 'waiting', 'assigned']], context=context)
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('confirmed', 'waiting', 'assigned'):
                continue
            if move.location_id.usage in ('supplier','inventory', 'production'):
                to_assign_moves.add(move.id)
                #in case the move is returned, we want to try to find quants before forcing the assignment
                if not move.origin_returned_move_id:
                    continue
            if move.product_id.type == 'consu':
                to_assign_moves.add(move.id)
                continue
            else:
                todo_moves.append(move)
                #we always search for yet unassigned quants
                main_domain[move.id] = [('reservation_id', '=', False), ('qty', '>', 0)]
 
                #if the move is preceeded, restrict the choice of quants in the ones moved previously in original move
                ancestors = self.find_move_ancestors(cr, uid, move, context=context)
                if move.state == 'waiting' and not ancestors:
                    #if the waiting move hasn't yet any ancestor (PO/MO not confirmed yet), don't find any quant available in stock
                    main_domain[move.id] += [('id', '=', False)]
                elif ancestors:
                    main_domain[move.id] += [('history_ids', 'in', ancestors)]
 
                #if the move is returned from another, restrict the choice of quants to the ones that follow the returned move
                if move.origin_returned_move_id:
                    main_domain[move.id] += [('history_ids', 'in', move.origin_returned_move_id.id)]
                for link in move.linked_move_operation_ids:
                    operations.add(link.operation_id)
        # Check all ops and sort them: we want to process first the packages, then operations with lot then the rest
        operations = list(operations)
        operations.sort(key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        for ops in operations:
            #first try to find quants based on specific domains given by linked operations for the case where we want to rereserve according to existing pack operations
            if not (ops.product_id and ops.pack_lot_ids):
                for record in ops.linked_move_operation_ids:
                    move = record.move_id
                    if move.id in main_domain:
                        qty = record.qty
                        #domain = main_domain[move.id]
                        #THANH: Dont use stock quant
#                         if qty:
#                             quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, domain=domain, preferred_domain_list=[], context=context)
#                             quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
            else:
                lot_qty = {}
                rounding = ops.product_id.uom_id.rounding
                for pack_lot in ops.pack_lot_ids:
                    lot_qty[pack_lot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, pack_lot.qty, ops.product_id.uom_id.id)
                for record in ops.linked_move_operation_ids:
                    move_qty = record.qty
                    move = record.move_id
                    #domain = main_domain[move.id]
                    for lot in lot_qty:
                        if float_compare(lot_qty[lot], 0, precision_rounding=rounding) > 0 and float_compare(move_qty, 0, precision_rounding=rounding) > 0:
                            qty = min(lot_qty[lot], move_qty)
                            #THANH: Dont use stock quant
#                             quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, ops=ops, lot_id=lot, domain=domain, preferred_domain_list=[], context=context)
#                             quant_obj.quants_reserve(cr, uid, quants, move, record, context=context)
                            lot_qty[lot] -= qty
                            move_qty -= qty
 
        for move in todo_moves:
            #then if the move isn't totally assigned, try to find quants without any specific domain
            if move.state != 'assigned':
            #THANH: Dont use stock quant
#                 qty_already_assigned = move.reserved_availability
#                 qty = move.product_qty - qty_already_assigned
#                 quants = quant_obj.quants_get_preferred_domain(cr, uid, qty, move, domain=main_domain[move.id], preferred_domain_list=[], context=context)
#                 quant_obj.quants_reserve(cr, uid, quants, move, context=context)
            #kiet: Xuất kho Validate luôn nếu có tồn kho
#                 if move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal':
#                     onhand = self.pool.get('product.product').get_Product_Onhand(cr,uid,move.product_id.id,move.location_id.id)
#                     if onhand >= move.product_qty:
#                         self.write(cr, uid, [move.id], {'state': 'assigned'}, context=context)
                if move.location_id.usage == 'transit' and move.location_dest_id.usage == 'internal':
                    self.write(cr, uid, [move.id], {'state': 'assigned'}, context=context)
                    
        #force assignation of consumable products and incoming from supplier/inventory/production
        # Do not take force_assign as it would create pack operations
        if to_assign_moves:
            self.write(cr, uid, list(to_assign_moves), {'state': 'assigned'}, context=context)
        if not no_prepare:
            self.check_recompute_pack_op(cr, uid, ids, context=context)
            
stock_move()  

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed', 'waiting'):
                    continue
                forced_qty = (move.state == 'assigned') and move.product_qty or 0
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    key = (move.product_id)
                    if forced_qties.get(key):
                        forced_qties[key] += forced_qty
                    else:
                        forced_qties[key] = forced_qty
            for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
                vals['fresh_record'] = False
                pack_operation_obj.create(cr, uid, vals, context=context)
        #recompute the remaining quantities all at once
#         self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)
    
#     def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
#         """ returns a list of dict, ready to be used in create() of stock.pack.operation.
# 
#         :param picking: browse record (stock.picking)
#         :param quants: browse record list (stock.quant). List of quants associated to the picking
#         :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
#         """
#         #THANH: Dont use stock quant
# #         def _picking_putaway_apply(product):
# #             location = False
# #             # Search putaway strategy
# #             if product_putaway_strats.get(product.id):
# #                 location = product_putaway_strats[product.id]
# #             else:
# #                 location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
# #                 product_putaway_strats[product.id] = location
# #             return location or picking.location_dest_id.id
#         #THANH: Dont use stock quant
#         # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
# #         product_uom = {} # Determines UoM used in pack operations
# #         location_dest_id = None
# #         location_id = None
# #         for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
# #             if not product_uom.get(move.product_id.id):
# #                 product_uom[move.product_id.id] = move.product_id.uom_id
# #             if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
# #                 product_uom[move.product_id.id] = move.product_uom
# #             if not move.scrapped:
# #                 if location_dest_id and move.location_dest_id.id != location_dest_id:
# #                     raise UserError(_('The destination location must be the same for all the moves of the picking.'))
# #                 location_dest_id = move.location_dest_id.id
# #                 if location_id and move.location_id.id != location_id:
# #                     raise UserError(_('The source location must be the same for all the moves of the picking.'))
# #                 location_id = move.location_id.id
#                 
#         #THANH: Dont use stock quant
# #         pack_obj = self.pool.get("stock.quant.package")
# #         quant_obj = self.pool.get("stock.quant")
#         vals = []
# #         qtys_grouped = {}
# #         lots_grouped = {}
#         #for each quant of the picking, find the suggested location
#         #THANH: Dont use stock quant
# #         quants_suggested_locations = {}
# #         product_putaway_strats = {}
# #         for quant in quants:
# #             if quant.qty <= 0:
# #                 continue
# #             suggested_location_id = _picking_putaway_apply(quant.product_id)
# #             quants_suggested_locations[quant] = suggested_location_id
# 
#         #find the packages we can movei as a whole
#         #THANH: Dont use stock quant
# #         top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
#         # and then create pack operations for the top-level packages found
#         #THANH: Dont use stock quant
# #         for pack in top_lvl_packages:
# #             pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
# #             pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
# #             vals.append({
# #                     'picking_id': picking.id,
# #                     'package_id': pack.id,
# #                     'product_qty': 1.0,
# #                     'location_id': pack.location_id.id,
# #                     'location_dest_id': quants_suggested_locations[pack_quants[0]],
# #                     'owner_id': pack.owner_id.id,
# #                 })
# #             #remove the quants inside the package so that they are excluded from the rest of the computation
# #             for quant in pack_quants:
# #                 del quants_suggested_locations[quant]
#         # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
#         # Lots will go into pack operation lot object
#         #THANH: Dont use stock quant
# #         for quant, dest_location_id in quants_suggested_locations.items():
# #             key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
# #             if qtys_grouped.get(key):
# #                 qtys_grouped[key] += quant.qty
# #             else:
# #                 qtys_grouped[key] = quant.qty
# #             if quant.product_id.tracking != 'none' and quant.lot_id:
# #                 lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
# #                 lots_grouped[key][quant.lot_id.id] += quant.qty
# 
#         # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
#         #THANH: Dont use stock quant
# #         for product, qty in forced_qties.items():
# #             if qty <= 0:
# #                 continue
# #             suggested_location_id = _picking_putaway_apply(product)
# #             key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
# #             if qtys_grouped.get(key):
# #                 qtys_grouped[key] += qty
# #             else:
# #                 qtys_grouped[key] = qty
# 
#         # Create the necessary operations for the grouped quants and remaining qtys
#         #THANH: qtys_grouped is empty because we Dont use stock quant
# #         uom_obj = self.pool.get('product.uom')
# #         prevals = {}
# #         for key, qty in qtys_grouped.items():
#         for move in picking.move_lines:
#             if move.state not in ('assigned', 'confirmed', 'waiting'):
#                 continue
# #             product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
# #             uom_id = product.uom_id.id
# #             qty_uom = qty
# #             if product_uom.get(key[0]):
# #                 uom_id = product_uom[key[0]].id
# #                 qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id)
#             pack_lot_ids = []
# #             if lots_grouped.get(key):
# #                 for lot in lots_grouped[key].keys():
# #                     pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
#             val_dict = {
#                 'product_ean': move.product_ean,
#                 'picking_id': picking.id,
#                 'product_qty': move.product_uom_qty,#qty_uom,
#                 'product_id': move.product_id.id,#key[0],
#                 'package_id': False,#key[1],
#                 'owner_id': False,#key[2],
#                 'location_id': move.location_id.id,#key[3],
#                 'location_dest_id': move.location_dest_id.id,#key[4],
#                 'product_uom_id': move.product_uom.id,#uom_id,
#                 'pack_lot_ids': pack_lot_ids,
#             }
# #             if key[0] in prevals:
# #                 prevals[key[0]].append(val_dict)
# #             else:
# #                 prevals[key[0]] = [val_dict]
#             #THANH: Add to vals
#             vals.append(val_dict)
#         # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
#         #THANH: qtys_grouped is empty because we Dont use stock quant
# #         processed_products = set()
# #         for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
# #             if move.product_id.id not in processed_products:
# #                 vals += prevals.get(move.product_id.id, [])
# #                 processed_products.add(move.product_id.id)
#         return vals

stock_picking()    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
