# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from collections import OrderedDict

import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.exceptions import UserError, AccessError

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    _columns = {
          'sale_line_id': fields.many2one('sale.order.line', 'Sale line'),
          }

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
              'mrp_request_id': fields.many2one('mrp.request.line', 'Production Request'),
              'production_ids': fields.many2many('mrp.production', 'mo_procurement_rel', 'procurement_id', 'production_id', 'Production Orders', readonly=True),
              }
    
    def make_mo(self, cr, uid, ids, context=None):
        res = {}
        production_obj = self.pool.get('mrp.production')
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if procurement.sale_line_id and procurement.sale_line_id.mrp_request_id:
                if self.check_bom_exists(cr, uid, [procurement.id], context=context):
                    # Kim: create the MO
                    res_id = procurement.move_dest_id and procurement.move_dest_id.id or False
                    newdate = self._get_date_planned(cr, uid, procurement, context=context)
                    bom_obj = self.pool.get('mrp.bom')
                    if procurement.bom_id:
                        bom_id = procurement.bom_id.id
                        routing_id = procurement.bom_id.routing_id.id
                    else:
                        properties = [x.id for x in procurement.property_ids]
                        bom_id = bom_obj._bom_find(cr, uid, product_id=procurement.product_id.id,
                                                   properties=properties, context=dict(context, company_id=procurement.company_id.id))
                        bom = bom_obj.browse(cr, uid, bom_id, context=context)
                        routing_id = bom.routing_id.id
                        
                    if context and context.get('mo_qty', False):
                        mo_qty = context['mo_qty']
                    else:
                        mo_qty = procurement.product_qty or 0
                        
                    mrp_request_id = context and context.get('mrp_request_id', False)
                    
                    vals = {'origin': procurement.origin, 'product_id': procurement.product_id.id, 'product_qty': mo_qty,'move_prod_id': res_id,
                        'product_uom': procurement.product_uom.id,'warehouse_id': procurement.rule_id.warehouse_id.id or procurement.warehouse_id.id,
                        'location_src_id': procurement.warehouse_id.wh_raw_material_loc_id.id or procurement.location_id.id,'routing_id': routing_id,
                        'location_dest_id': procurement.warehouse_id.lot_stock_id.id or procurement.location_id.id,'company_id': procurement.company_id.id, 
                        'bom_id': bom_id, 'sale_line_id': procurement.sale_line_id.id,'date_planned': time.strftime('%Y-%m-%d %H:%M:%S'),'state': 'draft'}
                    
                    produce_id = production_obj.create(cr, SUPERUSER_ID, vals, context=dict(context, force_company=procurement.company_id.id))
                    
                    # Kim: Update production_id on mrp_request_line
                    cr.execute('''INSERT INTO mo_procurement_rel (procurement_id, production_id) VALUES (%s, %s)''' % (procurement.id, produce_id))
                    if mrp_request_id:
                        cr.execute('update mrp_request_line set production_id=%s where id=%s', (produce_id, mrp_request_id))
                    
                    res[procurement.id] = produce_id
                    self.write(cr, uid, [procurement.id], {'production_id': produce_id})
                    self.production_order_create_note(cr, uid, procurement, context=context)
                    production_obj.button_load_mrp(cr, uid, [produce_id], context=context)
                    production_obj.action_compute(cr, uid, [produce_id], properties=[x.id for x in procurement.property_ids])
    #                 production_obj.signal_workflow(cr, uid, [produce_id], 'button_confirm')
                else:
                    res[procurement.id] = False
                    self.message_post(cr, uid, [procurement.id], body=_("No BoM exists for this product!"), context=context)
            else:
                res[procurement.id] = False
        return res
procurement_order()

class mrp_request(osv.osv):
    _name = "mrp.request"
    _order = 'create_date DESC'
    _columns = {
            'name': fields.char('Name', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'state': fields.selection([('draft', 'New'), ('confirmed', 'Confirmed'),('cancel', 'Cancelled'), ('done', 'Done')], 'State'),
            'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_qty': fields.float('Product Quantity', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_uom': fields.many2one('product.uom', 'Uom', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'sale_id': fields.many2one('sale.order', 'Sale Order', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'partner_id': fields.related('sale_id', 'partner_id', type="many2one", relation="res.partner", store=True, string="Customer", readonly=True),
            'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'create_date': fields.date('Creation Date', readonly=True),
            'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
            'validator': fields.many2one('res.users', 'Confirmer', readonly=True),
            'date_approved':fields.date('Date Approved', readonly=True),
            'date_done':fields.date('Date Done', readonly=True),
            'request_ids': fields.one2many('mrp.request.line', 'mrp_request_id', 'Production request Line', readonly=True,
                        states={'confirmed': [('readonly', False)], 'draft': [('readonly', False)]}),
                }
    
    _defaults = {
               'name': 'New',
               'state': 'draft',
               'create_uid': lambda self, cr, uid, c: uid,
               'create_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
               }
    
    def onchange_sale_id(self, cr, uid, ids, sale_id, context=None ):
        domain = {}
        product_ids = []
        order_line = self.pool.get('sale.order.line')
        if sale_id:
            sale_line_ids = order_line.search(cr,uid,[('order_id','=',sale_id),('mrp_request_id','=',False)])
            if sale_line_ids:
                for line in order_line.browse(cr, uid, sale_line_ids[0]):
                    product_ids.append(line.product_id.id)
                if product_ids:
                    domain.update({'product_id':[('id','in',product_ids)]})
            else:
                domain.update({'product_id':[('id','=',False)]})
        else:
            domain.update({'product_id':[('id','=',False)]})
        return {'domain':domain}
    
    def onchange_product_id(self, cr, uid, ids, product_id, sale_id,context=None):
        values = domain = {}
        order_line = self.pool.get('sale.order.line')
        if product_id: 
            sale_line_id = order_line.search(cr, uid, [('product_id','=',product_id),('order_id','=',sale_id)]) or False
            if sale_line_id:
                order_line_obj = order_line.browse(cr, uid, sale_line_id[0])
                values = {'sale_line_id': sale_line_id[0],'product_qty': order_line_obj.product_uom_qty or 0.0,'product_uom': order_line_obj.product_uom.id or False}
                domain = {'sale_line_id': [('id','=',sale_line_id[0])],'product_uom':[('id','=',order_line_obj.product_uom.id)]}
            else:
                values = {'sale_line_id': False,'product_qty': 0.0,'product_uom': False}
                domain = {'sale_line_id': [('id','=',False)],'product_uom':[('id','=',False)]}
        else:
            values = {'sale_line_id': False,'product_qty': 0.0,'product_uom': False}
            domain = {'sale_line_id': [('id','=',False)],'product_uom':[('id','=',False)]}
        return {'value': values, 'domain':domain}
                              
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'name': 'New', 'state' : 'state',
            'sale_id' :False,'sale_line_id' : False,
            'partner_id' : False,'request_ids' : [],
            'date_done': False, 'date_approved': False,
            'create_date': time.strftime('%Y-%m-%d %H:%M:%S'),'validator': False,
            'create_uid': uid, 'date_approved': False, 'date_done': False})
        return super(osv.osv, self).copy(cr, uid, id, default, context)
    
    def create(self, cr, uid, vals, context=None):
        if not vals.get('name', False) or vals['name'] == 'New':
            number = self.pool.get('ir.sequence').get(cr, uid, 'mrp.request')
            vals.update({'name':number}) 
        return super(mrp_request, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            if request.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a Production request.\nPlease close or cancel it first.'))
        return super(mrp_request, self).unlink(cr, uid, ids, context=context)
    
    def button_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft', 'date_approved': False, 'validator': False, 'date_done': False})
    
    def button_cancel(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            for line in request.request_ids:
                self.pool.get('mrp.request.line').button_cancel(cr, uid, [line.id])
            self.write(cr, uid, ids, {'state':'cancel', 'date_approved': False, 'validator': False, 'date_done': False})
        return True
    
    def button_confirmed(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'confirmed', 'date_approved': time.strftime('%Y-%m-%d %H:%M:%S'), 'validator': uid})
    
    def button_done(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            if len(request.request_ids) == 0:
                raise UserError(_('You can not done a Production request.\nPlease create Production Order.'))
            
            count_line = len(request.request_ids) or 0
            for line in request.request_ids:
                count = 0
                if line.production_id and line.state in ('draft', 'cancel'):
                    count += 1
                if count_line == count:
                    raise UserError(_('You can not done a Production request.\nPlease create Production Order.'))
                
                if line.production_id and line.production_id.state == 'in_production':
                    raise UserError(_('You can not make a Production Request.\nPlease put the status of implementation for Production Order.'))
        return self.write(cr, uid, ids, {'state':'done', 'date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
    
mrp_request()

class mrp_request_line(osv.osv):
    _name = "mrp.request.line"
    _order = 'create_date DESC'
    _columns = {
            'mrp_request_id': fields.many2one('mrp.request', 'MRP Request', ondelete='cascade',readonly=True, states={'draft': [('readonly', False)]}),
            'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_id': fields.many2one('product.product', 'Product', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'production_norms': fields.float('Production Norms', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_uom': fields.many2one('product.uom', 'Uom', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'product_qty': fields.float('Product Quantity', required=True, readonly=True, states={'draft': [('readonly', False)]}),
            'state': fields.selection([('draft', 'New'),('production', 'Production Order'),('cancel', 'Cancelled'),('done','Done')], 'State',default='New'),
            'create_date': fields.date('Creation Date', readonly=True),
            'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
            'validator': fields.many2one('res.users', 'Confirmer', readonly=True),
            'date_approved':fields.date('Date Approved', readonly=True),
            'production_id': fields.many2one('mrp.production', 'MO No.', readonly=True),
                }
    
    _defaults = {
               'state': 'draft',
               'create_uid': lambda self, cr, uid, c: uid,
               'create_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
               }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(mrp_request_line, self).default_get(cr, uid, fields, context=context)
        mrp_request_id = context.get('default_mrp_request_id', False)

        if not mrp_request_id:
            return res
        
        request_obj = self.pool.get('mrp.request').browse(cr, uid, mrp_request_id)
        sql = '''
            SELECT (pr.product_qty - sum(prl.product_qty)) qty 
            FROM mrp_request pr join mrp_request_line prl on prl.mrp_request_id = pr.id
            WHERE prl.id in (SELECT id FROM mrp_request_line WHERE mrp_request_id = %s AND state = 'production')
            GROUP BY pr.product_qty
        ''' % (request_obj.id)
        cr.execute(sql)
        result = cr.dictfetchall()
        product_qty = result and result[0] and result[0]['qty'] or 0.0
        
        res = {'sale_line_id': request_obj.sale_line_id.id or False,
               'product_uom': request_obj.product_uom.id or False,
               'production_norms': request_obj.product_qty or False,
               'product_qty': product_qty or request_obj.product_qty,
               'product_id': request_obj.product_id.id or False,
               'state': 'draft', 'create_uid': uid, 'create_date': time.strftime('%Y-%m-%d %H:%M:%S')}
        return res 
    
    def button_confirmed(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            if request.mrp_request_id != 'confirmed':
                self.pool.get('mrp.request').button_confirmed(cr, uid, [request.mrp_request_id.id])
        
            if not request.production_id:
                request_obj = self.pool.get('mrp.request').browse(cr, uid, request.mrp_request_id.id)
                if request_obj:
                    if request_obj.sale_id.state == 'sale':
                        context.update({'mo_qty': request.product_qty or 0.0, 'mrp_request_id': request.id})
    
                    procurement_obj = self.pool.get('procurement.order')
                    sql = '''
                        SELECT pro.id
                        FROM sale_order_line sol join procurement_order pro on pro.sale_line_id = sol.id
                            join stock_move sm on sm.procurement_id = pro.id
                        WHERE sol.mrp_request_id = %s
                            AND sm.procure_method = 'make_to_order'
                    ''' % (request_obj.id)
                    cr.execute(sql)
                    res = cr.dictfetchall()
                    if not res:
                        raise osv.except_osv(_('Error!'), _('Check information of produced.'))
                    for line in res:
                        procurement_obj.make_mo(cr, uid, [line['id']], context)
            self.write(cr, uid, ids, {'state':'production', 'date_approved': time.strftime('%Y-%m-%d %H:%M:%S'), 'validator': uid})
        return True
    
    def button_cancel(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            if request.production_id and request.production_id.state not in ('draft', 'cancel'):
                raise osv.except_osv(_('Warning'), _('You can not cancel a Production request Line when Production Order [' + request.production_id.name + '] with running manufacturing orders.'))
            self.pool.get('mrp.production').action_cancel(cr, uid, request.production_id.id)
            result = self.write(cr, uid, ids, {'state':'cancel'})
        return result
    
    def unlink(self, cr, uid, ids, context=None):
        for request in self.browse(cr, uid, ids):
            if request.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a Production Request Line.\nPlease close or cancel it first.'))
        return super(mrp_request_line, self).unlink(cr, uid, ids, context=context)
        
mrp_request_line()