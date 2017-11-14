# -*- coding: utf-8 -*-
from datetime import datetime

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
from openerp.exceptions import UserError

from lxml import etree
import base64
import xlrd

import logging
_logger = logging.getLogger(__name__)

class stock_production_lot(osv.osv):
    _inherit = 'stock.production.lot'
    _order = 'in_date desc,create_date'
    
    def _compute_qty(self, cr, uid, ids, name, args, context=None):
        res = {}
        for lot in self.browse(cr, uid, ids, context=context):
            qty = 0.0
            for quant in lot.quant_ids:
                if quant.location_id.usage == 'internal':
                    qty += quant.qty
            res[lot.id] = qty
        return res
    
    def _get_lots(self, cr, uid, ids, context=None):
        """Returns Lots from quants for store"""
        res = set()
        for quant in self.browse(cr, uid, ids, context=context):
            res.add(quant.lot_id.id)
        return list(res)
    
    def _compute_price(self, cr, uid, ids, name, args, context=None):
        res = {}
        for lot in self.browse(cr, uid, ids, context=context):
            total_qty = 0.0
            total_amount = 0.0
            for quant in lot.quant_ids:
                for move in quant.history_ids:
                    if move.location_id.usage != 'internal' and move.location_dest_id.usage == 'internal':
                        total_amount += (move.product_qty * move.price_unit)
                        total_qty += move.product_qty
            if total_qty:
                res[lot.id] = round(total_amount / total_qty)
            else:
                res[lot.id] = 0.0
        return res
    
    _columns = {
        #THANH: Add missing fields
        'in_date': fields.related('quant_ids', 'in_date', type='datetime', string='Incoming Date', store=True),
        'uom_id': fields.related('quant_ids', 'product_uom_id', type='many2one', relation='product.uom', string='UoM', store=True),
        
        #THANH: new field to get remaining lot qty
        'remaining_qty': fields.function(_compute_qty, type='float', 
             store={
                    'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, ['quant_ids'], 10),
                    'stock.quant': (_get_lots, ['location_id', 'qty'], 10),
             },
             string='Remaining Qty',
        ),
        'price_avg':fields.function(_compute_price, type='float', 
             store={
                    'stock.production.lot': (lambda self, cr, uid, ids, c={}: ids, ['quant_ids'], 10),
                    'stock.quant': (_get_lots, ['location_id', 'qty'], 10),
             },
             string='Price Avg',
        ),
    }
    
stock_production_lot()

class stock_location(osv.osv):
    _inherit = "stock.location"
    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'code':fields.char('Code',size=256),
    }
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        ids = self.search(cr, user, domain + args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def init(self, cr):
        #Thanh: Fix parent left and parent right
        def browse_rec(root, pos=0):
            cr.execute("SELECT id FROM stock_location WHERE location_id=%s"%(root))
            pos2 = pos + 1
            for id in cr.fetchall():
                pos2 = browse_rec(id[0], pos2)
            cr.execute('update stock_location set parent_left=%s, parent_right=%s where id=%s', (pos, pos2, root))
            return pos2 + 1  
        query = "SELECT id FROM stock_location WHERE location_id IS NULL"
        pos = 0
        cr.execute(query)
        for (root,) in cr.fetchall():
            pos = browse_rec(root, pos)
        return True
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        for location in self.browse(cr, uid, ids, context=context):
            res.append((location.id, location.name))
        return res
    
stock_location()

class stock_quant(osv.osv):
    _inherit = "stock.quant"
    
#     def _calc_inventory_value(self, cr, uid, ids, name, attr, context=None):
#         context = dict(context or {})
#         res = {}
#         uid_company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
#         for quant in self.browse(cr, uid, ids, context=context):
#             context.pop('force_company', None)
#             if quant.company_id.id != uid_company_id:
#                 #if the company of the quant is different than the current user company, force the company in the context
#                 #then re-do a browse to read the property fields for the good company.
#                 context['force_company'] = quant.company_id.id
#                 quant = self.browse(cr, uid, quant.id, context=context)
#             res[quant.id] = self._get_inventory_value(cr, uid, quant, context=context)
#         return res

#     def _get_inventory_value(self, cr, uid, quant, context=None):
#         if quant.cost:
#             return quant.cost * quant.qty
#         else:
#             return quant.product_id.standard_price * quant.qty
    
    
#     def _get_change_stock_move(self, cr, uid, ids, context=None):
#         result = {}
#         for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
#             for quant in move.quant_ids:
#                 result[quant.id] = True
#         return result.keys()
    
#     def _get_picking_type(self, cr, uid, ids, name, attr, context=None):
#         context = dict(context or {})
#         res = {}
#         for quant in self.browse(cr, uid, ids, context=context):
#             picking_type_id = False
#             for move in quant.history_ids:
#                 picking_type_id = move.picking_id.picking_type_id.id or False
#             res[quant.id] = picking_type_id
#         return res
    
#     def _get_picking(self, cr, uid, ids, name, attr, context=None):
#         context = dict(context or {})
#         res = {}
#         for quant in self.browse(cr, uid, ids, context=context):
#             picking_id = False
#             for move in quant.history_ids:
#                 picking_id = move.picking_id.id
#             res[quant.id] = picking_id
#         return res
    
    _columns = {
            #Thanh: Help to filter, should be stored
            'categ_id': fields.related('product_id', 'categ_id', type='many2one', 
                                       relation="product.category", 
                                       string='Category', store=True, readonly=True),
                
#             'inventory_value': fields.function(_calc_inventory_value, string="Inventory Value", type='float', readonly=True,store={
#                 'stock.quant': (lambda self, cr, uid, ids, c={}: ids, ['cost', 'product_id', 'qty','in_date','reservation_id'], 10),
#                 'stock.move': (_get_change_stock_move,['price_unit'],['product_uom_qty'], 10),                                                                                                  
#             }),
                
            #kiet: Get price giao dich
#             'picking_type_id':fields.function(_get_picking_type, string="Picking Type",relation='stock.picking.type', 
#                   type='many2one', readonly=True,store={
#                     'stock.quant': (lambda self, cr, uid, ids, c={}: ids, ['cost', 'product_id', 'qty','in_date','reservation_id'], 10),
#                     'stock.move': (_get_change_stock_move,['price_unit'],['product_uom_qty'], 10),        
#                 }),
#             'picking_id':fields.function(_get_picking, string="Picking", type='many2one',relation='stock.picking', readonly=True,),
    }
    
    #THANH: in_date of stock quant must be the same with stock_move date
    def _quant_create(self, cr, uid, qty, move, lot_id=False, owner_id=False, src_package_id=False, dest_package_id=False,
                      force_location_from=False, force_location_to=False, context=None):
        '''Create a quant in the destination location and create a negative quant in the source location if it's an internal location.
        '''
        if context is None:
            context = {}
        price_unit = self.pool.get('stock.move').get_price_unit(cr, uid, move, context=context)
        location = force_location_to or move.location_dest_id
        rounding = move.product_id.uom_id.rounding
        
        #THANH: Set in_date
        in_date = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if move.picking_id:
            in_date = move.picking_id.date_done
        else:
            in_date = move.date
        #THANH: Set in_date
          
        vals = {
            'product_id': move.product_id.id,
            'location_id': location.id,
            'qty': float_round(qty, precision_rounding=rounding),
            'cost': price_unit,
            'history_ids': [(4, move.id)],
            'in_date': in_date,
            'company_id': move.company_id.id,
            'lot_id': lot_id,
            'owner_id': owner_id,
            'package_id': dest_package_id,
        }
        if move.location_id.usage == 'internal':
            #if we were trying to move something from an internal location and reach here (quant creation),
            #it means that a negative quant has to be created as well.
            negative_vals = vals.copy()
            negative_vals['location_id'] = force_location_from and force_location_from.id or move.location_id.id
            negative_vals['qty'] = float_round(-qty, precision_rounding=rounding)
            negative_vals['cost'] = price_unit
            negative_vals['negative_move_id'] = move.id
            negative_vals['package_id'] = src_package_id
            negative_quant_id = self.create(cr, SUPERUSER_ID, negative_vals, context=context)
            vals.update({'propagated_from_id': negative_quant_id})

        # In case of serial tracking, check if the product does not exist somewhere internally already
        picking_type = move.picking_id and move.picking_id.picking_type_id or False
        if lot_id and move.product_id.tracking == 'serial' and (not picking_type or (picking_type.use_create_lots or picking_type.use_existing_lots)):
            if qty != 1.0:
                raise UserError(_('You should only receive by the piece with the same serial number'))
            other_quants = self.search(cr, uid, [('product_id', '=', move.product_id.id), ('lot_id', '=', lot_id),
                                                 ('qty', '>', 0.0), ('location_id.usage', '=', 'internal')], context=context)
            if other_quants:
                lot_name = self.pool['stock.production.lot'].browse(cr, uid, lot_id, context=context).name
                raise UserError(_('The serial number %s is already in stock') % lot_name)

        #create the quant as superuser, because we want to restrict the creation of quant manually: we should always use this method to create quants
        quant_id = self.create(cr, SUPERUSER_ID, vals, context=context)
        return self.browse(cr, uid, quant_id, context=context)
    
class stock_picking_type(osv.osv):
    _inherit = "stock.picking.type"
    
    _columns = {
        'default_location_transfer_id':fields.many2one('stock.location', 'Default Transit Location'),
        #Thanh: Add some options for code
        'code': fields.selection([('incoming', 'Suppliers'), 
                                  ('outgoing', 'Customers'), 
                                  ('internal', 'Internal'),
                                  ('transfer_out', 'Transfer Out'),
                                  ('transfer_in', 'Transfer In'),
                                  ('return_customer', 'Return Customers'), 
                                  ('return_supplier', 'Return Supplier'), 
                                  ('production_out', 'Production Out'),
                                  ('production_in', 'Production In'),
                                  ('phys_adj', 'Physical Adjustment')], 'Type of Operation', required=True),
        
        'is_service':fields.boolean('Service'),
        'is_product':fields.boolean('Product'),
        'is_materials':fields.boolean('Materials'),
        'is_tools':fields.boolean('Tools'),
        'is_consignment_agreement':fields.boolean('Consignment Agreement'),
        'dashboard_invisible': fields.boolean('Dashboard Invisible'),
        
        #THANH: For Security purpose (Filter data for user belong)
        'res_user_ids':fields.many2many('res.users', 'picking_type_users_ref','user_id','picking_type_id',
                                        'Allowed Users'),
        #Kiet: Transfer 
        'transfer_picking_type_id': fields.many2one('stock.picking.type', 'Picking type for transfer'),
    }
    
    _defaults = {
        'dashboard_invisible': False,
    }
    
    #THANH: Users can see owned picking type
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if uid != SUPERUSER_ID:# and not (context.get('warehouse_receipt',False) or context.get('warehouse_issue',False)):
            args.append('|')
            args.append(('res_user_ids','in', [uid]))
            args.append(('res_user_ids','=', False))
        return super(stock_picking_type, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
 
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    #THANH: Users can see owned picking type
    
stock_picking_type()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _default_picking_type_code(self, cr, uid, context=None):
        if 'default_picking_type_id' in context and context['default_picking_type_id']:
            picking_type = self.pool.get('stock.picking.type').browse(cr,uid,context['default_picking_type_id'])
            if picking_type.code in ('incoming', 'outgoing', 'return_customer', 'return_supplier'):
                return picking_type.code
        return False
    
    _columns = {
        #Thanh: Set this field editable
        'date_done': fields.datetime('Date of Transfer', 
                                     states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
                                     help="Completion Date of Transfer", readonly=False, copy=False),
        
        'move_lines': fields.one2many('stock.move', 'picking_id', string="Stock Moves", copy=True,
                                      readonly=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]}),
        
        #Thanh: Importing
        'file': fields.binary('File', help='Choose file Excel', states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},),
        'file_name':  fields.char('Filename', 100, readonly=True),
        'text_barcode': fields.char('Add Product', size=13, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},),
          
        #Thanh: Used for inter warehouse transfer
        'relation_internal_ids':fields.many2many('stock.picking','relation_internal_res','picking_id','relation_id','Relation internal'),
        'internal_relation_ids':fields.many2many('stock.picking','relation_internal_res','relation_id','picking_id','Relation internal'),
        'picking_type_code': fields.related('picking_type_id', 'code', type='selection',store =True, selection= [('incoming', 'Suppliers'), 
                                  ('outgoing', 'Customers'), 
                                  ('internal', 'Internal'),
                                  ('return_customer', 'Return Customers'), 
                                  ('return_supplier', 'Return Suppliers'), 
                                  ('production_out', 'Production Out'),
                                  ('transfer_in', 'Transfer in'),
                                  ('transfer_out', 'Transfer Out'),
                                  ('production_in', 'Production In'),
                                  ('phys_adj', 'Physical Adjustment')], string="picking_type_code"),
        
        #Thanh: Used to link invoice and picking
        'invoice_ids': fields.many2many('account.invoice', 'stock_invoice_rel', 'picking_id', 'invoice_id', 'Invoices', 
                                        help="Invoices generated for a picking order"),
        'picking_transfer_internal_ids':fields.many2many('stock.picking','transfer_internal_res','picking_id','transfer_id','Transfer internal'),
        'orign_transfer_internal_ids':fields.many2many('stock.picking','transfer_internal_res','transfer_id','picking_id','Transfer internal'),
        
    }   
    def _default_picking_type_id(self, cr, uid, context=None):
        picking_type_ids = self.pool.get('stock.picking.type').search(cr, uid, [], context=context)
        return picking_type_ids and picking_type_ids[0] 
    
    _defaults = {
        'picking_type_id': _default_picking_type_id,
        'file_name': 'import_picking.xls',
        'min_date': fields.datetime.now,
        'picking_type_code':_default_picking_type_code
    }
    
    #THANH: Users can see owned picking type
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if uid != SUPERUSER_ID:
            if context.get('warehouse_receipt',False) or context.get('warehouse_issue',False):
                cr.execute('''
                SELECT spt.default_location_src_id, spt.default_location_dest_id
                FROM stock_picking_type spt join picking_type_users_ref pr on spt.id=pr.user_id
                    and pr.picking_type_id = %s
                '''%(uid))
                res = cr.fetchall()
                default_location_src_ids = [x[0] for x in res]
                if context.get('warehouse_receipt',False):
                    args.append(('location_id','in', default_location_src_ids))
                if context.get('warehouse_issue',False):
                    args.append(('picking_type_id.res_user_ids','in', [uid]))
            else:
#                 args.append(('picking_type_id.res_user_ids','in', [uid]))
                args.append('|')
                args.append(('picking_type_id.res_user_ids','in', [uid]))
                args.append(('picking_type_id.res_user_ids','=', False))
        return super(stock_picking, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
    #THANH: Users can see owned picking type
    
    #THANH: Add product_id into compute_qty from UoM Object
    def _prepare_values_extra_move(self, cr, uid, op, product, remaining_qty, context=None):
        """
        Creates an extra move when there is no corresponding original move to be copied
        """
        uom_obj = self.pool.get("product.uom")
        uom_id = product.uom_id.id
        qty = remaining_qty
        if op.product_id and op.product_uom_id and op.product_uom_id.id != product.uom_id.id:
            if op.product_uom_id.factor > product.uom_id.factor: #If the pack operation's is a smaller unit
                uom_id = op.product_uom_id.id
                #HALF-UP rounding as only rounding errors will be because of propagation of error from default UoM
                qty = uom_obj._compute_qty_obj(cr, uid, product.uom_id, remaining_qty, op.product_uom_id, product_id=product.id, rounding_method='HALF-UP')
        picking = op.picking_id
        ref = product.default_code
        name = '[' + ref + ']' + ' ' + product.name if ref else product.name
        proc_id = False
        for m in op.linked_move_operation_ids:
            if m.move_id.procurement_id:
                proc_id = m.move_id.procurement_id.id
                break
        res = {
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': product.id,
            'procurement_id': proc_id,
            'product_uom': uom_id,
            'product_uom_qty': qty,
            'name': _('Extra Move: ') + name,
            'state': 'draft',
            'restrict_partner_id': op.owner_id,
            'group_id': picking.group_id.id,
            }
        return res
    
    #THANH: Add product_id into compute_qty from UoM Object
    def recompute_remaining_qty(self, cr, uid, picking, done_qtys=False, context=None):
        def _create_link_for_index(operation_id, index, product_id, qty_to_assign, quant_id=False):
            move_dict = prod2move_ids[product_id][index]
            qty_on_link = min(move_dict['remaining_qty'], qty_to_assign)
            self.pool.get('stock.move.operation.link').create(cr, uid, {'move_id': move_dict['move'].id, 'operation_id': operation_id, 'qty': qty_on_link, 'reserved_quant_id': quant_id}, context=context)
            if move_dict['remaining_qty'] == qty_on_link:
                prod2move_ids[product_id].pop(index)
            else:
                move_dict['remaining_qty'] -= qty_on_link
            return qty_on_link

        def _create_link_for_quant(operation_id, quant, qty):
            """create a link for given operation and reserved move of given quant, for the max quantity possible, and returns this quantity"""
            if not quant.reservation_id.id:
                return _create_link_for_product(operation_id, quant.product_id.id, qty)
            qty_on_link = 0
            for i in range(0, len(prod2move_ids[quant.product_id.id])):
                if prod2move_ids[quant.product_id.id][i]['move'].id != quant.reservation_id.id:
                    continue
                qty_on_link = _create_link_for_index(operation_id, i, quant.product_id.id, qty, quant_id=quant.id)
                break
            return qty_on_link

        def _create_link_for_product(operation_id, product_id, qty):
            '''method that creates the link between a given operation and move(s) of given product, for the given quantity.
            Returns True if it was possible to create links for the requested quantity (False if there was not enough quantity on stock moves)'''
            qty_to_assign = qty
            prod_obj = self.pool.get("product.product")
            product = prod_obj.browse(cr, uid, product_id)
            rounding = product.uom_id.rounding
            qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            if prod2move_ids.get(product_id):
                while prod2move_ids[product_id] and qtyassign_cmp > 0:
                    qty_on_link = _create_link_for_index(operation_id, 0, product_id, qty_to_assign, quant_id=False)
                    qty_to_assign -= qty_on_link
                    qtyassign_cmp = float_compare(qty_to_assign, 0.0, precision_rounding=rounding)
            return qtyassign_cmp == 0

        uom_obj = self.pool.get('product.uom')
        package_obj = self.pool.get('stock.quant.package')
        quant_obj = self.pool.get('stock.quant')
        link_obj = self.pool.get('stock.move.operation.link')
        quants_in_package_done = set()
        prod2move_ids = {}
        still_to_do = []
        #make a dictionary giving for each product, the moves and related quantity that can be used in operation links
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not prod2move_ids.get(move.product_id.id):
                prod2move_ids[move.product_id.id] = [{'move': move, 'remaining_qty': move.product_qty}]
            else:
                prod2move_ids[move.product_id.id].append({'move': move, 'remaining_qty': move.product_qty})

        need_rereserve = False
        #sort the operations in order to give higher priority to those with a package, then a serial number
        operations = picking.pack_operation_ids
        operations = sorted(operations, key=lambda x: ((x.package_id and not x.product_id) and -4 or 0) + (x.package_id and -2 or 0) + (x.pack_lot_ids and -1 or 0))
        #delete existing operations to start again from scratch
        links = link_obj.search(cr, uid, [('operation_id', 'in', [x.id for x in operations])], context=context)
        if links:
            link_obj.unlink(cr, uid, links, context=context)
        #1) first, try to create links when quants can be identified without any doubt
        for ops in operations:
            lot_qty = {}
            for packlot in ops.pack_lot_ids:
                lot_qty[packlot.lot_id.id] = uom_obj._compute_qty(cr, uid, ops.product_uom_id.id, packlot.qty, ops.product_id.uom_id.id, product_id=ops.product_id.id)
            #for each operation, create the links with the stock move by seeking on the matching reserved quants,
            #and deffer the operation if there is some ambiguity on the move to select
            if ops.package_id and not ops.product_id and (not done_qtys or ops.qty_done):
                #entire package
                quant_ids = package_obj.get_content(cr, uid, [ops.package_id.id], context=context)
                for quant in quant_obj.browse(cr, uid, quant_ids, context=context):
                    remaining_qty_on_quant = quant.qty
                    if quant.reservation_id:
                        #avoid quants being counted twice
                        quants_in_package_done.add(quant.id)
                        qty_on_link = _create_link_for_quant(ops.id, quant, quant.qty)
                        remaining_qty_on_quant -= qty_on_link
                    if remaining_qty_on_quant:
                        still_to_do.append((ops, quant.product_id.id, remaining_qty_on_quant))
                        need_rereserve = True
            elif ops.product_id.id:
                #Check moves with same product
                product_qty = ops.qty_done if done_qtys else ops.product_qty
                qty_to_assign = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, product_qty, ops.product_id.uom_id, product_id=ops.product_id.id, context=context)
                for move_dict in prod2move_ids.get(ops.product_id.id, []):
                    move = move_dict['move']
                    for quant in move.reserved_quant_ids:
                        if not qty_to_assign > 0:
                            break
                        if quant.id in quants_in_package_done:
                            continue

                        #check if the quant is matching the operation details
                        if ops.package_id:
                            flag = quant.package_id and bool(package_obj.search(cr, uid, [('id', 'child_of', [ops.package_id.id])], context=context)) or False
                        else:
                            flag = not quant.package_id.id
                        flag = flag and (ops.owner_id.id == quant.owner_id.id)
                        if flag:
                            if not lot_qty:
                                max_qty_on_link = min(quant.qty, qty_to_assign)
                                qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                qty_to_assign -= qty_on_link
                            else:
                                if lot_qty.get(quant.lot_id.id): #if there is still some qty left
                                    max_qty_on_link = min(quant.qty, qty_to_assign, lot_qty[quant.lot_id.id])
                                    qty_on_link = _create_link_for_quant(ops.id, quant, max_qty_on_link)
                                    qty_to_assign -= qty_on_link
                                    lot_qty[quant.lot_id.id] -= qty_on_link

                qty_assign_cmp = float_compare(qty_to_assign, 0, precision_rounding=ops.product_id.uom_id.rounding)
                if qty_assign_cmp > 0:
                    #qty reserved is less than qty put in operations. We need to create a link but it's deferred after we processed
                    #all the quants (because they leave no choice on their related move and needs to be processed with higher priority)
                    still_to_do += [(ops, ops.product_id.id, qty_to_assign)]
                    need_rereserve = True

        #2) then, process the remaining part
        all_op_processed = True
        for ops, product_id, remaining_qty in still_to_do:
            all_op_processed = _create_link_for_product(ops.id, product_id, remaining_qty) and all_op_processed
        return (need_rereserve, all_op_processed)
    
    #THANH: Check UoM Factor smaller than Product UoM
    def check_uom_smaller(self, uom_id, product):
        for line in product.uom_ids:
            if line.uom_id.id == uom_id.id and (line.factor < 1 or line.uom_type == 'smaller'):
                return True
        if uom_id.factor > product.uom_id.factor:
            return True
        return False
    
    #THANH: No need to check small UoM with Product UoM, just get the same move UoM for pack operation
    def _prepare_pack_ops(self, cr, uid, picking, quants, forced_qties, context=None):
        """ returns a list of dict, ready to be used in create() of stock.pack.operation.

        :param picking: browse record (stock.picking)
        :param quants: browse record list (stock.quant). List of quants associated to the picking
        :param forced_qties: dictionary showing for each product (keys) its corresponding quantity (value) that is not covered by the quants associated to the picking
        """
        def _picking_putaway_apply(product):
            location = False
            # Search putaway strategy
            if product_putaway_strats.get(product.id):
                location = product_putaway_strats[product.id]
            else:
                location = self.pool.get('stock.location').get_putaway_strategy(cr, uid, picking.location_dest_id, product, context=context)
                product_putaway_strats[product.id] = location
            return location or picking.location_dest_id.id

        # If we encounter an UoM that is smaller than the default UoM or the one already chosen, use the new one instead.
        product_uom = {} # Determines UoM used in pack operations
        location_dest_id = None
        location_id = None
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if not product_uom.get(move.product_id.id):
                product_uom[move.product_id.id] = move.product_id.uom_id
#             if move.product_uom.id != move.product_id.uom_id.id and move.product_uom.factor > product_uom[move.product_id.id].factor:
#                 product_uom[move.product_id.id] = move.product_uom
            
            #THANH: Check smaller UoM factor from Product Conversion Table
            smaller = self.check_uom_smaller(move.product_uom, move.product_id)
            if move.product_uom.id != move.product_id.uom_id.id and smaller:
                product_uom[move.product_id.id] = move.product_uom
                
            if not move.scrapped:
                if location_dest_id and move.location_dest_id.id != location_dest_id:
                    raise UserError(_('The destination location must be the same for all the moves of the picking.'))
                location_dest_id = move.location_dest_id.id
                if location_id and move.location_id.id != location_id:
                    raise UserError(_('The source location must be the same for all the moves of the picking.'))
                location_id = move.location_id.id

        pack_obj = self.pool.get("stock.quant.package")
        quant_obj = self.pool.get("stock.quant")
        vals = []
        qtys_grouped = {}
        lots_grouped = {}
        #for each quant of the picking, find the suggested location
        quants_suggested_locations = {}
        product_putaway_strats = {}
        for quant in quants:
            if quant.qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(quant.product_id)
            quants_suggested_locations[quant] = suggested_location_id

        #find the packages we can movei as a whole
        top_lvl_packages = self._get_top_level_packages(cr, uid, quants_suggested_locations, context=context)
        # and then create pack operations for the top-level packages found
        for pack in top_lvl_packages:
            pack_quant_ids = pack_obj.get_content(cr, uid, [pack.id], context=context)
            pack_quants = quant_obj.browse(cr, uid, pack_quant_ids, context=context)
            vals.append({
                    'picking_id': picking.id,
                    'package_id': pack.id,
                    'product_qty': 1.0,
                    'location_id': pack.location_id.id,
                    'location_dest_id': quants_suggested_locations[pack_quants[0]],
                    'owner_id': pack.owner_id.id,
                })
            #remove the quants inside the package so that they are excluded from the rest of the computation
            for quant in pack_quants:
                del quants_suggested_locations[quant]
        # Go through all remaining reserved quants and group by product, package, owner, source location and dest location
        # Lots will go into pack operation lot object
        for quant, dest_location_id in quants_suggested_locations.items():
            key = (quant.product_id.id, quant.package_id.id, quant.owner_id.id, quant.location_id.id, dest_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += quant.qty
            else:
                qtys_grouped[key] = quant.qty
            if quant.product_id.tracking != 'none' and quant.lot_id:
                lots_grouped.setdefault(key, {}).setdefault(quant.lot_id.id, 0.0)
                lots_grouped[key][quant.lot_id.id] += quant.qty

        # Do the same for the forced quantities (in cases of force_assign or incomming shipment for example)
        for product, qty in forced_qties.items():
            if qty <= 0:
                continue
            suggested_location_id = _picking_putaway_apply(product)
            key = (product.id, False, picking.owner_id.id, picking.location_id.id, suggested_location_id)
            if qtys_grouped.get(key):
                qtys_grouped[key] += qty
            else:
                qtys_grouped[key] = qty

        # Create the necessary operations for the grouped quants and remaining qtys
        uom_obj = self.pool.get('product.uom')
        prevals = {}
        for key, qty in qtys_grouped.items():
            product = self.pool.get("product.product").browse(cr, uid, key[0], context=context)
            uom_id = product.uom_id.id
            qty_uom = qty
            if product_uom.get(key[0]):
                uom_id = product_uom[key[0]].id
                #THANH: Add product_id to compute_qty
                qty_uom = uom_obj._compute_qty(cr, uid, product.uom_id.id, qty, uom_id, product_id=product.id)
            pack_lot_ids = []
            if lots_grouped.get(key):
                for lot in lots_grouped[key].keys():
                    pack_lot_ids += [(0, 0, {'lot_id': lot, 'qty': 0.0, 'qty_todo': lots_grouped[key][lot]})]
            val_dict = {
                'picking_id': picking.id,
                'product_qty': qty_uom,
                'product_id': key[0],
                'package_id': key[1],
                'owner_id': key[2],
                'location_id': key[3],
                'location_dest_id': key[4],
                'product_uom_id': uom_id,
                'pack_lot_ids': pack_lot_ids,
            }
            if key[0] in prevals:
                prevals[key[0]].append(val_dict)
            else:
                prevals[key[0]] = [val_dict]
        # prevals var holds the operations in order to create them in the same order than the picking stock moves if possible
        processed_products = set()
        for move in [x for x in picking.move_lines if x.state not in ('done', 'cancel')]:
            if move.product_id.id not in processed_products:
                vals += prevals.get(move.product_id.id, [])
                processed_products.add(move.product_id.id)
        return vals
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_picking,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
           
        if view_type == 'form':
            #Thanh: Filter partner_id in Picking Form
            picking_type_id = context.get('search_default_picking_type_id', False)
            doc = etree.XML(res['arch'])
            if picking_type_id:
                picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
                if picking_type.code in ['incoming','return_supplier']:
                    for node in doc.xpath("//field[@name='partner_id']"):
                        node.set('domain', "[('supplier', '=', True)]")
                        node.set('required', "True")
                        node.set('context', "{'default_company_type': 'company', 'default_supplier': True, 'default_customer': False}")
#                     for field in res['fields']:
#                         if field == 'partner_id':
#                             res['fields'][field]['domain'] = [('supplier', '=', True)]
#                             res['fields'][field]['required'] = True
#                             res['fields'][field]['context'] = {'default_company_type': 'company', 'default_supplier': True, 'default_customer': False}
                elif picking_type.code in ['outgoing','return_customer']:
                    for node in doc.xpath("//field[@name='partner_id']"):
                        node.set('domain', "[('customer', '=', True)]")
                        node.set('required', "True")
                        node.set('context', "{'default_company_type': 'company', 'default_supplier': False, 'default_customer': True}")
#                     for field in res['fields']:
#                         if field == 'partner_id':
#                             res['fields'][field]['domain'] = [('customer', '=', True)]
#                             res['fields'][field]['required'] = True
#                             res['fields'][field]['context'] = {'default_company_type': 'company', 'default_supplier': False, 'default_customer': True}
                else:
                    for node in doc.xpath("//field[@name='partner_id']"):
                        node.set('domain', "[('customer', '=', False), ('supplier', '=', False)]")
                        node.set('context', "{'default_company_type': 'person', 'default_supplier': False, 'default_customer': False}")
#                     for field in res['fields']:
#                         if field == 'partner_id':
#                             res['fields'][field]['domain'] = [('customer', '=', False), ('supplier', '=', False)]
#                             res['fields'][field]['context'] = {'default_company_type': 'person', 'default_supplier': False, 'default_customer': False}
                            
            if context.has_key('warehouse_issue') or context.has_key('warehouse_receipt'):
                for node in doc.xpath("//field[@name='picking_type_id']"):
                    node.set('domain', "[('code', '=', 'internal')]")
#                 for field in res['fields']:
#                         if field == 'picking_type_id':
#                             res['fields'][field]['domain'] = [('code', '=', 'internal')]
            res['arch'] = etree.tostring(doc)
        return res
    
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if context.has_key('warehouse_receipt'):
            raise osv.except_osv(_('Error!'),_("Can not create Internal Receipt manually, it should be generated from 'Internal Issues' menu"))
        return super(stock_picking, self).create(cr, uid, vals, context=context)
    
    def onchange_picking_type(self, cr, uid, ids, picking_type_id, partner_id, context=None):
        context = context or {}
        value ={}
        domain = {}
        
        #THANH: Warehouse Transfers
        if picking_type_id and context.has_key('warehouse_issue'):
            picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
            if not picking_type.default_location_transfer_id:
                value = {'picking_type_id': False}
                warning = {
                   'title': _('Warning!'),
                   'message' : _("Please define 'Default Transit Location' in Picking Type '%s' !!!"%(picking_type.name))
                }
                return {'value': value, 'warning': warning}
            value ={
              'location_id': picking_type.default_location_src_id.id,
              'location_dest_id': picking_type.default_location_transfer_id.id}
            return {'value': value}
    
        #THANH: Not Warehouse Transfers
        if not picking_type_id:
            value.update({'location_id':False,
                           'location_dest_id':False,
                           'picking_type_code': False})
            domain.update({'location_id':[('id','=',False)],
                           'location_dest_id':[('id','=',False)]})
        else:
            picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
            
            location_id = picking_type.default_location_src_id.id or False
            location_dest_id = picking_type.default_location_dest_id.id or False
            
            domain.update({'location_id':[('id','=',location_id)],
                           'location_dest_id':[('id','=',location_dest_id)]})
            
            if location_dest_id and location_dest_id != location_id:
                location_dest_id = location_dest_id
            value.update({'location_id':location_id,
                          'location_dest_id': location_dest_id,
                          'picking_type_code': picking_type.code})
        return {'value': value,'domain':domain}
    
    def import_file(self, cr, uid, ids ,context=None):
        this = self.browse(cr, uid, ids[0])
        exist_move_ids = []
        move_obj = self.pool.get('stock.move')
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            for row in range(sh.nrows):
                if row > 0:
                    product_qty = sh.cell(row,1).value or 0.0
                    barcode = sh.cell(row,0).value
                    price = sh.cell(row,2).value or 0.0
                    if isinstance(barcode, float):
                        barcode = int(barcode)
                        barcode = str(barcode)
                    product_id = self.pool.get('product.product').search(cr, uid, ['|', 
                                                 ('default_code','=', barcode), 
                                                 ('barcode','=', barcode)])
                    if product_id:
                        product_id = product_id[0] or False
                    else:
                        raise osv.except_osv(_('Warning!'), _('The Barcode ' + barcode +' is not exist !!!'))
                    cr.execute('select id, product_uom_qty from stock_move where picking_id=%s and product_id=%s'%(ids[0], product_id))
                    line = cr.fetchone()
                    if line and line[0]:
                        new_qty = product_qty
                        move_obj.write(cr, uid, [line[0]], {'product_uom_qty': new_qty})
                        exist_move_ids.append(line[0])
                    else:
                        pick_type = this.picking_type_id
                        if context.has_key('warehouse_issue'):
                            location_id = pick_type.default_location_src_id.id
                            location_dest_id = pick_type.default_location_transfer_id.id
                        else:
                            location_id = pick_type.default_location_src_id.id
                            location_dest_id = pick_type.default_location_dest_id.id
                        res = move_obj.onchange_product_id(cr, uid, False, prod_id=product_id, 
                                                loc_id=False, loc_dest_id=False, partner_id=this.partner_id.id)
                        
                        vals = res['value']
                        vals.update({
                                    'picking_id': ids[0],
                                    'product_id': product_id,
                                    'product_uom_qty': product_qty,
                                    'price_unit': price,
                                    'address_in_id': this.partner_id.id,
                                    'picking_type_id': this.picking_type_id.id,
                                    'location_id': location_id,
                                    'location_dest_id': location_dest_id,
                                    'state': 'draft'
                                    })
                        new_id = move_obj.create(cr, uid, vals)
                        exist_move_ids.append(new_id)
            
            #Thanh: Remove line is not in import file
            unlink_ids = []
            for move in this.move_lines:
                if move.id not in exist_move_ids:
                    unlink_ids.append(move.id)
                    
            move_obj.unlink(cr, uid, unlink_ids)
            self.write(cr, uid, ids, {'file': False})
        return True
    
    def onchange_barcode(self, cr, uid, ids, text_barcode, partner_id, picking_type_id, move_lines, context=None):
        if not text_barcode:
            return {}
        valss = []
        vals ={}
        new_flag= True
         
        move_line_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        pick_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id, context=context)
        product_ids = product_obj.search(cr,uid,['|', 
                                                 ('default_code','=', text_barcode), 
                                                 ('barcode','=', text_barcode)])
        if len(product_ids):
            new_qty = 1
            new_flag = True
            product_id = product_ids[0]
            if move_lines[0]:
                for line in move_lines:
                    if not (len(line) > 2):
                        continue
                    if 'product_id' in line[2]:
                        valss.append(line[2])
                        if line[2]['product_id'] == product_id:
                            line[2]['product_uom_qty'] = line[2]['product_uom_qty'] +1
#                             line[2]['product_uos_qty'] =line[2]['product_uos_qty'] +1
                            new_flag = False
                    else:
                        for move in self.pool.get('stock.move').browse(cr,uid,line[2]):
                            if move.product_id.id == product_id:
#                                 product_uos_qty = move.product_uos_qty + 1
                                product_uom_qty = move.product_uom_qty + 1
                                sql =''' DELETE from stock_move where id = %s'''%(move.id)
                                cr.execute(sql)
                                if context.has_key('warehouse_issue'):
                                    location_id = pick_type.default_location_src_id.id
                                    location_dest_id = pick_type.default_location_transfer_id.id
                                else:
                                    location_id = pick_type.default_location_src_id.id
                                    location_dest_id = pick_type.default_location_dest_id.id
                                res = move_line_obj.onchange_product_id(cr, uid, False, prod_id=product_id, 
                                                        loc_id=False, loc_dest_id=False, partner_id=partner_id)
                                vals = res['value']
                                vals.update({
                                    'product_id': product_id,
                                    'product_uom_qty': product_uom_qty, 
                                    'address_in_id': partner_id,
                                    'picking_type_id': picking_type_id,
                                    'location_id': location_id,
                                    'location_dest_id': location_dest_id,
                                    'state': 'draft',
                                    'scrapped': False,
                                    })
                                vals = [0, False,vals]
                                new_flag = False
                            else:
                                vals = [1, move.id, {}]
                            valss.append(vals)
                             
            if new_flag:
                if context.has_key('warehouse_issue'):
                    location_id = pick_type.default_location_src_id.id
                    location_dest_id = pick_type.default_location_transfer_id.id
                else:
                    location_id = pick_type.default_location_src_id.id
                    location_dest_id = pick_type.default_location_dest_id.id
                res = move_line_obj.onchange_product_id(cr, uid, False, prod_id=product_id, 
                                        loc_id=False, loc_dest_id=False, partner_id=partner_id)
                vals = res['value']
                vals.update({
                            'product_id': product_id,
                            'product_uom_qty': new_qty, 
                            'address_in_id': partner_id,
                            'picking_type_id': picking_type_id,
                            'location_id': location_id,
                            'location_dest_id': location_dest_id,
                            'state': 'draft',
                            'scrapped': False,
                            })
                vals = [0, False,vals]
                valss.append(vals)
        else:
            warning = {
               'title': _('Warning!'),
               'message' : _('This Barcode is not exist !!!')
            }
            return {'warning': warning}
        value = {'text_barcode': False, 'move_lines': valss}
        return {'value': value}
    
    
    def do_transfer(self, cr, uid, ids, context=None):
        """
            If no pack operation, we do simple action_done of the picking
            Otherwise, do the pack operations
        """
        if not context:
            context = {}

        stock_move_obj = self.pool.get('stock.move')
        self.create_lots_for_picking(cr, uid, ids, context=context)
        for picking in self.browse(cr, uid, ids, context=context):
            if not picking.pack_operation_ids:
                pick = self.pool.get('stock.picking').browse(cr,uid,picking.id)
                pick.action_done()
                continue
            else:
                need_rereserve, all_op_processed = self.picking_recompute_remaining_quantities(cr, uid, picking, context=context)
                #create extra moves in the picking (unexpected product moves coming from pack operations)
                todo_move_ids = []
                if not all_op_processed:
                    todo_move_ids += self._create_extra_moves(cr, uid, picking, context=context)

                #split move lines if needed
                toassign_move_ids = []
                for move in picking.move_lines:
                    remaining_qty = move.remaining_qty
                    if move.state in ('done', 'cancel'):
                        #ignore stock moves cancelled or already done
                        continue
                    elif move.state == 'draft':
                        toassign_move_ids.append(move.id)
                    if float_compare(remaining_qty, 0,  precision_rounding = move.product_id.uom_id.rounding) == 0:
                        if move.state in ('draft', 'assigned', 'confirmed'):
                            todo_move_ids.append(move.id)
                    elif float_compare(remaining_qty,0, precision_rounding = move.product_id.uom_id.rounding) > 0 and \
                                float_compare(remaining_qty, move.product_qty, precision_rounding = move.product_id.uom_id.rounding) < 0:
                        new_move = stock_move_obj.split(cr, uid, move, remaining_qty, context=context)
                        todo_move_ids.append(move.id)
                        #Assign move as it was assigned before
                        toassign_move_ids.append(new_move)
                todo_move_ids = list(set(todo_move_ids))
                if need_rereserve or not all_op_processed: 
                    if not picking.location_id.usage in ("supplier", "production", "inventory"):
                        self.rereserve_quants(cr, uid, picking, move_ids=todo_move_ids, context=context)
                    self.do_recompute_remaining_quantities(cr, uid, [picking.id], context=context)
                if todo_move_ids and not context.get('do_only_split'):
                    self.pool.get('stock.move').action_done(cr, uid, todo_move_ids, context=context)
                elif context.get('do_only_split'):
                    context = dict(context, split=todo_move_ids)
            self._create_backorder(cr, uid, picking, context=context)
            
            #Thanh: For warehouse transfer
            if picking.picking_type_id.code == 'internal' and picking.location_id.usage=='internal' and picking.location_dest_id.usage=='transit':
                location_transfer_id = picking.picking_type_id.default_location_transfer_id.id
                default_val = {
                    'location_id': location_transfer_id,
                    'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                    'origin':picking.name,
                    'move_lines':False,
                    'state':'assigned'
                }
                new_pick_id = self.copy(cr, uid, picking.id, default_val)
                self.write(cr, uid, [picking.id], {'relation_internal_ids':[(6, 0,[new_pick_id] )]})
                 
                for line in picking.move_lines:
                    default_move ={
                      'location_id': location_transfer_id,
                      'location_dest_id': picking.picking_type_id.default_location_dest_id.id,
                      'picking_id':new_pick_id,
                      'state':'assigned'}
                    self.pool.get('stock.move').copy(cr, uid, line.id, default_move)
            # kiet viet cho trừo7ng2 hợp chuyển kho transfer
            #self.transfer(cr, uid, ids, context)
        return True
    
    
    
    #THANH: Check cancel in case Warehouse Transfers
    def action_cancel(self, cr, uid, ids, context=None):
        for pick in self.browse(cr, uid, ids, context=context):
            #THANH: Trường hợp Return to transfer
            if pick.picking_type_id.code == 'internal' and pick.location_id.usage == 'transit' and pick.location_dest_id.usage  == 'internal':
                src_location_id = False
                src_location_dest_id = False
                if pick.picking_type_id.code == 'internal':
                    src_location_id = pick.picking_type_id.default_location_src_id.id
                    src_location_dest_id = pick.picking_type_id.default_location_dest_id.id
                    src_location_transfer_id = pick.picking_type_id.default_location_transfer_id.id
                    
                    picking_type_ids = self.pool.get('stock.picking.type').search(cr,uid,
                                            [('code','=','internal'),
                                            ('default_location_src_id','=',src_location_dest_id),
                                             ('default_location_dest_id','=',src_location_id)])
                    if not picking_type_ids:
                        raise osv.except_osv(_('Error!'),_("No define Picking type. Please contact Administrator!!!"))
                    
                    default_val = {
                        'location_id': src_location_transfer_id,
                        'location_dest_id': src_location_id,
                        'origin':pick.name,
                        'move_lines':False,
                        'state':'assigned',
                        'picking_type_id':picking_type_ids[0]
                    }
                    new_pick_id = self.copy(cr, uid, pick.id, default_val)
                    self.write(cr,uid,[pick.id],{'relation_internal_ids':[(6, 0,[new_pick_id] )]})
                     
                    for line in pick.move_lines:
                        default_move ={
                          'location_id': src_location_transfer_id,
                          'location_dest_id': src_location_id,
                          'picking_id': new_pick_id,
                          'state': 'assigned'
                        }
                        self.pool.get('stock.move').copy(cr, uid, line.id, default_move)
                        
            ids2 = [move.id for move in pick.move_lines]
            self.pool.get('stock.move').action_cancel(cr, uid, ids2, context)
        return True
    
    #Thanh: Reopen Picking
    def action_revert_done(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        for picking in self.browse(cr, uid, ids, context):
            sql ='''
                DELETE FROM stock_pack_operation where picking_id =%s
            '''%(picking.id)
            cr.execute(sql)
            for move in picking.move_lines:
                quant_ids = [x.id for x in move.quant_ids]
                if len(quant_ids):
                    default_val = {
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': move.location_id.id,
                        'scrapped': True,
                        'picking_id': False,
                    }
                    new_move_id = move_obj.copy(cr, uid, move.id, default_val)
                    move_obj.action_done(cr, uid, [new_move_id])
                    #Thanh: Delete these revert move to balance stock
                    try:
                        cr.execute('''DELETE FROM stock_picking 
                                        WHERE id in (select picking_id from stock_move where id=%s)'''%(new_move_id))
                        cr.execute("DELETE FROM stock_move WHERE id=%s"%(new_move_id))
                    except Exception, ex:
                        pass
                    
                move_obj.action_cancel(cr, uid, [move.id])
                move_obj.write(cr, uid, [move.id], {'state': 'draft'})
                
            #Kiệt: Kiểm tra chuyển kho nội bộ
            if picking.picking_type_id.code =='internal' and picking.location_id.usage=='internal' and picking.location_dest_id.usage=='transit':
                for relation_internal_id in picking.relation_internal_ids:
                    if relation_internal_id.state in ('done'):
                        raise osv.except_osv(_('Error!'),_("Can not reopen this picking due to the related picking '%s' has been done.")%(relation_internal_id.name))
                    
                    operation_ids = self.pool.get('stock.pack.operation').search(cr, uid, [('picking_id','=',relation_internal_id.id)])
                    self.pool.get('stock.pack.operation').unlink(cr, uid, operation_ids)
                    self.unlink(cr, uid, [relation_internal_id.id])
        return True

stock_picking()

class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"
    
    #THANH: Add product_id to compute_qty of UoM Object
    def _get_remaining_qty(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for ops in self.browse(cr, uid, ids, context=context):
            res[ops.id] = 0
            if ops.package_id and not ops.product_id:
                #dont try to compute the remaining quantity for packages because it's not relevant (a package could include different products).
                #should use _get_remaining_prod_quantities instead
                continue
            else:
                qty = ops.product_qty
                if ops.product_uom_id:
                    qty = uom_obj._compute_qty_obj(cr, uid, ops.product_uom_id, ops.product_qty, ops.product_id.uom_id, product_id=ops.product_id.id, context=context)
                for record in ops.linked_move_operation_ids:
                    qty -= record.qty
                res[ops.id] = float_round(qty, precision_rounding=ops.product_id.uom_id.rounding)
        return res
    
    _columns = {
        #THANH: Add product_id to compute_qty of UoM Object
        'remaining_qty': fields.function(_get_remaining_qty, type='float', digits = 0, string="Remaining Qty", help="Remaining quantity in default UoM according to moves matched with this operation. "),
    }
    
    #THANH: Get date_done from picking to pack operation
    def create(self, cr, uid, vals, context=None):
        if vals.has_key('picking_id') and vals.get('picking_id',False):
            picking = self.pool.get('stock.picking').browse(cr, uid, vals['picking_id'])
            if picking.date_done:
                vals.update({'date': picking.date_done})
        return super(stock_pack_operation, self).create(cr, uid, vals, context=context)
        
class stock_move(osv.osv):
    _inherit = 'stock.move'
    _order = 'picking_id, sequence, id'
    
    
    #kiet: Không update giá, để cho trường hợp Gía promotion = 0
    def attribute_price(self, cr, uid, move, context=None):
        """
            Attribute price to move, important in inter-company moves or receipts with only one partner
        """
#         if not move.price_unit:
#             price = move.product_id.standard_price
#             self.write(cr, uid, [move.id], {'price_unit': move.price_unit})
        return True
    
    def init(self, cr):
        cr.execute('''
            UPDATE stock_move stm
            SET picking_type_id = (select picking_type_id from stock_picking where id=stm.picking_id)
            WHERE picking_type_id is null and picking_id is not null 
            ''')
        
        cr.execute('''
            UPDATE stock_move stm
            SET picking_type_id = (select picking_type_id from stock_inventory where id=stm.inventory_id)
            WHERE picking_type_id is null and inventory_id is not null 
            ''')
        return True
    
    #THANH: Add picking_type to stock move from stock picking or inventory
    def create(self, cr, uid, vals, context=None):
        new_id = super(stock_move, self).create(cr, uid, vals, context=context)
        if vals.has_key('picking_id') and vals.get('picking_id', False):
            cr.execute('''
            UPDATE stock_move stm
            SET picking_type_id = (select picking_type_id from stock_picking where id=%s)
            WHERE id=%s
            '''%(vals['picking_id'], new_id))
        if vals.has_key('inventory_id') and vals.get('inventory_id', False):
            cr.execute('''
            UPDATE stock_move stm
            SET picking_type_id = (select picking_type_id from stock_inventory where id=%s)
            WHERE id=%s
            '''%(vals['inventory_id'], new_id))
        return new_id
    
    def write(self, cr, uid, ids, vals, context=None):
        context = context or {}
        for move in self.browse(cr, uid, ids, context=context):
            #THANH: When change Qty in state in ('assigned', 'confirmed', 'waiting')
            #Picking should re-compute Pack Operation to prevent split picking with diff Qty
            if move.state in ('assigned', 'confirmed', 'waiting') and vals.has_key('product_uom_qty'):
                vals.update({'state': 'draft'})
        return super(stock_move, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        picking_ids = []
        for move in self.browse(cr, uid, ids, context=context):
            if move.state not in ('draft', 'cancel'):
                #THANH: Cancel it firstly
                self.action_cancel(cr, uid, [move.id], context=context)
                if move.picking_id:
                    picking_ids.append(move.picking_id.id)
        super(stock_move, self).unlink(cr, uid, ids, context=context)
        #THANH: Recompute Pack
        self.pool.get('stock.picking').do_prepare_partial(cr, uid, picking_ids)
        return True
    
    def action_done(self, cr, uid, ids, context=None):
        super(stock_move,self).action_done(cr, uid, ids, context=context)
        #THANH: Update the same stock_move with date done of stock_picking
        for move in self.browse(cr, uid, ids):
            if move.picking_id and move.picking_id.date_done:
                sql = '''
                UPDATE stock_move stm
                SET date = '%s', costed = false
                WHERE stm.id = %s
                '''%(move.picking_id.date_done, move.id)
                cr.execute(sql)
                
            if move.inventory_id and move.inventory_id.freeze_date:
                sql = '''
                    UPDATE stock_move stm
                    SET date = '%s'
                    WHERE stm.id = %s
                '''%(move.invnetory_id.freeze_date, move.id)
                cr.execute(sql)
        return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels the moves and if all moves are cancelled it cancels the picking.
        @return: True
        """
        procurement_obj = self.pool.get('procurement.order')
        context = context or {}
        procs_to_check = []
        for move in self.browse(cr, uid, ids, context=context):
#             if move.state == 'done':
#                 raise UserError(_('You cannot cancel a stock move that has been set to \'Done\'.'))
            if move.reserved_quant_ids:
                self.pool.get("stock.quant").quants_unreserve(cr, uid, move, context=context)
            if context.get('cancel_procurement'):
                if move.propagate:
                    procurement_ids = procurement_obj.search(cr, uid, [('move_dest_id', '=', move.id)], context=context)
                    procurement_obj.cancel(cr, uid, procurement_ids, context=context)
            else:
                if move.move_dest_id:
                    if move.propagate:
                        self.action_cancel(cr, uid, [move.move_dest_id.id], context=context)
                    elif move.move_dest_id.state == 'waiting':
                        #If waiting, the chain will be broken and we are not sure if we can still wait for it (=> could take from stock instead)
                        self.write(cr, uid, [move.move_dest_id.id], {'state': 'confirmed'}, context=context)
                if move.procurement_id:
                    # Does the same as procurement check, only eliminating a refresh
                    procs_to_check.append(move.procurement_id.id)

        res = self.write(cr, uid, ids, {'state': 'cancel', 'move_dest_id': False}, context=context)
        if procs_to_check:
            procurement_obj.check(cr, uid, procs_to_check, context=context)
        return res
    
#     def _get_product_info(self, cr, uid, ids, field_name, arg, context=None):
#         res = {}
#         uom_obj = self.pool.get('product.uom')
#         for line in self.browse(cr, uid, ids, context=context):
#             res[line.id] = {
#                             'uom_conversion': 0.0,
#                             'primary_qty': 0.0,
#                             }
#             if line.product_id.product_tmpl_id and line.product_uom:
#                 if line.product_uom.id != line.product_id.uom_id.id:
#                     if line.product_id.product_tmpl_id.uom_ids:
#                         res[line.id]['primary_qty'] = uom_obj._compute_qty(cr, uid, line.product_uom.id, line.product_uom_qty, line.product_id.uom_id.id, product_id=line.product_id.id)
#                     else:
#                         res[line.id]['primary_qty'] = uom_obj._compute_qty(cr, uid, line.product_uom.id, line.product_uom_qty, line.product_id.uom_id.id)
#                 else:
#                     res[line.id]['primary_qty'] = line.product_uom_qty
#                 res[line.id]['uom_conversion'] = line.product_uom_qty and round(res[line.id]['primary_qty']/line.product_uom_qty,3) or 0.0
#         return res
    
    def _compute_subtotal(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                            'price_subtotal': line.price_unit * line.product_uom_qty,
                            #'price_subtotal_vnd':line.price_currency * line.product_uom_qty,
                            }
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_move,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
         
        if view_type == 'tree':
            doc = etree.XML(res['arch'])
            #Thanh: Filter partner_id in Picking Form
            location_id = context.get('default_location_id', False)
            if location_id:
                location = self.pool.get('stock.location').browse(cr, uid, location_id)
                if location.usage not in ['supplier']:
#                     for node in doc.xpath("//field[@name='price_unit']"):
#                         node.set('readonly', "True")
#rw
                    #THANH: 
                    xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
                    res['arch'] = xarch
                    res['fields'] = xfields
#             res['arch'] = etree.tostring(doc)
        return res
    
    #THANH: Add product_id to compute_qty of UoM Object
    def _quantity_normalize(self, cr, uid, ids, name, args, context=None):
        uom_obj = self.pool.get('product.uom')
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = {'product_qty': 0.0,
                         'uom_conversion': 0.0}
            
            res[m.id]['product_qty'] = uom_obj._compute_qty_obj(cr, uid, m.product_uom, m.product_uom_qty, m.product_id.uom_id, product_id=m.product_id.id, context=context)
        
            #THANH: Compute uom_conversion
            res[m.id]['uom_conversion'] = m.product_uom_qty and round(res[m.id]['product_qty']/m.product_uom_qty,3) or 0.0
        return res
    
    def _set_product_qty(self, cr, uid, id, field, value, arg, context=None):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
            in the default product UoM. This code has been added to raise an error if a write is made given a value
            for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
            detect errors.
        """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))

    _columns = {
        #Thanh: Change this field to Store = True for sql query purpose
        'type': fields.related('picking_type_id', 'code', type='selection', selection=[
                                  ('incoming', 'Suppliers'), 
                                  ('outgoing', 'Customers'), 
                                  ('internal', 'Internal'),
                                  ('return_customer', 'Return Customers'), 
                                  ('return_supplier', 'Return Suppliers'), 
                                  ('production_out', 'Production Out'),
                                  ('production_in', 'Production In'),
                                  ('phys_adj', 'Physical Adjustment')], string="picking_type_code"),
        
        #THANH: Add product_id to compute_qty of UoM Object
        'product_qty': fields.function(_quantity_normalize, 
#                                        fnct_inv=_set_product_qty, 
                                       type='float', digits=0, store={
                'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['product_id', 'product_uom', 'product_uom_qty'], 10),
            }, string='Quantity',
                help='Quantity in the default UoM of the product', multi='pro_info'),
                
        'uom_conversion': fields.function(_quantity_normalize, string='Factor', type='float', digits= (16,4), store={
                'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['product_id','product_uom','product_qty'], 10),
            }, readonly=True, multi='pro_info'),
        
        #THANH: No need to you this field in V9 due to existing field product_qty (So replace all field primary_qty by product_qty)
#         'primary_qty': fields.function(_get_product_info, string='Primary Qty', digits_compute= dp.get_precision('Product Unit of Measure'), type='float',
#             store={
#                 'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['product_id','product_uom','product_qty'], 10),
#             }, readonly=True, multi='pro_info'),
                
        'categ_id': fields.related('product_id', 'categ_id', type='many2one', relation='product.category', store=True, string='Product Category'),
        'primary_uom_id': fields.related('product_id', 'uom_id', type='many2one', relation='product.uom', store=True, string='Primary UoM'),
        
        'price_subtotal': fields.function(_compute_subtotal, string='Subtotal', digits= (16,2), type='float',
#             store={
#                 'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['product_uom_qty','price_unit'], 10),
#             }, 
                                          readonly=True, multi='total_info'),
        
#         'price_subtotal_vnd': fields.function(_compute_subtotal, string='Subtotal vnd', digits= (16,0), type='float',
# #             store={
# #                 'stock.move': (lambda self, cr, uid, ids, c={}: ids, ['product_uom_qty','price_unit'], 10),
# #             }, 
#                                           readonly=True, multi='total_info'),
                
        # Kiet currency_rate
        'exchange_rate':fields.float('Exchange rate'),
        'currency_id':fields.many2one('res.currency','Currency'),
        
        # Kiet fields Costed
        'costed':fields.boolean('Costed'),
        'is_promotion':fields.boolean('Is Promotion'),
        'price_currency': fields.float(string="Price Currency",copy=False)
        
        #'valuation_move_id':fields.many2one('account.move','Valuation Move')
        }
    
    _defaults = {
        'costed':False,
        'exchange_rate':1,
        'is_promotion':False
    }
    
    def onchange_quantity(self, cr, uid, ids, product_id, product_qty, product_uom, price_unit=0.0):
        """ On change of product quantity finds UoM
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @return: Dictionary of values
        """
#         res = super(stock_move, self).onchange_quantity(cr, uid, ids, product_id, product_qty, product_uom)
        res = {}
        result = {}
        if (not product_id) or (product_qty <= 0.0):
            result['product_qty'] = 0.0
            return {'value': result}
        
        res['value'] = {'price_subtotal': product_qty * price_unit}
        return res
    
class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns={
              'wh_raw_material_loc_id': fields.many2one('stock.location', 'Raw Material Stock'),
              'wh_finished_good_loc_id': fields.many2one('stock.location', 'Finished Goods Stock'),
              'wh_production_loc_id': fields.many2one('stock.location', 'Production Stock'),
              'production_in_type_id': fields.many2one('stock.picking.type', 'Production Type - In'),
              'production_out_type_id': fields.many2one('stock.picking.type', 'Production Type - Out'),
              'return_customer_type_id': fields.many2one('stock.picking.type', 'Customer Returns'),
              'return_supplier_type_id': fields.many2one('stock.picking.type', 'Supplier Returns'),
              'other_location_loc_id':fields.many2one('stock.location', 'Other Location'),
              #'master_warehouse':fields.boolean('Master Warehouse')
              }
    
    _defaults = {
        'master_warehouse': False
    }
    
    #KIM: Auto define picking type when set up a new Warehouse
    def create_sequences_and_picking_types(self, cr, uid, warehouse, context=None):
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')
        #create new location
        wh_loc_id = warehouse.lot_stock_id.location_id or False
        location_obj.write(cr, uid, wh_loc_id.id, {'warehouse_id': warehouse.id})
        
        if not warehouse.wh_finished_good_loc_id:
            wh_finished_good_loc_id = location_obj.create(cr, uid, {'name': warehouse.name + _(' - Finished Goods Stock'),'usage': 'internal', 'location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)
        else:
            wh_finished_good_loc_id = warehouse.wh_finished_good_loc_id.id
        if not warehouse.wh_raw_material_loc_id:
            wh_raw_material_loc_id = location_obj.create(cr, uid, {'name': warehouse.name + _(' - Raw Material Stock'),'usage': 'internal','location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)
        else:
            wh_raw_material_loc_id = warehouse.wh_raw_material_loc_id.id
        if not warehouse.wh_production_loc_id:
            wh_production_loc_id = location_obj.create(cr, uid, {'name': warehouse.name + _(' - Production Stock'),'usage': 'internal','location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)    
        else:
            wh_production_loc_id = warehouse.wh_production_loc_id.id
            
        #create new sequences
        if not warehouse.in_type_id:
            in_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence in'), 'prefix': warehouse.code + '/IN/', 'padding': 5}, context=context)
        if not warehouse.out_type_id:
            out_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence out'), 'prefix': warehouse.code + '/OUT/', 'padding': 5}, context=context)
        if not warehouse.pack_type_id:
            pack_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence packing'), 'prefix': warehouse.code + '/PACK/', 'padding': 5}, context=context)
        if not warehouse.pick_type_id:
            pick_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence picking'), 'prefix': warehouse.code + '/PICK/', 'padding': 5}, context=context)
        if not warehouse.int_type_id:
            int_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence internal'), 'prefix': warehouse.code + '/INT/', 'padding': 5}, context=context)
        if not warehouse.production_in_type_id:
            production_in_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence produced-in'), 'prefix': warehouse.code + '/PRODUCED-IN/', 'padding': 5}, context=context)
        if not warehouse.production_out_type_id:
            production_out_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence produced-out'), 'prefix': warehouse.code + '/PRODUCED-OUT/', 'padding': 5}, context=context)
        if not warehouse.return_customer_type_id:
            return_customer_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence return customer'), 'prefix': warehouse.code + '/RETURN-CUSTOMER/', 'padding': 5}, context=context)
        if not warehouse.return_supplier_type_id:
            return_supplier_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence return supplier'), 'prefix': warehouse.code + '/RETURN-SUPPLIER/', 'padding': 5}, context=context)
        
        wh_stock_loc = warehouse.lot_stock_id
        location_obj.write(cr, uid, [wh_stock_loc.id], {'warehouse_id': warehouse.id})
        wh_input_stock_loc = warehouse.wh_input_stock_loc_id
        location_obj.write(cr, uid, [wh_input_stock_loc.id], {'warehouse_id': warehouse.id})
        wh_output_stock_loc = warehouse.wh_output_stock_loc_id
        location_obj.write(cr, uid, [wh_output_stock_loc.id], {'warehouse_id': warehouse.id})
        wh_pack_stock_loc = warehouse.wh_pack_stock_loc_id
        location_obj.write(cr, uid, [wh_pack_stock_loc.id], {'warehouse_id': warehouse.id})

        #create in, out, internal picking types for warehouse
        input_loc = wh_input_stock_loc
        if warehouse.reception_steps == 'one_step':
            input_loc = wh_stock_loc
        output_loc = wh_output_stock_loc
        if warehouse.delivery_steps == 'ship_only':
            output_loc = wh_stock_loc

        #choose the next available color for the picking types of this warehouse
        color = 0
        available_colors = [0, 3, 4, 5, 6, 7, 8, 1, 2]  # put white color first
        all_used_colors = self.pool.get('stock.picking.type').search_read(cr, uid, [('warehouse_id', '!=', False), ('color', '!=', False)], ['color'], order='color')
        #don't use sets to preserve the list order
        for x in all_used_colors:
            if x['color'] in available_colors:
                available_colors.remove(x['color'])
        if available_colors:
            color = available_colors[0]

        #order the picking types with a sequence allowing to have the following suit for each warehouse: reception, internal, pick, pack, ship. 
        max_sequence = self.pool.get('stock.picking.type').search_read(cr, uid, [], ['sequence'], order='sequence desc')
        max_sequence = max_sequence and max_sequence[0]['sequence'] or 0
        internal_active_false = (warehouse.reception_steps == 'one_step') and (warehouse.delivery_steps == 'ship_only')
        internal_active_false = internal_active_false and not self.user_has_groups(cr, uid, 'stock.group_locations')
        
        #THANH: get customer and supplier location id
        loc_cus_ids = location_obj.search(cr, uid, [('usage', '=', 'customer')])
        loc_sup_ids = location_obj.search(cr, uid, [('usage', '=', 'supplier')])
        #THANH: get customer and supplier location id
        
        in_type_id = False
        if not warehouse.in_type_id:
            in_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Receipts'),
                'warehouse_id': warehouse.id,
                'code': 'incoming',
                'use_create_lots': True,
                'use_existing_lots': False,
                'sequence_id': in_seq_id,
                'default_location_src_id': len(loc_sup_ids) and loc_sup_ids[0] or False,
                'default_location_dest_id': input_loc.id,
                'sequence': max_sequence + 1,
                'color': color}, context=context)
        else:
            in_type_id = warehouse.in_type_id.id
        if not warehouse.out_type_id:
            out_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Delivery Orders'),
                'warehouse_id': warehouse.id,
                'code': 'outgoing',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': out_seq_id,
                'return_picking_type_id': in_type_id,
                'default_location_src_id': output_loc.id,
                'default_location_dest_id': len(loc_cus_ids) and loc_cus_ids[0] or False,
                'sequence': max_sequence + 4,
                'color': color}, context=context)
            picking_type_obj.write(cr, uid, [in_type_id], {'return_picking_type_id': out_type_id}, context=context)
        if not warehouse.int_type_id:
            int_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Internal Transfers'),
                'warehouse_id': warehouse.id,
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': int_seq_id,
                'default_location_src_id': wh_stock_loc.id,
                'default_location_dest_id': wh_stock_loc.id,
                'active': not internal_active_false,
                'sequence': max_sequence + 2,
                'color': color}, context=context)
        if not warehouse.pack_type_id:
            pack_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Pack'),
                'warehouse_id': warehouse.id,
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': pack_seq_id,
                'default_location_src_id': wh_pack_stock_loc.id,
                'default_location_dest_id': output_loc.id,
                'active': warehouse.delivery_steps == 'pick_pack_ship',
                'sequence': max_sequence + 3,
                'color': color}, context=context)
        if not warehouse.pick_type_id:
            pick_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Pick'),
                'warehouse_id': warehouse.id,
                'code': 'internal',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': pick_seq_id,
                'default_location_src_id': wh_stock_loc.id,
                'default_location_dest_id': output_loc.id if warehouse.delivery_steps == 'pick_ship' else wh_pack_stock_loc.id,
                'active': warehouse.delivery_steps != 'ship_only',
                'sequence': max_sequence + 2,
                'color': color}, context=context)
        if not warehouse.production_in_type_id:
            production_in_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Finhed Goods Receipt'),
                'warehouse_id': warehouse.id,
                'code': 'production_in',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': production_in_seq_id,
                'default_location_src_id': wh_production_loc_id,
                'default_location_dest_id': wh_finished_good_loc_id or wh_stock_loc.id,
                'active': not internal_active_false,
                'sequence': max_sequence + 6,
                'color': color}, context=context)
        if not warehouse.production_out_type_id:
            production_out_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Material Issue'),
                'warehouse_id': warehouse.id,
                'code': 'production_out',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': production_out_seq_id,
                'default_location_src_id': wh_raw_material_loc_id or wh_stock_loc.id,
                'default_location_dest_id': wh_production_loc_id,
                'active': not internal_active_false,
                'sequence': max_sequence + 5,
                'color': color}, context=context)
        if not warehouse.return_customer_type_id:
            return_customer_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Customer Returns'),
                'warehouse_id': warehouse.id,
                'code': 'return_customer',
                'use_create_lots': True,
                'use_existing_lots': False,
                'sequence_id': return_customer_seq_id,
                'default_location_src_id': len(loc_cus_ids) and loc_cus_ids[0] or False,
                'default_location_dest_id': wh_stock_loc.id,
                'sequence': max_sequence + 7,
                'color': color}, context=context)
        if not warehouse.return_supplier_type_id:
            return_supplier_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Supplier Returns'),
                'warehouse_id': warehouse.id,
                'code': 'return_supplier',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': return_supplier_seq_id,
                'default_location_src_id': wh_stock_loc.id,
                'default_location_dest_id': len(loc_sup_ids) and loc_sup_ids[0] or False,
                'sequence': max_sequence + 8,
                'color': color}, context=context)

        #write picking types on WH
        vals = {
            'wh_raw_material_loc_id': wh_raw_material_loc_id,
            'wh_finished_good_loc_id': wh_finished_good_loc_id,
            'wh_production_loc_id': wh_production_loc_id,
            
            'in_type_id': warehouse.in_type_id.id or in_type_id,
            'out_type_id': warehouse.out_type_id.id or out_type_id,
            'pack_type_id': warehouse.pack_type_id.id or pack_type_id,
            'pick_type_id':  warehouse.pick_type_id.id or pick_type_id,
            'int_type_id': warehouse.int_type_id.id or int_type_id,
            
            'production_in_type_id': warehouse.production_in_type_id.id or production_in_type_id,
            'production_out_type_id': warehouse.production_out_type_id.id or production_out_type_id,
            'return_customer_type_id': warehouse.return_customer_type_id.id or return_customer_type_id,
            'return_supplier_type_id': warehouse.return_supplier_type_id.id or return_supplier_type_id,
            }
        super(stock_warehouse, self).write(cr, uid, warehouse.id, vals=vals, context=context)
    
    def init(self, cr):
        sql = '''SELECT id FROM stock_warehouse WHERE return_customer_type_id IS NULL OR return_supplier_type_id IS NULL'''
        cr.execute(sql)
        for warehouse_id in cr.fetchall():
            warehouse = self.browse(cr, SUPERUSER_ID, warehouse_id)
            self.create_sequences_and_picking_types(cr, SUPERUSER_ID, warehouse)
        return True
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
