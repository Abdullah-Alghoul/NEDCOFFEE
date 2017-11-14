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

class stock_inventory(osv.osv):
    _inherit = "stock.inventory"
    
    
    def read_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        product_obj = self.pool.get('product.product')
        inven_line_obj = self.pool.get('stock.inventory.line')
        
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            falg = False
            for row in range(sh.nrows):
                if not falg:
                    falg = True
                    continue
                product_qty = sh.cell(row,3).value or 0.0
                total_cost = sh.cell(row,4).value or 0.0
                if not product_qty and product_qty ==0:
                    continue
                
                try:
                    freeze_cost = float(total_cost)/ float(product_qty)
                except Exception, e:
                    print sh.cell(row,0).value
                
                default_code = sh.cell(row,0).value
#                 if isinstance(default_code, float):
#                     default_code = int(default_code)
#                     default_code = str(default_code)
                
                    
                product_id = product_obj.search(cr, uid, [('default_code','=', default_code)])
                if product_id:
                    product_id = product_id[0] or False
                else:
                    print 'tim khong ra' +sh.cell(row,0).value
                    continue
                    
                product = product_obj.read(cr, uid, product_id, ['uom_id', 'standard_price'])
                product_uom = product['uom_id'][0]
                
                vals = {
                      'inventory_id':ids[0],
                      'product_id':product_id,
                      'product_uom_id': product_uom or False,
                      'product_qty': product_qty,
                      'location_id': 73,
                      'freeze_cost':freeze_cost,
                }
                 
                #THANH: Check exist inventory for this product
                try:
                    inven_line_obj.create(cr, uid, vals)
                except Exception, e:
                    raise osv.except_osv(_('Warning!'), str(e))
                        
        return True
    
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    
    _columns = {
        'picking_type_code': fields.related('picking_type_id', 'code', type='selection',store =True, 
                    selection= [('incoming', 'Suppliers'), 
                                  ('outgoing', 'Customers'), 
                                  ('internal', 'Internal'),
                                  ('return_customer', 'Return Customers'), 
                                  ('return_supplier', 'Return Suppliers'), 
                                  ('production_out', 'Production Out'),
                                  ('adjust_stock','Adjust Stock'),
                                  ('transfer_in', 'Transfer in'),
                                  ('transfer_out', 'Transfer Out'),
                                  ('production_in', 'Production In'),
                                  ('phys_adj', 'Physical Adjustment')], string="picking_type_code"),
        'product_id': fields.related('move_lines', 'product_id', type='many2one', relation='product.product', string='Product',store = True),
        'warehouse_id': fields.related('picking_type_id','warehouse_id',type="many2one",relation= 'stock.warehouse',string="Warehouse",store=True),
    }
    
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
            
            if context.has_key('picking_grn_Goods'):
                picking_type_id = picking_type.search([('code','=','incoming'),('active','=',True)], limit=1)
                domain.update({'domain': {'picking_type_id': [('id','=',picking_type_id.id)]}})
            
            if context.has_key('picking_grp_Goods'): 
                picking_type_id = picking_type.search([('code','=','production_in'),('active','=',True)], limit=1)
                domain.update({'domain': {'picking_type_id': [('id','=',picking_type_id.id)]}})
                
                
            domain.update({'location_id':[('id','=',location_id)],
                           'location_dest_id':[('id','=',location_dest_id)]})
            
            if location_dest_id and location_dest_id != location_id:
                location_dest_id = location_dest_id
            value.update({'location_id':location_id,
                          'location_dest_id': location_dest_id,
                          'picking_type_code': picking_type.code})
        return {'value': value,'domain':domain}
    
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_picking,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
           
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='vehicle_no']"):
                node.set('attrs', "{'invisible': [('picking_type_code','not in',('incoming','return_supplier'))]}")
                #node.set('attrs', "{'required': [('picking_type_code','in',('incoming','return_supplier'))]}")
             
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res