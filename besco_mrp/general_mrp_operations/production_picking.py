# -*- coding: utf-8 -*-
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging

from lxml import etree
import base64
import xlrd

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    _columns = {
        'move_lines': fields.many2many('stock.move', 'mrp_production_move_ids', 'production_id', 'move_id', 'Products to Consume',
            domain=[('state', '=', 'done')]),
        'move_lines2': fields.many2many('stock.move', 'mrp_production_consumed_products_move_ids', 'production_id', 'move_id', 'Consumed Products',
            readonly=True, states={'draft':[('readonly', False)]}),
        'move_loss_ids': fields.many2many('stock.move', 'mrp_production_products_move_loss_ids', 'production_id', 'move_id', 'Consumed Lost',
            readonly=True, states={'draft':[('readonly', False)]}),
        'move_created_ids': fields.one2many('stock.move', 'production_id', 'Products to Produce',
            domain=[('state', 'not in', ('done', 'cancel')), ('type', '=', 'production_in')], readonly=True),
        'move_created_ids2': fields.one2many('stock.move', 'production_id', 'Produced Products',
            domain=[('state', '=', 'done'), ('type', '=', 'production_in'),('location_dest_id.usage', '=', 'internal')], readonly=True),
    }

# Thanh: New Object to batch the Material Receipt from many Production Order
class production_picking_batch(osv.osv):
    _name = 'production.picking.batch'
    
    _columns = {
        'name': fields.char('Batch number', size=50, required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'date': fields.datetime('Date', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'date_done': fields.datetime('Date done', required=False, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}, select=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}, select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}, select=True),
        'receipt_user': fields.char('Receipt User', size=200, required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'material_picking_list':fields.one2many('stock.picking', 'production_picking_batch_id', 'Material Receipts',
                                                states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('done', 'Done'),
            ], 'Status', readonly=True, select=True),
        
        'note': fields.text('Notes'),
        'write_date':  fields.datetime('Last Modification', readonly=True),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Updated by', readonly=True),
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
    }
    
    def _default_warehouse(self, cr, uid, context=None):
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
        return warehouse_ids and warehouse_ids[0] 
    
    _defaults = {
        'name': '/',
        'date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'state': 'draft',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'stock.picking', context=c),
        'warehouse_id': _default_warehouse
    }
    
    def onchange_picking_type(self, cr, uid, ids, picking_type_id, context=None):
        value = {}
        domain = {}
        if not picking_type_id:
            value.update({'location_id':False,
                           'location_dest_id':False})
            domain.update({'location_id':[('id', '=', False)],
                           'location_dest_id':[('id', '=', False)]})
        else:
            picking_type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id)
            
            location_id = picking_type.default_location_src_id.id or False
            location_dest_id = picking_type.default_location_dest_id.id or False
            
            domain.update({'location_id':[('id', '=', location_id)],
                           'location_dest_id':[('id', '=', location_dest_id)]})
            
            if location_dest_id and location_dest_id != location_id:
                location_dest_id = location_dest_id
            value.update({'location_id':location_id,
                          'location_dest_id': location_dest_id})
        return {'value': value, 'domain':domain}
    
    def button_confirm(self, cr, uid, ids, context=None):
        picking_pool = self.pool.get('stock.picking')
        for batch in self.browse(cr, uid, ids):
            if not batch.material_picking_list:
                error = "Thông tin phiếu kho chưa có, vui lòng tạo các phiếu kho." 
                raise osv.except_osv(unicode('Lỗi Thông Tin!', 'utf8'), unicode(error, 'utf8'))
            date_done = time.strftime('%Y-%m-%d %H:%M:%S')
            for picking in batch.material_picking_list:
                picking_pool.write(cr, uid, picking.id, {'date_done': date_done})
                picking_pool.do_transfer(cr, uid, picking.id)
                if picking.production_id and picking.picking_type_id.code == 'production_out' and picking.location_id.usage == 'internal':
                    cr.execute(''' DELETE FROM mrp_production_move_ids WHERE production_id = %s 
                            And move_id in (select stm.id FROM stock_move stm join stock_picking sp on stm.picking_id=sp.id WHERE sp.id=%s);
                    ''' % (picking.production_id.id, picking.id))
                    cr.execute('''INSERT INTO mrp_production_move_ids
                    SELECT sp.production_id, stm.id FROM stock_move stm join stock_picking sp on stm.picking_id=sp.id WHERE sp.id=%s
                    ''' % (picking.id))
            self.write(cr, uid, ids[0], {'state': 'done', 'date_done': date_done})
        return True
    
    def button_cancel(self, cr, uid, ids, context=None):
        picking_pool = self.pool.get('stock.picking')
        for batch in self.browse(cr, uid, ids):
            for picking in batch.material_picking_list:
                picking_pool.action_cancel(cr, uid, picking.id)
            self.write(cr, uid, ids[0], {'state': 'cancel'})
        return True
    
    def reset_to_draft(self, cr, uid, ids, context=None):
        picking_pool = self.pool.get('stock.picking')
        for batch in self.browse(cr, uid, ids):
            for picking in batch.material_picking_list:
                picking_pool.action_revert_done(cr, uid, [picking])
            self.write(cr, uid, ids[0], {'state': 'draft'})
        return True
production_picking_batch()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
        'production_picking_batch_id':fields.many2one('production.picking.batch', 'Production Picking Batch', ondelete='cascade'),
            }
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_picking, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
         
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            # Kim: Edit xml 
            for node in doc.xpath("//field[@name='partner_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('production_in','production_out'))]}")
            for node in doc.xpath("//label[@for='production_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out'))]}")
            for node in doc.xpath("//field[@name='production_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out'))], 'required': [('picking_type_code','in',('production_in','production_out'))]}")
            for node in doc.xpath("//div[@name='production']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_in','production_out'))]}")
            for node in doc.xpath("//field[@name='operation_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','!=','production_in')]}")
                node.set('domain', "[('production_id','=',production_id),('state','!=','cancel')]")
            for node in doc.xpath("//field[@name='origin']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('production_in','production_out'))]}")
            for node in doc.xpath("//field[@name='group_id']"):
                node.set('attrs', "{'invisible': [('picking_type_code','in',('production_in','production_out'))]}")
             
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
stock_picking()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
