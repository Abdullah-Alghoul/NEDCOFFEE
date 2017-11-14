# -*- coding: utf-8 -*-

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

from lxml import etree
import base64
import xlrd
    
class stock_location(osv.osv):
    _inherit="stock.location"
    _columns = { 
            'mrp_outsource_location': fields.boolean(string="Is a Outsource Location?")
            }
stock_location()

class stock_picking_type(osv.osv):
    _inherit="stock.picking.type"
    _columns = { 
                'code': fields.selection([('incoming', 'Suppliers'), 
                      ('outgoing', 'Customers'),    ('internal', 'Internal'),
                      ('return_customer', 'Return Customers'),  ('return_supplier', 'Return Supplier'), 
                      ('production_out', 'Production Out'), ('production_in', 'Production In'),
                      ('outsource_issue', 'Outsource Issue'),  ('outsource_receipt', 'Outsource Receipt'),
                      ('phys_adj', 'Physical Adjustment')], 'Type of Operation', required=True),
                }
    
stock_picking_type()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = { 
                'outsouce_id': fields.many2one('mrp.outsource.request', 'Outsouce Request', readonly=False, states={'draft': [('readonly', True)]}),
                'picking_type_code': fields.related('picking_type_id', 'code', type='selection', selection=[
                      ('incoming', 'Suppliers'), ('outgoing', 'Customers'), 
                      ('internal', 'Internal'), ('return_customer', 'Return Customers'), 
                      ('return_supplier', 'Return Suppliers'),  ('internal', 'Internal'),
                      ('production_out', 'Production Out'), ('production_in', 'Production In'),
                      ('outsource_issue', 'Outsource Issue'),('outsource_receipt', 'Outsource Receipt'),
                      ('phys_adj', 'Physical Adjustment')], string="picking_type_code"),
                 }
    
    # Update State MRPOutsourceRequest 
    def do_transfer(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = super(stock_picking, self).do_transfer(cr, uid, ids, context=context)
        
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.picking_type_code == "outsource_issue" and picking.outsouce_id:
                self.pool.get('mrp.outsource.request').button_done(cr, uid, picking.outsouce_id.id)
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
         
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('production_in','production_out'))], 'required': [('picking_type_code','in',('outgoing','incoming','outsource_issue','outsource_receipt','return_supplier','return_customer'))]}")
            for node in doc.xpath("//label[@for='production_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out','outsource_issue','outsource_receipt'))]}")
            for node in doc.xpath("//field[@name='production_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out','outsource_issue','outsource_receipt'))], 'required': [('picking_type_code','in',('production_in','production_out','outsource_issue','outsource_receipt'))]}")
            for node in doc.xpath("//div[@name='production']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out','outsource_issue','outsource_receipt'))]}")
            for node in doc.xpath("//field[@name='operation_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','!=','production_in')],'required': [('picking_type_code','=','production_in')]}")
                node.set('domain', "[('production_id','=',production_id),('state','!=','cancel')]")
            for node in doc.xpath("//field[@name='origin']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('production_in','production_out','outsource_issue'))]}")
            for node in doc.xpath("//field[@name='location_dest_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('outgoing','outsource_issue'))]}")
            for node in doc.xpath("//field[@name='location_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('incoming','outsource_receipt'))]}")
            for node in doc.xpath("//button[@name='button_loading']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('outsource_issue','outsource_receipt'))]}")
             
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
stock_picking()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = { 
                'type': fields.related('picking_type_id', 'code', type='selection',store =True, selection= [('incoming', 'Suppliers'), 
                      ('outgoing', 'Customers'),  ('internal', 'Internal'),
                      ('return_customer', 'Return Customers'),('return_supplier', 'Return Suppliers'), 
                      ('production_out', 'Production Out'),('production_in', 'Production In'),
                      ('outsource_issue', 'Outsource Issue'), ('outsource_receipt', 'Outsource Receipt'),
                      ('phys_adj', 'Physical Adjustment')], string="picking_type_code"),
                 }
stock_move()
    
class stock_warehouse(osv.osv):
    _inherit = 'stock.warehouse'
    _columns={
              'wh_outsource_loc_id': fields.many2one('stock.location', 'Outsource Stock'),
              'outsource_receipt_type_id': fields.many2one('stock.picking.type', 'Outsource Receipt'),
              'outsource_issue_type_id': fields.many2one('stock.picking.type', 'Outsource Issue'),
              }

    #KIM: Auto define picking type outsource when set up a new Warehouse
    def create_sequences_and_picking_types(self, cr, uid, warehouse, context=None):
        seq_obj = self.pool.get('ir.sequence')
        picking_type_obj = self.pool.get('stock.picking.type')
        location_obj = self.pool.get('stock.location')
        #create new location
        wh_loc_id = warehouse.lot_stock_id.location_id or False
        location_obj.write(cr, uid, wh_loc_id.id, {'warehouse_id': warehouse.id})
        
        #THANH: get customer and supplier location id
        loc_cus_ids = location_obj.search(cr, uid, [('usage', '=', 'customer')])
        loc_sup_ids = location_obj.search(cr, uid, [('usage', '=', 'supplier')])
        #THANH: get customer and supplier location id
        
        if not warehouse.wh_finished_good_loc_id:
            wh_finished_good_loc_id = location_obj.create(cr, uid, {'name': warehouse.code + _(' - Finished Goods Stock'),'usage': 'internal', 'location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)
        else:
            wh_finished_good_loc_id = warehouse.wh_finished_good_loc_id.id
        if not warehouse.wh_raw_material_loc_id:
            wh_raw_material_loc_id = location_obj.create(cr, uid, {'name': warehouse.code + _(' - Raw Material Stock'),'usage': 'internal','location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)
        else:
            wh_raw_material_loc_id = warehouse.wh_raw_material_loc_id.id
        if not warehouse.wh_production_loc_id:
            wh_production_loc_id = location_obj.create(cr, uid, {'name': warehouse.code + _(' - Production Stock'),'usage': 'internal','location_id': wh_loc_id.id,
                    'active': True,'warehouse_id': warehouse.id,'company_id': warehouse.company_id.id}, context=context)    
        else:
            wh_production_loc_id = warehouse.wh_production_loc_id.id
        
        if not warehouse.wh_outsource_loc_id:
            location = location_obj.browse(cr, uid, loc_sup_ids[0])
            wh_outsource_loc_ids = location_obj.search(cr, uid, [('location_id','=',location.location_id.id),('mrp_outsource_location','=',True)])
            if not wh_outsource_loc_ids:
                wh_outsource_loc_id = location_obj.create(cr, uid, {'name': _('Outsouce Stock'),'usage': 'supplier','location_id': location.location_id.id,
                        'active': True,'mrp_outsource_location': True}, context=context)  
            else:
                wh_outsource_loc_id = wh_outsource_loc_ids and wh_outsource_loc_ids[0]
        else:
            wh_outsource_loc_id = warehouse.wh_outsource_loc_id.id
            
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
        # Outsouce picking type
        if not warehouse.outsource_receipt_type_id:
            outsource_receipt_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence outsource receipt'), 'prefix': warehouse.code + '/OUTSOURCE-IN/', 'padding': 5}, context=context)
        if not warehouse.outsource_issue_type_id:
            outsource_issue_seq_id = seq_obj.create(cr, SUPERUSER_ID, {'name': warehouse.name + _(' Sequence outsource issue'), 'prefix': warehouse.code + '/OUTSOURCE-OUT/', 'padding': 5}, context=context)
        
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
        if not warehouse.outsource_issue_type_id:
            outsource_issue_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Outsource Issue'),
                'warehouse_id': warehouse.id,
                'code': 'outsource_issue',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': outsource_issue_seq_id,
                'default_location_src_id': wh_raw_material_loc_id or wh_stock_loc.id,
                'default_location_dest_id': wh_outsource_loc_id,
                'sequence': max_sequence + 9,
                'color': color}, context=context)
        if not warehouse.outsource_receipt_type_id:
            outsource_receipt_type_id = picking_type_obj.create(cr, uid, vals={
                'name': _(' - Outsource Receipt'),
                'warehouse_id': warehouse.id,
                'code': 'outsource_receipt',
                'use_create_lots': False,
                'use_existing_lots': True,
                'sequence_id': outsource_receipt_seq_id,
                'default_location_src_id': wh_outsource_loc_id,
                'default_location_dest_id': wh_finished_good_loc_id or wh_stock_loc.id,
                'sequence': max_sequence + 10,
                'color': color}, context=context)

        #write picking types on WH
        vals = {
            'wh_raw_material_loc_id': wh_raw_material_loc_id,
            'wh_finished_good_loc_id': wh_finished_good_loc_id,
            'wh_production_loc_id': wh_production_loc_id,
            'wh_outsource_loc_id': wh_outsource_loc_id,
            
            'in_type_id': warehouse.in_type_id.id or in_type_id,
            'out_type_id': warehouse.out_type_id.id or out_type_id,
            'pack_type_id': warehouse.pack_type_id.id or pack_type_id,
            'pick_type_id':  warehouse.pick_type_id.id or pick_type_id,
            'int_type_id': warehouse.int_type_id.id or int_type_id,
            
            'production_in_type_id': warehouse.production_in_type_id.id or production_in_type_id,
            'production_out_type_id': warehouse.production_out_type_id.id or production_out_type_id,
            'return_customer_type_id': warehouse.return_customer_type_id.id or return_customer_type_id,
            'return_supplier_type_id': warehouse.return_supplier_type_id.id or return_supplier_type_id,
            'outsource_receipt_type_id': warehouse.outsource_receipt_type_id.id or outsource_receipt_type_id,
            'outsource_issue_type_id': warehouse.outsource_issue_type_id.id or outsource_issue_type_id,
            }
        super(stock_warehouse, self).write(cr, uid, warehouse.id, vals=vals, context=context)
        
stock_warehouse()
