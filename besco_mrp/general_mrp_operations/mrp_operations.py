# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp import pooler
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.exceptions import UserError, AccessError
from lxml import etree
import base64
import xlrd

DEFAULT_SERVER_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class product_product(osv.osv):
    _inherit = 'product.product'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        ids = super(product_product, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
        if context.has_key('search_related_finished_good_id'):
            args.append(('related_finished_good_id', '=', context['search_related_finished_good_id']))
            cr.execute('select id from product_product where related_finished_good_id=%s' % (context['search_related_finished_good_id']))
            ids = [x[0] for x in cr.fetchall()]
        return ids

class direct_labour(osv.osv):
    _name = 'direct.labour'
    _columns = {
        'emp_id':fields.many2one('hr.employee', 'Employee', required=True),
        'job_id':fields.many2one('hr.job', 'Job'),
        'department_id':fields.many2one('hr.department', 'Department'),
        'hour_nbr': fields.float('Number of Hours', required=True),
        'result_id':fields.many2one('mrp.operation.result', 'Operation Result'),
    }
direct_labour()

# Thanh: Add more information for Operation to manage semi-product
class mrp_production_workcenter_line(osv.osv):
    _inherit = 'mrp.production.workcenter.line'
    _order = 'priority,sequence'
    
    def list_stages(self, cr, uid, context=None):
        ids = self.pool.get('mrp.production.stage').search(cr, uid, [])
        res = []
        for line in self.pool.get('mrp.production.stage').browse(cr, uid, ids):
            res.append((line.id, line.name))
        return res
#         return self.pool.get('mrp.congdoan').name_get(cr, uid, ids, context=context)

    def list_workcenters(self, cr, uid, context=None):
        ids = self.pool.get('mrp.workcenter').search(cr, uid, [])
#         return self.pool.get('mrp.workcenter').name_get(cr, uid, ids, context=context)
        res = []
        for line in self.pool.get('mrp.workcenter').browse(cr, uid, ids):
            res.append((line.id, line.name))
        return res
    
    def default_quicksearch(self, cr, uid, context=None):
        res = {'congdoan_id':False,
               'workcenter_id': False}
        production_stage_ids = self.pool.get('mrp.production.stage').search(cr, uid, [])
        res ['congdoan_id'] = production_stage_ids and production_stage_ids[0] or False
        if res['congdoan_id']:
            workcenter_ids = self.pool.get('mrp.workcenter').search(cr, uid, [('production_stage_id', '=', res['congdoan_id'])])
            res ['workcenter_id'] = workcenter_ids and workcenter_ids[0] or False
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if name:
            ids = self.search(cr, user, args + ['|', ('name', operator, name), ('production_id.name', operator, name)], context=context, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def _fail_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = 0.0
            res[line.id] = line.produced_qty - line.reached_qty or 0.0 
        return res
    
    _columns = {
        'priority': fields.integer('Priority', readonly=True, states={'draft': [('readonly', False)]}),
        'product_id': fields.many2one('product.product', 'Product', readonly=True, states={'draft': [('readonly', False)]}),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, states={'draft':[('readonly', False)]}),
        'produced_qty': fields.float('Produced Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'reached_qty': fields.float('Reached Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True, states={'startworking':[('readonly', False)]}),
        'fail_qty': fields.function(_fail_qty, digits_compute=dp.get_precision('Product Unit of Measure'), string='Failing Quantity',),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', readonly=True, states={'draft': [('readonly', False)]}),
        'location_src_id': fields.many2one('stock.location', 'Raw Materials Location', required=True,
            readonly=True, states={'draft':[('readonly', False)]},
            help="Location where the system will look for components."),
        'location_dest_id': fields.many2one('stock.location', 'Finished Products Location', required=True,
            readonly=True, states={'draft':[('readonly', False)]},
            help="Location where the system will stock the finished products."),
                
        
        'congdoan_id': fields.many2one('mrp.production.stage', 'Stage', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        # Thanh: filter where workcenter beloging to
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=True, readonly=True, states={'draft': [('readonly', False)]},
                                        ),
        'production_results': fields.one2many('mrp.operation.result', 'operation_id', 'Production Results', readonly=True, states={'draft':[('readonly', False)], 'startworking':[('readonly', False)]}),
        'product_lines': fields.one2many('mrp.production.workcenter.product.line', 'operation_id', 'Scheduled goods',
            readonly=True, states={'draft':[('readonly', False)], 'startworking':[('readonly', False)]}),
        'consumed_product': fields.one2many('mrp.production.workcenter.product.consumed', 'operation_id', 'Consumed Product',
            readonly=True, states={'done':[('readonly', False)]}),
        'fail_location_id': fields.many2one('stock.location', 'Fails Location', readonly=True, states={'draft':[('readonly', False)], 'startworking':[('readonly', False)]}),
        }
    
    def _get_fail_location(self, cr, uid, context=None):
        fail_location_id = self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'inventory'), ('scrap_location', '=', True)])
        return fail_location_id and fail_location_id[0] or False
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(mrp_production_workcenter_line, self).default_get(cr, uid, fields, context=context)
        if 'production_id' in res:
            production_id = res['production_id']
            production_obj = self.pool.get('mrp.production').browse(cr, uid, production_id)
            res.update[{'location_id': production_obj.location_id.id or False,
                        'location_dest_id': production_obj.location_dest_id.id or False}]
        return res
    
    _defaults = {'name': '/', 'fail_location_id': _get_fail_location}
    
    def update_operation_sequence(self, cr, uid, congdoan_id, workcenter_id, current_date_planned, operation_id, update_date_planned=False):
        dem = 0
        previous_date_planned_end = False
        if current_date_planned:
            previous_ids = self.search(cr, uid, [('state', 'in', ['draft', 'pause', 'startworking']),
                ('congdoan_id', '=', congdoan_id),('workcenter_id', '=', workcenter_id),('id', '!=', operation_id)],
                ('date_planned', '!=', False),('date_planned', '<', current_date_planned), order='date_planned asc')
            for previous_id in previous_ids:
                dem += 1
                if update_date_planned:
                    previous_data = self.read(cr, uid, previous_id, ['date_planned', 'hour'])
                    date_planned = previous_date_planned_end
                    if not previous_date_planned_end:
                        date_planned = previous_data['date_planned']
                    date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                    date_planned_end = date_planned + timedelta(hours=previous_data['hour'])
                    date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                        ''' % (dem, date_planned, date_planned_end, previous_id))
                    cr.execute('commit;')
                    previous_date_planned_end = date_planned_end
                else:
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, previous_id))
                    cr.execute('commit;')
            dem += 1
            if update_date_planned and previous_date_planned_end:
                current_data = self.read(cr, uid, previous_id, ['date_planned', 'hour'])
                date_planned = datetime.strptime(previous_date_planned_end, DEFAULT_SERVER_DATETIME_FORMAT)
                date_planned_end = date_planned + timedelta(hours=current_data['hour'])
                date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                    ''' % (dem, date_planned, date_planned_end, operation_id))
                cr.execute('commit;')
            else:
                cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, operation_id))
                cr.execute('commit;')
            next_ids = self.search(cr, uid, [('state', 'in', ['draft', 'pause', 'startworking']),
                ('congdoan_id', '=', congdoan_id),('workcenter_id', '=', workcenter_id), ('id', '!=', operation_id)],
                ('date_planned', '!=', False),('date_planned', '>', current_date_planned),order='date_planned asc')
            for next_id in next_ids:
                dem += 1
                if update_date_planned:
                    next_data = self.read(cr, uid, next_id, ['date_planned', 'hour'])
                    date_planned = previous_date_planned_end
                    if not previous_date_planned_end:
                        date_planned = next_data['date_planned']
                    date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                    date_planned_end = date_planned + timedelta(hours=next_data['hour'])
                    date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    cr.execute('''UPDATE mrp_production_workcenter_line  SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                       ''' % (dem, date_planned, date_planned_end, next_id))
                    cr.execute('commit;')
                    previous_date_planned_end = date_planned_end
                else:
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, next_id))
                    cr.execute('commit;')
        else:
            exist_ids = self.search(cr, uid, [('state', 'in', ['draft', 'pause', 'startworking']),('date_planned', '!=', False),
                ('congdoan_id', '=', congdoan_id), ('workcenter_id', '=', workcenter_id)],order='date_planned asc')
            for exist_id in exist_ids:
                dem += 1
                if update_date_planned:
                    exist_data = self.read(cr, uid, exist_id, ['date_planned', 'hour'])
                    date_planned = previous_date_planned_end
                    if not previous_date_planned_end:
                        date_planned = exist_data['date_planned']
                    date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                    date_planned_end = date_planned + timedelta(hours=exist_data['hour'])
                    date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                        ''' % (dem, date_planned, date_planned_end, exist_id))
                    cr.execute('commit;')
                    previous_date_planned_end = date_planned_end
                else:
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, exist_id))
                    cr.execute('commit;')
        # Thanh: Update sequence for date_planned is Null
        other_ids = self.search(cr, uid, [('state', 'in', ['draft', 'startworking']), ('congdoan_id', '=', congdoan_id),('workcenter_id', '=', workcenter_id), ('date_planned', '=', False)])
        for other_id in other_ids:
            dem += 1
            cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, other_id))
            cr.execute('commit;')
        return True
    
    def update_sequence_new(self, cr, uid, sequence, congdoan_id, workcenter_id, current_date_planned, operation_id, update_date_planned=False):
        cr.execute('commit;')
        previous_date_planned_end = False
        dem = False
        if sequence == 1 and current_date_planned: 
            dem = 1 
            previous_ids = self.search(cr, uid, [('state', 'in', ['draft', 'pause']),
                ('congdoan_id', '=', congdoan_id),('workcenter_id', '=', workcenter_id),
                ('date_planned', '!=', False),('sequence', '>=', sequence),
                ('id', '!=', operation_id)], order='sequence asc')
            for previous_id in previous_ids:
                dem += 1
                if update_date_planned:
                    previous_data = self.read(cr, uid, previous_id, ['hour'])
                    date_planned = previous_date_planned_end
                    if not previous_date_planned_end:
                        date_planned = current_date_planned
                    date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                    date_planned_end = date_planned + timedelta(hours=previous_data['hour'])
                    date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                    ''' % (dem, date_planned, date_planned_end, previous_id))
                    cr.execute('commit;')
                    previous_date_planned_end = date_planned_end
                else:
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, previous_id))
                    cr.execute('commit;')
                    
        if sequence != 1 and current_date_planned:
            dem = 0
            previous_ids = self.search(cr, uid, [('state', 'in', ['draft', 'startworking', 'pause']),
                ('congdoan_id', '=', congdoan_id),('workcenter_id', '=', workcenter_id),('date_planned', '!=', False)], order='date_planned asc')
            for previous_id in previous_ids:
                dem += 1
                if update_date_planned:
                    previous_data = self.read(cr, uid, previous_id, ['date_planned', 'hour'])
                    date_planned = previous_date_planned_end
                    if not previous_date_planned_end:
                        date_planned = previous_data['date_planned']
                    date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                    date_planned_end = date_planned + timedelta(hours=previous_data['hour'])
                    date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s, date_planned='%s', date_planned_end='%s' WHERE id=%s
                    ''' % (dem, date_planned, date_planned_end, previous_id))
                    cr.execute('commit;')
                    previous_date_planned_end = date_planned_end
                else:
                    cr.execute('''UPDATE mrp_production_workcenter_line SET sequence=%s WHERE id=%s''' % (dem, previous_id))
                    cr.execute('commit;')
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        result = super(mrp_production_workcenter_line, self).write(cr, uid, ids, vals, context=context)
        if vals.get('sequence',False):
            for prod in self.browse(cr, uid, ids, context=context):
                if vals.get('hour',False):
                    hours = vals['hour']
                else:
                    hours = prod.hour
                if prod.state == 'startworking':
                    vals['sequence'] = prod.sequence
                    raise osv.except_osv(unicode('Error', 'utf8'), unicode('Không thể thay đổi lịch khi đang ở trạng thái sản xuất.', 'utf8'))
                else:
                    cr.execute('''SELECT id FROM mrp_production_workcenter_line WHERE state = 'startworking' AND congdoan_id = %s  AND workcenter_id = %s AND sequence = %s AND id != %s 
                    ''' %(prod.congdoan_id.id, prod.workcenter_id.id, vals['sequence'], prod.id))
                    res = cr.fetchone()
                    if res and res[0]:
                        vals['sequence'] = prod.sequence
                        vals['date_planned'] = prod.date_planned
                        raise osv.except_osv(unicode('Error', 'utf8'), unicode('Không thể xếp trước yêu cầu đang sản xuất.', 'utf8'))
                    else:
                        line_ids = self.search(cr, uid, [('state', 'in', ['draft', 'pause']), ('sequence', '<=', vals['sequence']),
                          ('congdoan_id','=', prod.congdoan_id.id),('workcenter_id', '=', prod.workcenter_id.id),('id', '!=', prod.id)])
                        if line_ids:
                            operation_obj = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, line_ids[0])
                            date_planned = operation_obj.date_planned or False 
                            if date_planned:
                                vals['date_planned'] = date_planned
                                date_planned = datetime.strptime(date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                                date_planned_end = date_planned + timedelta(hours=hours)
                                date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                                vals['date_planned_end'] = date_planned_end
                                self.update_sequence_new(cr, uid, vals['sequence'], prod.congdoan_id.id, prod.workcenter_id.id, date_planned_end, prod.id,update_date_planned=True)
        
        if vals.get('workcenter_id', False):
            for prod in self.browse(cr, uid, ids, context=context):
                self.update_sequence_new(cr, uid, False, prod.congdoan_id.id, vals['workcenter_id'], prod.date_planned_end, prod.id, update_date_planned=True)
        
        if vals.get('hour', False):
            for prod in self.browse(cr, uid, ids, context=context):
                date_planned = datetime.strptime(prod.date_planned, DEFAULT_SERVER_DATETIME_FORMAT)
                date_planned_end = date_planned + timedelta(hours=hours)
                date_planned_end = date_planned_end.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                vals['date_planned_end'] = date_planned_end
                
        if vals.get('state') and vals['state'] == 'done':
            vals['sequence'] = 0
        return result
    
    def create(self, cr, uid, vals, context=None):
        if not vals.get('date_planned', False):
            vals['sequence'] = len(self.search(cr, uid, [('state', 'in', ['draft', 'startworking']),
               ('congdoan_id', '=', vals.get('congdoan_id',False)),('workcenter_id', '=', vals.get('workcenter_id',False))])) + 1
        
        if vals.get('name', '/'):
            production = self.pool.get('mrp.production').browse(cr, uid, vals['production_id'])
            congdoan = self.pool.get('mrp.production.stage').browse(cr, uid, vals['congdoan_id'])
            number = production.name or ''
            number += '/' + congdoan.code
            
            stt = len(self.search(cr, uid, [('production_id', '=', vals['production_id']), ('congdoan_id', '=', vals['congdoan_id'])])) + 1
            number += '/%%0%sd' % 2 % stt
            vals.update({'name':number})
        return super(mrp_production_workcenter_line, self).create(cr, uid, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        unlink_data = {}
        for line in self.browse(cr, uid, ids):
            if line.state in ['draft', 'startworking']:
                if not unlink_data.has_key(line.congdoan_id.id):
                    unlink_data.update({line.congdoan_id.id: [line.workcenter_id.id]})
                else:
                    if line.workcenter_id.id not in unlink_data[line.congdoan_id.id]:
                        unlink_data[line.congdoan_id.id].append(line.workcenter_id.id)
                update_ids = self.search(cr, uid, [('state', 'in', ['draft', 'startworking']),('congdoan_id', '=', line.congdoan_id.id),('workcenter_id', '=', line.workcenter_id.id), ('sequence', '>', line.sequence)],)
                if len(update_ids):
                    cr.execute("UPDATE mrp_production_workcenter_line SET sequence=sequence-1 WHERE id in %s", (tuple(update_ids),))
        for congdoan_id, workcenter_ids in unlink_data.items():
            for workcenter_id in workcenter_ids:
                self.update_operation_sequence(cr, uid, congdoan_id, workcenter_id, False, False, update_date_planned=True)
        return super(mrp_production_workcenter_line, self).unlink(cr, uid, ids, context)
    
    # Thanh: Overwrite to prevent error
    def modify_production_order_state(self, cr, uid, ids, action):
        """ Modifies production order state if work order state is changed.
        @param action: Action to perform.
        @return: Nothing
        """
        prod_obj_pool = self.pool.get('mrp.production')
        oper_obj = self.browse(cr, uid, ids)[0]
        prod_obj = oper_obj.production_id
        if action == 'start':
            if prod_obj.state == 'confirmed':
                prod_obj_pool.force_production(cr, uid, [prod_obj.id])
                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_produce')
            elif prod_obj.state == 'ready':
                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_produce')
            elif prod_obj.state == 'in_production':
                return
            else:
                raise osv.except_osv(_('Error!'), _("Manufacturing order cannot be started in state '%s'!") % (prod_obj.state))
        if action == 'done':
            if prod_obj.state == 'in_production':
                operation_ids = self.search(cr, uid, [('production_id','=',prod_obj.id)])
                operation_done_ids = self.search(cr, uid, [('production_id','=',prod_obj.id),('state','=','done'),('id','!=',oper_obj.id)])
                if len(operation_ids) - len(operation_done_ids) == 1:
                    prod_obj_pool.action_done(cr, uid, prod_obj.id, context=None)
        else:
            oper_ids = self.search(cr, uid, [('production_id', '=', prod_obj.id)])
            obj = self.browse(cr, uid, oper_ids)
            flag = True
            for line in obj:
                if line.state != 'done':
                    flag = False
            if flag:
                for production in prod_obj_pool.browse(cr, uid, [prod_obj.id], context=None):
                    if production.move_lines or production.move_created_ids:
                        prod_obj_pool.action_produce(cr, uid, production.id, production.product_qty, 'consume_produce', context=None)
                prod_obj_pool.signal_workflow(cr, uid, [prod_obj.id], 'button_produce_done')
        return
    
    # Thanh: Update start date of this operation as the first line of result
    def action_start_working(self, cr, uid, ids, context=None):
        self.modify_production_order_state(cr, uid, ids, 'start')
        # Thanh: Modify here
        for operation in self.browse(cr, uid, ids):
            date_start = time.strftime('%Y-%m-%d %H:%M:%S')
            for result in operation.production_results:
                date_start = result.start_date
                break
            self.write(cr, uid, [operation.id], {'state':'startworking', 'date_start': date_start}, context=context)
        return True
    
    def create_move_loss(self, cr, uid, operation, context=None):
        location_id = False
        location_dest_id = False
        move = self.pool.get('stock.move')
        location_pool = self.pool.get('stock.location')
        production_obj = self.pool.get('mrp.production').browse(cr, uid, operation.production_id.id)
        
        if not production_obj.warehouse_id:
            raise osv.except_osv(unicode('Error', 'utf8'), unicode('Do not have warehouse in MO .', 'utf8'))
        warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)
        if not warehouse_obj.wh_production_loc_id.id:
            raise osv.except_osv(_('Error!', 'utf8'), _('Lack of Locations Production at warehouse (%s).', 'utf8') % (warehouse_obj.name))
        location_id = warehouse_obj.wh_production_loc_id.id
        if not operation.fail_location_id:
            raise osv.except_osv(_('Error!', 'utf8'), _('Lack of Locations Finished Product at warehouse (%s).', 'utf8')% (warehouse_obj.name))
        location_dest_id = operation.fail_location_id.id
        
        var = {'name': operation.product_id.name, 'picking_id': False, 'operation_id': operation.id, 'production_id': operation.production_id.id,
              'product_id': operation.product_id.id, 'date': time.strftime('%Y-%m-%d %H:%M:%S'),
              'product_uom_qty': operation.reached_qty, 'product_uom': operation.product_uom.id, 'state': 'draft',
              'location_id': location_id, 'location_dest_id': location_dest_id, 'origin': operation.name}
              
        move_id = move.create(cr, uid, var)
        move.action_confirm(cr, uid, [move_id], context=context)[0]
        move.action_done(cr, uid, [move_id])
    
    # Thanh: Overwrite actiondone to check previous Operation is done yet
    def action_done(self, cr, uid, ids, context=None):
        # Thanh: Modify here
        production_pool = self.pool.get('mrp.production')
        consumed_obj = self.pool.get('mrp.production.workcenter.product.consumed')
        for operation in self.browse(cr, uid, ids):
            if operation.reached_qty > operation.produced_qty:
                raise osv.except_osv(_('Error!','utf8'), _('Qty produced in stages (%s) is not greater than the total amount was produced.','utf8') % (operation.congdoan_id.name))
            if operation.reached_qty == 0:
                raise osv.except_osv(_('Error!','utf8'), _('Not have Qty Produced in stage %s.','utf8')%(operation.congdoan_id.name))
            if operation.priority > 5:
                priority_old = operation.priority - 5 or 0
                operation_ids = self.search(cr, uid, [('production_id', '=', operation.production_id.id), ('priority', '=', priority_old), ('production_id', '!=', operation.id)])
                for line in self.browse(cr, uid, operation_ids):
                    if line.state != 'done':
                        raise osv.except_osv(_('Error!','utf8'), _('Need completed the stage %s before.','utf8') % (line.congdoan_id.name))
                    for i in operation.consumed_product:
                        if i.product_id.id == line.product_id.id:
                            total_qty_production = line.produced_qty or 0.0
                            norms_production = operation.product_qty or 0.0
                            total_received_qty = line.reached_qty or 0.0
                            norms_operation = i.norms_operation or 0.0
                            received_qty = line.reached_qty or 0.0
                            if total_qty_production > 0.0:
                                product_consume = received_qty * total_qty_production / norms_production
                            else: 
                                product_consume = 0.0
                            product_rest = received_qty - product_consume or 0.0
                            consumed_obj.write(cr, uid, [i.id], {'norms_production': norms_production, 'total_received_qty': total_received_qty,
                                'total_qty_production': total_qty_production, 'received_qty': received_qty, 'product_consume': product_consume,'product_rest': product_rest})
            # Thanh: Get Date finished from Results
            delay = 0.0
            date_finished = time.strftime('%Y-%m-%d %H:%M:%S')
            dem = 0
            for result in operation.production_results:
                dem += 1
                if dem == len(operation.production_results):
                    date_finished = result.end_date
                    break
            date_start = datetime.strptime(operation.date_start, '%Y-%m-%d %H:%M:%S')
            date_finished = datetime.strptime(date_finished, '%Y-%m-%d %H:%M:%S')
            delay += (date_finished - date_start).days * 24
            delay += (date_finished - date_start).seconds / float(60 * 60)
            self.create_move_loss(cr, uid, operation, context=context)
            # Thanh: Get Date finished from Results
            self.write(cr, uid, [operation.id], {'state':'done', 'date_finished': date_finished, 'delay':delay}, context=context)
         
        self.signal_workflow(cr, uid, [result.operation_id.id], 'button_done')
        self.modify_production_order_state(cr, uid, ids, 'done')
        return True
    
    # Thanh: Allow cancel order at Done state
    def action_cancel(self, cr, uid, ids, context=None):
        for operation in self.browse(cr, uid, ids):
            if operation.state == 'done':
                self.signal_workflow(cr, uid, [operation.id], 'button_cancel')
            for line in operation.production_results:
                self.pool.get('mrp.operation.result').button_cancel(cr, uid, [line.id], context=context)
            cr.execute(''' DELETE FROM stock_move WHERE operation_id = %s AND location_dest_id = %s 
            ''' % (operation.id, operation.fail_location_id.id))
        return self.write(cr, uid, ids, {'state':'cancel', 'produced_qty': 0, 'reached_qty': 0}, context=context)
    
    def action_updates_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context.update({
            'active_model': self._name,
            'active_ids': ids,
            'active_id': len(ids) and ids[0] or False})
        return { 'name': _('Updates Quantity Actual'),
            'view_type': 'form', 'view_mode': 'form',
            'res_model': 'updates.number','type': 'ir.actions.act_window',
            'target': 'new', 'context': context,'nodestroy': True }
    
mrp_production_workcenter_line()    

class mrp_production_workcenter_product_line(osv.osv):
    _name = 'mrp.production.workcenter.product.line'
    _description = 'Operation Scheduled Product'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence', required=False),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'operation_id': fields.many2one('mrp.production.workcenter.line', 'Operation Order', ondelete='cascade', select=True),
    }
mrp_production_workcenter_product_line()

class mrp_production_workcenter_product_consumed(osv.osv):
    _name = 'mrp.production.workcenter.product.consumed'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'product_id': fields.many2one('product.product', 'Material', required=True),
        'product_uom': fields.many2one('product.uom', 'Uom', required=True),
        'operation_id': fields.many2one('mrp.production.workcenter.line', 'Operation Order', ondelete='cascade', select=True),
        'production_id': fields.many2one('mrp.production', 'Production Order', ondelete='cascade', select=True),
        'total_received_qty': fields.float('Total Quantity Received', required=True),
        'norms_operation': fields.float('Norms Quantity', required=True),
        'norms_production': fields.float('Production Norms', required=True),
        'received_qty': fields.float('Quantity Received'),
        'total_qty_production':fields.float('Production Results'),
        'product_consume': fields.float('Quantity Consume'),
        'product_rest': fields.float('Remaining'),
        'actual_qty': fields.float('Quantity Actual'),
        'product_rest_actual': fields.float('Remaining Actual'),
    }
mrp_production_workcenter_product_consumed()

class mrp_operation_result(osv.osv):
    _name = 'mrp.operation.result'
    _description = 'Operation Result'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'operation_id,start_date'
    
    def _get_hours(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = 0.0
            start_date = datetime.strptime(line.start_date, DEFAULT_SERVER_DATETIME_FORMAT)
            end_date = datetime.strptime(line.end_date, DEFAULT_SERVER_DATETIME_FORMAT)
            if end_date > start_date:
                diff_hours = round(float((end_date - start_date).seconds) / 3600, 2)
                res[line.id] = diff_hours
        return res
    
    def _sum_qty(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids):
            res[line.id] = 0.0
            for result in line.produced_products:
                res[line.id] += result.product_qty
        return res
    
    def _get_result(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('mrp.operation.result.produced.product').browse(cr, uid, ids, context=context):
            result[line.operation_result_id.id] = True
        return result.keys()
    
    _columns = {
        'name': fields.char('Reference', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'operation_id': fields.many2one('mrp.production.workcenter.line', 'Operation Order', required=True, select=True, track_visibility='onchange', states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}, ondelete='cascade'),
        'production_id': fields.related('operation_id','production_id', type="many2one", relation="mrp.production", store=False, string="Manufacturing Order", readonly=True),
        'finished_good_id': fields.related('operation_id', 'production_id', 'product_id', type="many2one", relation="product.product", store=False, string="Finished good", readonly=True),
        'calendar_id': fields.many2one('resource.calendar', 'Shift', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'start_date': fields.datetime('Start date', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'end_date': fields.datetime('End date', required=True, states={'done':[('readonly', True)], 'cancel':[('readonly', True)]}),
        'congdoan_id': fields.many2one('mrp.production.stage', 'Production stage'),
        'hours': fields.function(_get_hours, method=True, string="Hours", readonly=True,
            store={  'mrp.operation.result': (lambda self, cr, uid, ids, c={}: ids, ['start_date', 'end_date'], 10)}),
        'product_id': fields.many2one('product.product', 'Product',required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_qty': fields.function(_sum_qty, digits_compute=dp.get_precision('Product Unit of Measure'), string='Product Quantity',
            store={
                'mrp.operation.result': (lambda self, cr, uid, ids, c={}: ids, ['produced_products'], 10),
                'mrp.operation.result.produced.product': (_get_result, ['product_qty'], 10),
            }),
        'product_uom': fields.many2one('product.uom', 'UoM',required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'resource_id': fields.many2one('mrp.workcenter', 'Resource', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'produced_products': fields.one2many('mrp.operation.result.produced.product', 'operation_result_id', 'Produced Products', readonly=True, states={'draft': [('readonly', False)]}),
        'consumed_products': fields.one2many('mrp.operation.result.consumed.product', 'operation_result_id', 'Consumed Products', readonly=True, states={'draft': [('readonly', False)]}),
        'note': fields.text('Notes'),
        'write_date':  fields.datetime('Last Modification', readonly=True),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Updated by', readonly=True),
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('cancel', 'Cancelled'),
            ('done', 'Done'),
            ('transfered','Stock Transfered')
            ], 'Status', readonly=True),
        'finished': fields.boolean('Finished',readonly=True, states={'draft': [('readonly', False)]}),
        'direct_labour':fields.one2many('direct.labour', 'result_id', 'Direct Labour', ondelete='cascade', readonly=True, states={'draft': [('readonly', False)]}),
        }
    
    def _get_default_calendar_id(self, cr, uid, context=None):
        calendar_ids = self.pool.get('resource.calendar').search(cr, uid, [], context=context)
        return calendar_ids and calendar_ids[0] or False
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(mrp_operation_result, self).default_get(cr, uid, fields, context=context)
        if 'operation_id' in res:
            operation_id = res['operation_id']
            operation_obj = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, operation_id)
            res.update({'product_id': operation_obj.product_id.id,'product_uom': operation_obj.product_uom.id})
        return res
    
    _defaults = {
        'calendar_id': _get_default_calendar_id,
        'state': 'draft',
        'start_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'name': 'New'
    }
    
    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'name': 'New',
            'state': 'draft',
            'start_date': time.strftime('%Y-%m-%d %H:%M:%S'), 
        })
        return super(osv.osv, self).copy(cr, uid, id, default, context)
    
    def onchange_operation(self, cr, uid, ids, operation_id, context=None):
        res = domain = {}
        if operation_id:
            operation_obj = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, operation_id)
            res = {'product_id': operation_obj.product_id.id or False,  'product_uom': operation_obj.product_uom.id or False,
              'resource_id': operation_obj.workcenter_id.id or False, 'congdoan_id': operation_obj.congdoan_id.id or False}
            domain = {'product_id': [('id','=',operation_obj.product_id.id)],
                      'product_uom': [('id','=',operation_obj.product_uom.id)]}
        return {'value': res, 'domain': domain} 
    
    def create(self, cr, uid, vals, context=None):
        standard_worked = 0.0
        attendance = self.pool.get('resource.calendar.attendance')
        if context.get('calendar_id', False):
            start_date = datetime.strptime(vals['start_date'], DEFAULT_SERVER_DATETIME_FORMAT)
            calendar_obj = self.pool.get('resource.calendar').browse(cr, uid, vals['calendar_id'])
            
            cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (start_date))
            result = cr.dictfetchall()
            dayofweek = result and result[0] and result[0]['dayofweek'] or False
            dayofweek = int(dayofweek - 1)
           
            attendance_id = attendance.search(cr, uid,[('calendar_id','=',calendar_obj.id),('dayofweek','=',str(dayofweek))], limit=1)
            if attendance_id:
                attendance_obj = attendance.browser(cr, uid, attendance_id[0])
                standard_worked = attendance_obj.hour_to - attendance_obj.hour_from 
                end_date = start_date + timedelta(hours=standard_worked)
                vals.update({'end_date': end_date})
            
        if vals.get('name', 'New'):
            workcenter = self.pool.get('mrp.production.workcenter.line').browse(cr, uid, vals['operation_id'])
            number = workcenter.name
            stt = len(self.search(cr, uid, [('operation_id', '=', vals['operation_id'])])) + 1
            number += '-%%0%sd' % 3 % stt
            vals.update({'name':number})
        return super(mrp_operation_result, self).create(cr, uid, vals, context=context)
    
    def onchange_calendar_id(self, cr, uid, ids, calendar_id, start_date, context=None):
        end_date = False
        standard_worked = 0.0
        attendance = self.pool.get('resource.calendar.attendance')
        
        if not calendar_id:
            return True
        if calendar_id:
            calendar_obj = self.pool.get('resource.calendar').browse(cr, uid, calendar_id)
            cr.execute('''SELECT EXTRACT(ISODOW FROM TIMESTAMP '%s') dayofweek;''' % (start_date))
            result = cr.dictfetchall()
            dayofweek = result and result[0] and result[0]['dayofweek'] or False
            dayofweek = int(dayofweek - 1)
            
            attendance_id = attendance.search(cr, uid,[('calendar_id','=',calendar_obj.id),('dayofweek','=',str(dayofweek))], limit=1)
            if attendance_id:
                attendance_obj = attendance.browse(cr, uid, attendance_id[0])
                standard_worked = attendance_obj.hour_to - attendance_obj.hour_from 
                end_date = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S') + relativedelta(hours=standard_worked)
        return {'value':{'end_date': end_date}}
    
    def create_move_result(self, cr, uid, mrp_result, context=None):
        location_id = False
        location_dest_id = False
        move = self.pool.get('stock.move')
        production_obj = self.pool.get('mrp.production').browse(cr, uid, mrp_result.production_id.id)
        if not production_obj.warehouse_id:
            raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Thiếu thông tin Vị Trí Kho trong lệnh sản xuất!', 'utf8'))
        
        warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)
        
        if not mrp_result.product_id.property_stock_production.id:
            error = "Thiếu thông tin Địa Điểm Sản Xuất trện sản phẩm (%s)." % (str(mrp_result.product_id.name))
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_id = mrp_result.product_id.property_stock_production.id
        
        if not warehouse_obj.wh_production_loc_id.id:
            error = "Thiếu thông tin Địa Điểm Đích trong Nhật Ký Sản Xuất (%s)." % (str(warehouse_obj.production_out_type_id.name))
            raise osv.except_osv(unicode('Lỗi!', 'utf8'), unicode(error, 'utf8'))
        location_dest_id = warehouse_obj.wh_production_loc_id.id
        
        var = {'name': unicode(mrp_result.product_id.name), 'picking_id': False, 'picking_type_id': warehouse_obj.production_in_type_id.id,
              'production_id': mrp_result.production_id.id, 'result_id': mrp_result.id,
              'product_finished_goods': mrp_result.production_id.product_id.id, 'product_id': mrp_result.product_id.id,
              'date': mrp_result.end_date, 'product_uom_qty': mrp_result.product_qty, 'product_uom': mrp_result.product_uom.id,
              'location_id': location_id, 'location_dest_id': location_dest_id, 'state': 'draft', 'origin': mrp_result.operation_id.name}
            
        move_id = move.create(cr, uid, var)
        move.action_confirm(cr, uid, [move_id], context=context)
        move.action_done(cr, uid, [move_id])
        
    def button_confirm(self, cr, uid, ids, context=None):
        workcenter = self.pool.get('mrp.production.workcenter.line')
        for result in self.browse(cr, uid, ids):
            if not len(result.produced_products):
                error = 'Results of production does not exist.'
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            
            if not len(result.direct_labour):
                error = 'Employee information have not yet been created.'
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            
            if not len(result.production_id.move_lines):
                error = 'Materials will be consumed not exist.'
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            
            if result.operation_id.state == 'draft':
                if result.finished:
                    workcenter.action_start_working(cr, uid, [result.operation_id.id], context=context)
                else:
                    workcenter.action_start_working(cr, uid, [result.operation_id.id], context=context)
                    
            if result.operation_id.state == 'cancel':
                error = "Production requirements ('%s') of this section ('%s') has been canceled." % (str(result.operation_id.name), str(result.operation_id.congdoan_id.type))
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            
            self.write(cr, uid, [result.id], {'state':'done'})
            
            workcenter_obj = workcenter.browse(cr, uid, result.operation_id.id)
            product_qty = workcenter_obj.produced_qty + result.product_qty or 0.0
            workcenter.write(cr , uid, [result.operation_id.id], {'produced_qty': product_qty})
            
            if result.finished:
                workcenter.action_done(cr, uid, result.operation_id.id)
            
            self.create_move_result(cr, uid, result, context=context)
            
            consumed_obj = self.pool.get('mrp.production.workcenter.product.consumed')
            total_qty_production = product_qty
            
            production_id = result.production_id.id or False
            operation_id = result.operation_id.id or False
            end_date = result.end_date or False
            workcenter_obj = workcenter.browse(cr, uid, operation_id)
            
            production_obj = self.pool.get('mrp.production').browse(cr, uid, production_id)
            if not production_obj.warehouse_id:
                raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Thiếu thông tin Vị Trí Kho trong lệnh sản xuất!', 'utf8'))
            warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)
            
            if not warehouse_obj.wh_production_loc_id.id:
                error = "Locations Material  does not exist."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            location_id = warehouse_obj.wh_production_loc_id.id
            
            if not result.product_id.property_stock_production.id:
                error = "Production Locations  does not exist."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            location_dest_id = result.product_id.property_stock_production.id

            norms_production = workcenter_obj.product_qty or 0.0
            for product_lines in workcenter_obj.product_lines:
                sql = """ SELECT actual_qty 
                    FROM mrp_production_workcenter_product_consumed 
                    WHERE operation_id = %s AND product_id = %s
                """ % (operation_id, product_lines.product_id.id)
                cr.execute(sql)
                result = cr.dictfetchall()
                actual_qty = result and result[0] and result[0]['actual_qty'] or 0.0

                cr.execute('''DELETE FROM mrp_production_workcenter_product_consumed WHERE operation_id = %s AND product_id = %s;''' % (operation_id, product_lines.product_id.id))
                
                norms_operation = product_lines.product_qty or 0.0
                sql = """ SELECT sum(product_uom_qty) total_received_qty
                    FROM mrp_production_move_ids mpmi INNER JOIN mrp_production mp on mp.id = mpmi.production_id
                        INNER JOIN stock_move sm on sm.id = mpmi.move_id
                    WHERE mp.id = %s AND sm.product_id = %s
                """ % (production_id, product_lines.product_id.id)
                cr.execute(sql)
                result1 = cr.dictfetchall()
                total_received_qty = result1 and result1[0] and result1[0]['total_received_qty'] or 0.0
                
                received_qty = total_received_qty and (norms_operation / total_received_qty) * total_received_qty or 0.0
                
                if total_qty_production > 0:
                    product_consume = received_qty * total_qty_production / norms_production
                else: 
                    product_consume = 0.0
                
                product_rest = received_qty - product_consume or 0.0
                received_qty_update = received_qty - actual_qty or 0.0
                
                consumed_obj.create(cr, uid, {'sequence': product_lines.sequence or 0, 'product_id': product_lines.product_id.id or False,
                                            'product_uom': product_lines.product_uom.id or False, 'operation_id': product_lines.operation_id.id or False,
                                            'production_id': production_id, 'norms_operation': norms_operation, 'norms_production': norms_production,
                                            'total_received_qty': total_received_qty, 'total_qty_production': total_qty_production, 'received_qty': received_qty,
                                            'product_consume': product_consume, 'product_rest': product_rest, 'actual_qty': actual_qty, 'product_rest_actual': received_qty_update})
        return True
    
    def button_cancel(self, cr, uid, ids, context=None):
        move = self.pool.get('stock.move')
        workcenter = self.pool.get('mrp.production.workcenter.line')
        for result in self.browse(cr, uid, ids):
            if result.production_id.state == 'done':
                raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Production order (%s) is done.', 'utf8')% (result.production_id.name))
            else:
                cr.execute('''DELETE from stock_move where result_id = %s;''' % (result.id))
                workcenter_obj = workcenter.browse(cr, uid, result.operation_id.id)
                product_qty = workcenter_obj.produced_qty - result.product_qty or 0.0
                workcenter.write(cr , uid, [result.operation_id.id], {'produced_qty': product_qty})
                consumed_obj = self.pool.get('mrp.production.workcenter.product.consumed')
            total_qty_production = product_qty
            
            production_id = result.production_id.id or False
            operation_id = result.operation_id.id or False
            end_date = result.end_date or False
            workcenter_obj = workcenter.browse(cr, uid, operation_id)
            
            production_obj = self.pool.get('mrp.production').browse(cr, uid, production_id)
            if not production_obj.warehouse_id:
                raise osv.except_osv(unicode('Lỗi', 'utf8'), unicode('Thiếu thông tin Vị Trí Kho trong lệnh sản xuất!', 'utf8'))
            warehouse_obj = self.pool.get('stock.warehouse').browse(cr, uid, production_obj.warehouse_id.id)
            
            if not warehouse_obj.wh_production_loc_id.id:
                error = "Locations Material  does not exist."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            location_id = warehouse_obj.wh_production_loc_id.id
            
            if not result.product_id.property_stock_production.id:
                error = "Production Locations  does not exist."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            location_dest_id = result.product_id.property_stock_production.id
            
            norms_production = workcenter_obj.product_qty or 0.0
            for product_lines in workcenter_obj.product_lines:
                sql = """ SELECT actual_qty 
                    FROM mrp_production_workcenter_product_consumed 
                    WHERE operation_id = %s AND product_id = %s
                """ % (operation_id, product_lines.product_id.id)
                cr.execute(sql)
                result = cr.dictfetchall()
                actual_qty = result and result[0] and result[0]['actual_qty'] or 0.0

                cr.execute('''DELETE FROM mrp_production_workcenter_product_consumed WHERE operation_id = %s AND product_id = %s;''' % (operation_id, product_lines.product_id.id))
                
                norms_operation = product_lines.product_qty or 0.0
                sql = """ SELECT sum(product_uom_qty) total_received_qty
                    FROM mrp_production_move_ids mpmi INNER JOIN mrp_production mp on mp.id = mpmi.production_id
                        INNER JOIN stock_move sm on sm.id = mpmi.move_id
                    WHERE mp.id = %s AND sm.product_id = %s
                """ % (production_id, product_lines.product_id.id)
                cr.execute(sql)
                result1 = cr.dictfetchall()
                total_received_qty = result1 and result1[0] and result1[0]['total_received_qty'] or 0.0
                
                received_qty = total_received_qty and (norms_operation / total_received_qty) * total_received_qty or 0.0
                
                if total_qty_production > 0:
                    product_consume = received_qty * total_qty_production / norms_production
                else: 
                    product_consume = 0.0
                product_rest = received_qty - product_consume or 0.0
                received_qty_update = received_qty - actual_qty or 0.0
                
                consumed_obj.create(cr, uid, {'sequence': product_lines.sequence or 0, 'product_id': product_lines.product_id.id or False,
                                            'product_uom': product_lines.product_uom.id or False, 'operation_id': product_lines.operation_id.id or False,
                                            'production_id': production_id, 'norms_operation': norms_operation, 'norms_production': norms_production,
                                            'total_received_qty': total_received_qty, 'total_qty_production': total_qty_production, 'received_qty': received_qty,
                                            'product_consume': product_consume, 'product_rest': product_rest, 'actual_qty': actual_qty, 'product_rest_actual': received_qty_update})
            self.write(cr, uid, ids, {'state':'cancel'})
        return True
    
    def reset_to_draft(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'draft'})
    
    def button_transfered(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'transfered'})
    
mrp_operation_result()

class mrp_operation_result_produced_product(osv.osv):
    _name = 'mrp.operation.result.produced.product'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Qty'),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
        'notes': fields.text('Notes'),
        'operation_result_id': fields.many2one('mrp.operation.result', 'Operation Result', ondelete='cascade'),
        }
    
    def _check_qty(self, cr, uid, ids, context=None):
        for produced in self.browse(cr, uid, ids, context=context):
            if produced.product_qty <= 0:
                return False
        return True
 
    _constraints = [
        (_check_qty, 'Product Qty must be greater than 0.', ['product_qty']),
        ]
    
    def default_get(self, cr, uid, fields, context=None):
        prodlot_id = False
        res = super(mrp_operation_result_produced_product, self).default_get(cr, uid, fields, context=context)
        if context.get('default_operation_id'):
            operation_id = context['default_operation_id']
            res.update({'default_operation_id': operation_id})
        return res
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        product_uom = False
        if product_id:
            product_obj = self.pool.get('product.product').browse(cr, uid, product_id)
            product_uom =  product_obj.uom_id.id or False
        return {'value':{'product_uom': product_uom}}
mrp_operation_result_produced_product()

class mrp_operation_result_consumed_product(osv.osv):
    _name = 'mrp.operation.result.consumed.product'
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
        'operation_result_id': fields.many2one('mrp.operation.result', 'Operation Result', ondelete='cascade'),
        'move_id':fields.many2one('stock.move', 'Move Line', ondelete='cascade'),
        'date_consumed':fields.related('picking_id', 'date_done', type='date', string='Date Consumed', readonly=True),
        'picking_id':fields.many2one('stock.picking', 'Picking', required=False),
    }
mrp_operation_result_consumed_product()


    
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
