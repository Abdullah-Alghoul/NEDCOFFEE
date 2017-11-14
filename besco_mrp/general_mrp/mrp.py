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

class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    
    def _prepare_mo_vals(self, cr, uid, procurement, context=None):
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
        return {
            'origin': procurement.origin, 'product_id': procurement.product_id.id,
            'product_qty': procurement.product_qty, 'product_uom': procurement.product_uom.id,
            'warehouse_id': procurement.rule_id.warehouse_id.id or procurement.warehouse_id.id,
            'location_src_id': procurement.warehouse_id.wh_raw_material_loc_id.id or procurement.location_id.id,
            'location_dest_id': procurement.warehouse_id.lot_stock_id.id or procurement.location_id.id,
            'bom_id': bom_id, 'routing_id': routing_id, 'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'), 
            'move_prod_id': res_id,'company_id': procurement.company_id.id, 'state': 'draft'}
    
    def make_mo(self, cr, uid, ids, context=None):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        res = {}
        production_obj = self.pool.get('mrp.production')
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if self.check_bom_exists(cr, uid, [procurement.id], context=context):
                # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = self._prepare_mo_vals(cr, uid, procurement, context=context)
                produce_id = production_obj.create(cr, SUPERUSER_ID, vals, context=dict(context, force_company=procurement.company_id.id))
                res[procurement.id] = produce_id
                self.write(cr, uid, [procurement.id], {'production_id': produce_id})
                self.production_order_create_note(cr, uid, procurement, context=context)
                production_obj.action_compute(cr, uid, [produce_id], properties=[x.id for x in procurement.property_ids])
#                 production_obj.signal_workflow(cr, uid, [produce_id], 'button_confirm')
            else:
                res[procurement.id] = False
                self.message_post(cr, uid, [procurement.id], body=_("No BoM exists for this product!"), context=context)
        return res
    
procurement_order()

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    
    def _production_calc(self, cr, uid, ids, prop, unknow_none, context=None):
        result = {}
        for prod in self.browse(cr, uid, ids, context=context):
            result[prod.id] = {
                'cycle_total': 0.0,
                }
            for wc in prod.workcenter_lines:
                result[prod.id]['cycle_total'] += wc.cycle
        return result
     
    _columns = {
          'hour_total': fields.float('Total Hours', readonly=True, states={'draft': [('readonly', False)], 'ready': [('readonly', False)]}),
          'notes': fields.text('Notes', size=256),
          'warehouse_id':fields.many2one('stock.warehouse', 'Warehouse', required=True, readonly=True, states={'draft': [('readonly', False)]}),
          'bom_stage_replace_lines': fields.one2many('mrp.bom.stage.line.replace', 'production_id', 'MRP', readonly=True, states={'draft': [('readonly', False)]}),
          }
    
    def _default_warehouse_id(self, cr, uid, ids, context=None):
        warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
        return warehouse_ids and warehouse_ids[0]
    
    def _default_location_src_id(self, cr, uid, ids, context=None):
        warehouse_pool = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_pool.search(cr, uid, [] , context=context)
        warehouse_obj = warehouse_pool.browse(cr, uid, warehouse_ids[0])
        location_src_id = warehouse_obj.wh_raw_material_loc_id.id or False
        return location_src_id or False
    
    def _default_location_dest_id(self, cr, uid, ids, context=None):
        warehouse_pool = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_pool.search(cr, uid, [] , context=context)
        warehouse_obj = warehouse_pool.browse(cr, uid, warehouse_ids[0])
        location_dest_id = warehouse_obj.wh_finished_good_loc_id.id or False
        return location_dest_id or False
    
    _defaults = {'warehouse_id': _default_warehouse_id,
                 'location_src_id': _default_location_src_id,
                 'location_dest_id': _default_location_dest_id}
    
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        warehouse_pool = self.pool.get('stock.warehouse')
        value = {}
        domain = {}
        if not warehouse_id:
            value.update({'location_src_id':False,
                           'location_dest_id':False})
            domain.update({'location_src_id':[('id', '=', False)],
                           'location_dest_id':[('id', '=', False)]})
        else:
            warehouse_obj = warehouse_pool.browse(cr, uid, warehouse_id)

            location_src_id = warehouse_obj.wh_raw_material_loc_id.id or False
            location_dest_id = warehouse_obj.wh_finished_good_loc_id.id or False
            domain.update({'location_src_id':[('id', '=', location_src_id)],
                       'location_dest_id':[('id', '=', location_dest_id)]})
            
            if location_dest_id and location_dest_id != location_src_id:
                location_dest_id = location_dest_id
            value.update({'location_src_id':location_src_id,
                          'location_dest_id': location_dest_id})
        return {'value': value, 'domain': domain}
    
    # Thanh: Change work-flow when confirm MO
    def action_ready(self, cr, uid, ids, context=None):
        proc_obj = self.pool.get('procurement.order')
        move_obj = self.pool.get('stock.move')
        for production in self.browse(cr, uid, ids, context=context):
            if not len(production.product_lines) or not len(production.workcenter_lines):
                error = "Information on Estimating Materials and Semi-manufactured Norms have not been created."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            for line in production.workcenter_lines:
                if not line.date_planned or not line.date_planned_end: 
                    error = "Time scheduled to begin and expected to end have not yet been created.'"
                    raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            
            warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production.warehouse_id.id)
            if not production.move_created_ids:
                destination_location_id = production.location_dest_id.id
                for line in production.workcenter_lines: 
                    product_id = line.product_id.id
                    product_qty = line.product_qty
                    product_uom = line.product_uom.id
                    source_location_id = line.product_id.property_stock_production.id
                    procs = proc_obj.search(cr, uid, [('production_id', '=', production.id)], context=context)
                    procurement = procs and proc_obj.browse(cr, uid, procs[0], context=context) or False
                    data = {'name': production.name, 'date': production.date_planned,
                        'product_id': product_id, 'product_uom': product_uom, 'picking_type_id': warehouse_obj.production_in_type_id.id,
                        'product_uom_qty': product_qty, 'location_id': source_location_id, 'group_id': procurement and procurement.group_id.id,
                        'location_dest_id': destination_location_id, 'move_dest_id': production.move_prod_id.id,
                        'procurement_id': procurement and procurement.id, 'company_id': production.company_id.id,
                        'production_id': production.id, 'origin': production.name, 'state': 'waiting'}
                    move_id = move_obj.create(cr, uid, data, context=context)
#                 production.write({'move_created_ids': [(6, 0, [move_id])]}, context=context)
                    if production.move_prod_id and production.move_prod_id.location_id.id != production.location_dest_id.id:
                        move_obj.write(cr, uid, [production.move_prod_id.id], {'location_id': production.location_dest_id.id})
            self.write(cr, uid, ids, {'state': 'in_production'})
            
            for operation in production.workcenter_lines:
                if operation.priority == 5:
                    self.pool.get('mrp.production.workcenter.line').action_start_working(cr, uid, [operation.id])
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'name': '/',
            'move_lines' : [],
            'move_lines2' : [],
            'move_created_ids' : [],
            'move_created_ids2' : [],
            'product_lines' : [],
            'move_prod_id' : False})
        return super(osv.osv, self).copy(cr, uid, id, default, context)
    
    def create(self, cr, uid, vals, context=None):
        # Thanh: Get Routing from BOM
        if vals.get('bom_id', False):
            cr.execute('select routing_id from mrp_bom where id=%s' % (vals['bom_id']))
            routing_id = cr.fetchone()
            if routing_id and routing_id[0]:
                vals.update({'routing_id': routing_id[0]})
        return super(mrp_production, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None, update=True, mini=True):
        if vals.get('bom_id', False):
            cr.execute('select routing_id from mrp_bom where id=%s' % (vals['bom_id']))
            routing_id = cr.fetchone()
            if routing_id and routing_id[0]:
                vals.update({'routing_id': routing_id[0]})
        return super(mrp_production, self).write(cr, uid, ids, vals, context=context)
    
    def button_load_mrp(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids):
            sql = '''DELETE FROM mrp_bom_stage_material_line_replace WHERE bom_stage_line_id in (SELECT id FROM mrp_bom_stage_line_replace WHERE production_id = %s);
                DELETE FROM mrp_bom_stage_output_line_replace WHERE bom_stage_line_id in (SELECT id FROM mrp_bom_stage_line_replace WHERE production_id = %s);
                DELETE FROM mrp_bom_stage_line_replace WHERE production_id = %s; 
            ''' % (this.id, this.id, this.id)
            cr.execute(sql)
            if this.bom_id.id:
                bom_obj = self.pool.get('mrp.bom').browse(cr, uid, this.bom_id.id)
                for line in bom_obj.bom_stage_lines:
                    var = { 'production_id': this.id,
                           'seq': line.seq or 0,
                           'name': line.name or False,
                           'production_stage_id': line.production_stage_id.id or False,
                           'workcenter_id': line.workcenter_id.id or False,
                           'cycle_nbr': line.cycle_nbr or 0.0,
                           'hour_nbr': line.hour_nbr or 0.0}
                    new_id = self.pool.get('mrp.bom.stage.line.replace').create(cr, uid, var)
                    if new_id:
                        for i in line.bom_stage_material_line:
                            bom_stage_material_line = {'sequence': i.sequence or 0,
                                    'name': i.name or False,
                                    'product_id': i.product_id.id or False,
                                    'product_qty': i.product_qty or 0,
                                    'product_uom': i.product_uom.id or False,
                                    'bom_stage_line_id': new_id}
                            self.pool.get('mrp.bom.stage.material.line.replace').create(cr, uid, bom_stage_material_line)
                        for j in line.bom_stage_output_line:
                            bom_stage_output_line = { 'bom_stage_line_id': new_id,
                                             'product_id': j.product_id.id or False,
                                             'product_uom': j.product_uom.id or False,
                                             'product_qty': j.product_qty or 0.0  }
                            self.pool.get('mrp.bom.stage.output.line.replace').create(cr, uid, bom_stage_output_line)
        return True
    
    def print_report_production_order(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_production_order'}

class mrp_production_stage(osv.osv):
    _name = 'mrp.production.stage'
    _columns = {
            'sequence':fields.integer('Sequence', required=True),
            'name':fields.char('Name', size=120, required=True),
            'code': fields.char('Code', size=20, required=True),
          }

class mrp_routing(osv.osv):
    _inherit = 'mrp.routing'
    _columns = {
                'name': fields.char('Name', size=64, required=True),
                'code': fields.char('Code', size=8, required=True),
              }
    
    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        default.update({'code': '/'})
        return super(mrp_routing, self).copy(cr, uid, id, default, context=context)
    
    def is_default_uniq(self, cr, uid, ids):
        for i in self.browse(cr, uid, ids):
            if i.code != '/':
                mrp_routing_ids = self.search(cr, uid, [('code', '=', i.code),
                                                    ('active', '=', True), ('id', '<>', i.id)])
                if mrp_routing_ids:
                    return False
        return True
    
    _constraints = [(is_default_uniq, 'Error: Code already exists!!!', [''])]
    
class mrp_bom(osv.osv):
    _inherit = 'mrp.bom'
    _columns = {
          'bom_stage_lines': fields.one2many('mrp.bom.stage.line', 'bom_id', 'MRP'),
          'description': fields.text('Description'),
      }      
    
    def onchange_product_tmpl_id(self, cr, uid, ids, product_tmpl_id, product_qty=0, context=None):
        res = {}
        if product_tmpl_id:
            prod = self.pool.get('product.template').browse(cr, uid, product_tmpl_id, context=context)
            res['value'] = {
                'product_uom': prod.uom_id.id,
            }
        
        return res
    
    def is_uniq(self, cr, uid, ids):
        for bom in self.browse(cr, uid, ids):
            if bom.code:
                mrp_routing_ids = self.search(cr, uid, [('code', '=', bom.code), ('id', '<>', bom.id)])
                if mrp_routing_ids:
                    return False
        return True
    
    _constraints = [(is_uniq, 'Error: Code already exists!!!', ['code'])]   
    
    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        default.update({'code': ''})
        return super(mrp_bom, self).copy(cr, uid, id, default, context=context)
    
    def create_semi_product(self, cr, uid, ids, context=None):
        congdoan_obj = self.pool.get('mrp.production.stage')
        product_pool = self.pool.get('product.product')
        product_categ_obj = self.pool.get('product.category')
        bom_stage_material_obj = self.pool.get('mrp.bom.stage.material.line')
        bom_congdoan_thanhpham_obj = self.pool.get('mrp.bom.stage.output.line')
        
        for bom in self.browse(cr, uid, ids):
            product_id = product_pool.search(cr, uid, [('product_tmpl_id', '=', bom.product_tmpl_id.id)])
            product_uom = bom.product_uom.id
            product_obj = product_pool.browse(cr, uid, product_id[0])
                
            production_stage_ids = []
            routing_id = bom.routing_id.id or False
            roouting_obj = self.pool.get('mrp.routing').browse(cr, uid, routing_id)
            for line in roouting_obj.workcenter_lines:
                production_stage_ids.append(line.production_stage_id.id)
            
            if production_stage_ids != []: 
                semi_products = {}
                sequence = 0
                for congdoan in congdoan_obj.browse(cr, uid, production_stage_ids):
                    semi_products.update({congdoan.id:False})
                    check_semi_product = product_pool.search(cr, uid, [('categ_id.production_stage_id', '=', congdoan.id)])
                    if not len(check_semi_product):
                        sequence += 1
                        if sequence < len(bom.bom_stage_lines):
                            product_categ_ids = product_categ_obj.search(cr, uid, [('production_stage_id', '=', congdoan.id)])
                            if not len(product_categ_ids):
                                raise osv.except_osv(unicode('Error', 'utf8'), unicode('Category of Semi – finished product %s does not exist!', 'utf8')%(congdoan.name))
                            product_categ = product_categ_obj.browse(cr, uid, product_categ_ids[0])
                            semi_proc_name = unicode('BTP') + ' - ' + unicode(congdoan.name)
                            default_code = unicode(product_categ.code) + unicode(congdoan.code)
                            vals = {'name': semi_proc_name, 'default_code': default_code,
                                    'categ_id': product_categ_ids[0], 'uom_id': product_uom,
                                    'uom_po_id': product_uom, 'purchase_ok': False,
                                    'sale_ok': True, 'track_production': True,
                                    'track_incoming': True, 'track_outgoing': True, }
                            new_semi_product_id = product_pool.create(cr, uid, vals)
                            semi_products.update({congdoan.id:new_semi_product_id})
                    else:
                        semi_products.update({congdoan.id:check_semi_product[0]})
                        continue

            dem = 0
            production_stage_id = {} 
            for line in bom.bom_stage_lines:
                dem += 1
                if not len(line.bom_stage_output_line):
                    product_id = semi_products[line.production_stage_id.id]
                    product_uom = product_uom
                    if dem > 1:
                        for i in bom.bom_stage_lines:
                            if i.seq == (dem - 1):
                                production_stage_id = i.production_stage_id.id or False
                                semi_product_id = semi_products[production_stage_id]
                                material_id = bom_stage_material_obj.search(cr, uid, [('product_id', '=', semi_product_id), ('bom_stage_line_id', '=', line.id)])
                                if not material_id:
                                    sql = '''
                                            SELECT count(id) number FROM mrp_bom_stage_material_line WHERE bom_stage_line_id = %s
                                    ''' % (line.id)
                                    cr.execute(sql)
                                    result = cr.dictfetchall()
                                    number = result and result[0] and result[0]['number'] or 0
                                    number = number + 1
                                    bom_stage_material_obj.create(cr, uid, {'sequence': number,
                                                                            'product_id': semi_product_id,
                                                                            'product_uom': product_uom,
                                                                            'product_qty': 1,
                                                                            'bom_stage_line_id': line.id, })
                    if dem == len(bom.bom_stage_lines):
                        product_id = product_obj.id
                        product_uom = bom.product_uom.id
                    bom_congdoan_thanhpham_obj.create(cr, uid, {'product_id': product_id,
                                                                'product_uom': product_uom,
                                                                'product_qty': 1,
                                                                'bom_stage_line_id': line.id, })
                else:
                    for congdoan_thanhpham in line.bom_stage_output_line:
                        if congdoan_thanhpham.product_id.categ_id.production_stage_id != line.production_stage_id:
                            product_id = congdoan_thanhpham.product_id.id or False
                            bom_stage_material_id = bom_stage_material_obj.search(cr, uid, [('product_id', '=', product_id), ('bom_stage_line_id', '=', line.id)])
                            if bom_stage_material_id and bom_stage_material_id[0]:
                                bom_stage_material_obj.unlink(cr, uid, [bom_stage_material_id[0]])
                            bom_congdoan_thanhpham_obj.unlink(cr, uid, [congdoan_thanhpham.id])
                    
                    line.refresh()
                    if not len(line.bom_stage_output_line):
                        product_id = semi_products[line.production_stage_id.id]
                        product_uom = product_uom
                        if dem > 1:
                            for i in bom.bom_stage_lines:
                                if i.seq == (dem - 1):
                                    production_stage_id = i.production_stage_id.id or False
                                    semi_product_id = semi_products[production_stage_id]
                                    material_id = bom_stage_material_obj.search(cr, uid, [('product_id', '=', semi_product_id), ('bom_stage_line_id', '=', line.id)])
                                    if not material_id:
                                        sql = '''
                                            SELECT count(id) number FROM mrp_bom_stage_material_line WHERE bom_stage_line_id = %s
                                        ''' % (line.id)
                                        cr.execute(sql)
                                        result = cr.dictfetchall()
                                        number = result and result[0] and result[0]['number'] or 0
                                        number = number + 1
                                        bom_stage_material_obj.create(cr, uid, {'sequence': number,
                                                                                'product_id': semi_product_id,
                                                                                'product_uom': product_uom,
                                                                                'product_qty': 1,
                                                                                'bom_stage_line_id': line.id, })
                        if dem == len(bom.bom_stage_lines):
                            product_id = product_obj.id
                            product_uom = bom.product_uom.id
                        bom_congdoan_thanhpham_obj.create(cr, uid, {'product_id': product_id,
                                                                    'product_uom': product_uom,
                                                                    'product_qty': 1,
                                                                    'bom_stage_line_id': line.id, })
        return True
    
    def onchange_routing(self, cr, uid, ids, routing_id, context=None):
        routing_ids = []
        if routing_id:
            routing_obj = self.pool.get('mrp.routing').browse(cr, uid, routing_id)
            sequence = 0
            for line in routing_obj.workcenter_lines:
                sequence += 1
                var = {'workcenter_id':line.workcenter_id and line.workcenter_id.id or False,
                      'seq':sequence,
                      'production_stage_id':line.production_stage_id.id or False,
                      'cycle_nbr': line.cycle_nbr,
                      'hour_nbr': line.hour_nbr,
                      'name': line.name}
                routing_ids.append(var)
        return {'value': {'bom_stage_lines': routing_ids}}
        
mrp_bom()

class mrp_bom_stage_line(osv.osv):
    _name = 'mrp.bom.stage.line'
    _columns = {
               'bom_id':fields.many2one('mrp.bom', 'BOM', ondelete='cascade'),
               'seq':fields.integer('Sequence'),
               'name': fields.char('Name', size=64, required=True),
               'production_stage_id':fields.many2one('mrp.production.stage', 'Production Stage', required=True),
               'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True),
               'cycle_nbr': fields.float('Number of Cycles', required=True),
               'hour_nbr': fields.float('Number of Hours', required=True),
        
               'bom_stage_material_line': fields.one2many('mrp.bom.stage.material.line', 'bom_stage_line_id', 'Materials'),
               'bom_stage_output_line':fields.one2many('mrp.bom.stage.output.line', 'bom_stage_line_id', 'Semi or Finished Goods'),
               }
    _defaults = {
        'cycle_nbr': lambda *a: 1.0,
        'hour_nbr': lambda *a: 0.0,
    }
    
mrp_bom_stage_line()

class mrp_bom_stage_material_line(osv.osv):
    _name = 'mrp.bom.stage.material.line'
    _order = 'sequence ASC'
    
    def _get_sequence(self, cr, uid, ids, field_names, arg=None, context=None):
        res = {}
        if not ids: 
            return res
        seq = 1
        for line in self.browse(cr, uid, ids):
            res[line.id] = seq
            seq += 1
        return res
    
    _columns = {
                'sequence': fields.function(_get_sequence, string='Sequence', type='integer'),
                'name': fields.char('name', size=64, required=False),
                'product_id': fields.many2one('product.product', 'Product', required=True),
                'product_qty': fields.float('Qty', required=True),
                'product_uom': fields.many2one('product.uom', 'UoM', required=True),
                'bom_stage_line_id': fields.many2one('mrp.bom.stage.line', 'BOM Stage', required=True, ondelete='cascade'),
                'type':fields.selection([('prime', 'Prime Material'),
                     ('other', 'Other')], 'Type'),
               }
    
    _defaults = {
        'sequence': 1,
        'type': 'prime'
    }
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        res = {}
        if not product_id:
            return res
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
        res = {'product_uom': product_obj.uom_id.id or False}
        return {'value': res}
    
mrp_bom_stage_material_line()

class mrp_bom_stage_output_line(osv.osv):
    _name = 'mrp.bom.stage.output.line'
    _order = 'sequence ASC'
    
    def _get_sequence(self, cr, uid, ids, field_names, arg=None, context=None):
        res = {}
        if not ids: 
            return res
        seq = 1
        for line in self.browse(cr, uid, ids):
            res[line.id] = seq
            seq += 1
        return res
    
    _columns = {
               'sequence': fields.function(_get_sequence, string='Sequence', type='integer'),
               'product_id': fields.many2one('product.product', 'Product', required=True),
               'product_uom': fields.many2one('product.uom', 'UoM', required=True),
               'product_qty': fields.float('Qty'),
               'bom_stage_line_id': fields.many2one('mrp.bom.stage.line', 'BOM Stage', required=True, ondelete='cascade'),
               }
    
    _defaults = {'product_qty': 1 }
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        res = {}
        if not product_id:
            return res
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
        res = {'product_uom': product_obj.uom_id.id or False}
        return {'value': res}
    
mrp_bom_stage_output_line()

class mrp_bom_stage_line_replace(osv.osv):
    _name = "mrp.bom.stage.line.replace"
    _columns = {
                'production_id': fields.many2one('mrp.production', 'Production', required=True, readonly=True, ondelete='cascade'),
                'seq':fields.integer('Sequence', readonly=True),
                'name': fields.char('Name', size=64, required=True, readonly=True),
                'production_stage_id':fields.many2one('mrp.production.stage', 'Production Stage', required=True, readonly=True),
                'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True, readonly=True),
                'cycle_nbr': fields.float('Number of Cycles', required=True, readonly=True),
                'hour_nbr': fields.float('Number of Hours', required=True, readonly=True),
                'bom_stage_material_line': fields.one2many('mrp.bom.stage.material.line.replace', 'bom_stage_line_id', 'Materials'),
                'bom_stage_output_line':fields.one2many('mrp.bom.stage.output.line.replace', 'bom_stage_line_id', 'Semi or Finished Goods', readonly=True),
              }
mrp_bom_stage_line_replace()

class mrp_bom_stage_material_line_replace(osv.osv):
    _name = 'mrp.bom.stage.material.line.replace'
    _order = 'sequence'
    _columns = {
               'sequence': fields.integer('Sequence', required=False),
               'name': fields.char('name', size=64, required=False,),
               'product_id': fields.many2one('product.product', 'Product', required=True),
               'product_qty': fields.float('Qty', required=True),
               'product_uom': fields.many2one('product.uom', 'UoM', required=True),
               'bom_stage_line_id': fields.many2one('mrp.bom.stage.line.replace', 'BOM Stage', required=True, ondelete='cascade'),
               'type':fields.selection([('prime', 'Prime Material'), ('other', 'Other')], 'Type'),
               }
    
    _defaults = {
        'sequence': 1,
        'type': 'other'
    }
    
    def _check_sequence(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            if this.sequence <= 0:
                return False
        return True
    
    _constraints = [
        (_check_sequence, 'Error!\nSequence must be greater than 0.', ['sequence']),
    ]
    
mrp_bom_stage_material_line_replace()

class mrp_bom_stage_output_line_replace(osv.osv):
    _name = 'mrp.bom.stage.output.line.replace'
    _columns = {
               'product_id': fields.many2one('product.product', 'Product', required=True),
               'product_uom': fields.many2one('product.uom', 'UoM', required=True),
               'product_qty': fields.float('Qty', required=True),
               'bom_stage_line_id': fields.many2one('mrp.bom.stage.line.replace', 'BOM Stage', required=True, ondelete='cascade'),
               }
mrp_bom_stage_output_line_replace()

class mrp_routing_workcenter(osv.osv):
    _inherit = 'mrp.routing.workcenter'
    _columns = {
                'production_stage_id':fields.many2one('mrp.production.stage', 'Production Stage', required=True)
              }
mrp_routing_workcenter()

class mrp_workcenter(osv.osv):
    _inherit = 'mrp.workcenter'
    _columns = {
            'code':fields.char('Code', size=128, required=True),
            'production_stage_id':fields.many2one('mrp.production.stage', 'Production Stage', required=True)
    }
    
    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        default.update({'code': '/'})
        return super(mrp_workcenter, self).copy(cr, uid, id, default, context=context)
    
    def is_code_uniq(self, cr, uid, ids):
        for i in self.browse(cr, uid, ids):
            if i.code and i.code != '/':
                workcenter_ids = self.search(cr, uid, [('code', '=', i.code),
                                                  ('id', '<>', i.id)])
                if workcenter_ids:
                    return False
        return True
    
    _constraints = [(is_code_uniq, 'Error: Code already exists !!!', ['code'])]
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if name:
                ids = self.search(cr, user, ['&', '!', ('code', '=like', name + "%"), ('name', operator, name)] + args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
class product_category(osv.osv):
    _inherit = 'product.category'
    _columns = {
        'production_stage_id':fields.many2one('mrp.production.stage', 'Production Stage')
    }
    
class product_product(osv.osv):
    _inherit = 'product.product'
    _columns = {
    }
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
          
        categ_pool = self.pool.get('product.category')
        new_args = []
                
        if context.has_key('search_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'TP')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
           
        if context.has_key('search_service'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'DV')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
                    
        if context.has_key('search_product'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'HH')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
                    
        if context.has_key('search_materials'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'NVL')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
            
        if context.has_key('search_semi_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'BTP')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
            
        if context.has_key('search_congcudungcu'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'CCDC')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
            
        if context.has_key('search_nguyenlieutieuhao'):
            categ_ids = categ_pool.search(cr, uid, [('code', '=', 'NLTH')])
            if len(categ_ids):
                new_args.append(('categ_id', 'child_of', categ_ids))
                    
        if len(new_args):
            if len(new_args) > 1:
                for i in range(0, len(new_args) - 1):
                    args.append('|')
            args += new_args
 
        operator = False
        value = False
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'name' and args[pos][1] in ('like', 'ilike', '=') and args[pos][2]:
                operator = args[pos][1]
                value = args[pos][2]
                args.pop(pos)
                break
            pos += 1
        if operator:
            args.append('|')
            args.append('|')
            args.append(['name', operator, value])
            args.append(['barcode', operator, value])
            args.append(['default_code', operator, value])
        return super(product_product, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
product_product()
