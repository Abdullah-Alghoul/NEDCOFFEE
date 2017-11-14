# -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp

class mrp_production_workcenter_line(osv.osv):
    _inherit = 'mrp.production.workcenter.line'
    
    _columns = {
        # Thanh: Set readonly when done
        'date_planned': fields.datetime('Scheduled Date', select=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_planned_end': fields.datetime('Scheduled End Date', select=True, readonly=True, states={'draft': [('readonly', False)]}),
        'production_id': fields.many2one('mrp.production', 'Manufacturing Order',
            track_visibility='onchange', select=True, ondelete='cascade', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'hour': fields.float('Number of Hours', digits=(16, 2), readonly=True, states={'draft': [('readonly', False)]}),
        'operation_finished': fields.boolean('Operation Finished Goods', readonly=True)
    }
    
mrp_production_workcenter_line()

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    
    def _default_wh_production_loc_id(self, cr, uid, ids, context=None):
        warehouse_pool = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_pool.search(cr, uid, [] , context=context)
        warehouse_obj = warehouse_pool.browse(cr, uid, warehouse_ids[0])
        wh_production_loc_id = warehouse_obj.wh_production_loc_id.id or False
        return wh_production_loc_id or False
    
    _columns = {
                'wh_production_loc_id': fields.many2one('stock.location', 'Production Stock')
    }
    _defaults = {'wh_production_loc_id': _default_wh_production_loc_id}
    
    def action_done(self, cr, uid, ids, context=None):
        operation_pool = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids, context=context):
            if not production.move_created_ids2:
                error = "Production results have not updated."
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            for work_order in production.workcenter_lines:
                if work_order.state == 'draft':
                    operation_pool.action_cancel(cr, uid, work_order.id, context=context)
                elif work_order.state == 'startworking':
                    operation_pool.action_done(cr, uid, work_order.id, context=context)
           
            self.write(cr, uid, ids, {'state': 'done'})
        return True
    
    def calculate_starttime(self, cr, uid, work_order):
        ls_time_start = False
        global is_preStartTime
        ldc_time_wait_state = 5
        ls_time_start_state_fist = False
        ls_time_state_fist = False
        if not ls_time_start_state_fist:
            ls_time_start_state_fist = is_preStartTime
        if ls_time_start_state_fist:
            ldc_time_wait_state = 10
            ls_time_start_state_fist = datetime.strptime(ls_time_start_state_fist, DEFAULT_SERVER_DATETIME_FORMAT)
            ls_time_state_fist = ls_time_start_state_fist + timedelta(minutes=ldc_time_wait_state)
            ls_time_state_fist = ls_time_state_fist.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        ls_time_end_proced_end = False
        cr.execute('''SELECT MAX(mor.end_date) FROM mrp_operation_result mor join mrp_production_workcenter_line mpwl on mor.operation_id = mpwl.id
            WHERE mpwl.congdoan_id=%s AND mpwl.workcenter_id=%s AND mpwl.id != %s''' % (work_order.congdoan_id.id, work_order.workcenter_id.id,work_order.id))
        res = cr.fetchone()
        if res and res[0]:
            ls_time_end_proced_end = res[0] or False
        else:
            cr.execute(''' SELECT MAX(date_planned_end) FROM mrp_production_workcenter_line WHERE congdoan_id=%s AND workcenter_id=%s AND id !=%s '''
             %(work_order.congdoan_id.id, work_order.workcenter_id.id,work_order.id))
            res = cr.fetchone()
            if res and res[0]:
                ls_time_end_proced_end = res[0] or False
        if not ls_time_state_fist and not ls_time_end_proced_end:
            raise osv.except_osv(unicode('Error', 'utf8'), unicode('Please enter dates Scheduled Date of stage (%s).', 'utf8')%(work_order.congdoan_id.code))
        if not ls_time_end_proced_end and work_order.date_planned:
            ls_time_end_proced_end = work_order.date_planned
        if not ls_time_state_fist and ls_time_end_proced_end:
            ls_time_start = ls_time_end_proced_end
        if not ls_time_end_proced_end and ls_time_state_fist:
            ls_time_start = ls_time_state_fist
        if ls_time_end_proced_end and ls_time_state_fist and (ls_time_state_fist < ls_time_end_proced_end):
            ls_time_start = ls_time_end_proced_end
        if ls_time_end_proced_end and ls_time_state_fist and (ls_time_state_fist > ls_time_end_proced_end):
            ls_time_start = ls_time_state_fist
        return ls_time_start

    def calculate_endtime(self, cr, uid, work_order, ls_StartDate, adc_processhours):
        ldc_time_ready = 30  # work_order.kieu_chuanbi_may.sophut_chuanbi or 0
        ldc_sum_tume_proced = (adc_processhours * 60) + ldc_time_ready
        adc_processhours = ldc_sum_tume_proced / 60
        as_starttime = datetime.strptime(ls_StartDate, DEFAULT_SERVER_DATETIME_FORMAT)
        ls_EndTime = as_starttime + timedelta(minutes=ldc_sum_tume_proced)
        ls_EndTime = ls_EndTime.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return ls_EndTime, adc_processhours
    
    def calculate_processtime(self, cr, uid, work_order):
        ldc_ProcessHour = ProcessHour = 0
        production = self.pool.get('mrp.production')
        bom_stage = self.pool.get('mrp.bom.stage.line')
        if work_order:
            production_stage_id = work_order.congdoan_id.id or False
            production_id = work_order.production_id.id or False
            product_qty = work_order.product_qty or 0
            if production_id and production_stage_id:
                production_obj = production.browse(cr, uid, production_id)
                bom_id = production_obj.bom_id.id or False
                bom_stage_id = bom_stage.search(cr, uid, [('bom_id','=',bom_id),('production_stage_id','=',production_stage_id)])
                if bom_stage_id:
                    bom_stage_obj = bom_stage.browse(cr, uid, bom_stage_id[0])
                    cycle_nbr = bom_stage_obj.cycle_nbr or 0
                    hour_nbr = bom_stage_obj.hour_nbr or 0
                    ProcessHour = cycle_nbr * hour_nbr or 0
            ldc_ProcessHour = product_qty * ProcessHour or 0
        return ldc_ProcessHour
    
    def _compute_planned_workcenter(self, cr, uid, ids, context=None, mini=False):
        global is_preStartTime
        is_preStartTime = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        total_hours = 0.0
        for production in self.browse(cr, uid, ids):
            for work_order in production.workcenter_lines:
                ls_StartDate = self.calculate_starttime(cr, uid, work_order)
                is_preStartTime = ls_StartDate
                if not ls_StartDate:
                    ls_StartDate = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                ldc_ProcessHours = self.calculate_processtime(cr, uid, work_order)
                ls_EndDate, ldc_ProcessHours = self.calculate_endtime(cr, uid, work_order, ls_StartDate, ldc_ProcessHours)
                cr.execute('''
                    UPDATE mrp_production_workcenter_line
                    SET date_planned='%s', date_planned_end='%s', hour=%s
                    WHERE id=%s
                ''' % (ls_StartDate, ls_EndDate, ldc_ProcessHours, work_order.id))
                total_hours += ldc_ProcessHours
            
            cr.execute('''
                UPDATE mrp_production
                SET hour_total=%s
                WHERE id=%s
                ''' % (total_hours, production.id))
        return True
    
    def compute_speculate_production(self, cr, uid, production, list_operation_code={}):
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        workcenter_obj = self.pool.get('mrp.workcenter')
        
        total_product_line = {}
        priority = 0
        for bom_line in production.bom_stage_replace_lines:
            total_qty = 0.0
            for material in bom_line.bom_stage_material_line:
                state_product_lines = {}
                priority += 5
                if not  total_product_line.get(material.product_id, False):
                    total_product_line.update({material.product_id:{'sequence': material.sequence,'name': material.product_id.name,
                            'product_id': material.product_id.id or False,'product_uom': material.product_uom.id or False, 'product_qty': 0.0}})  
                            
                product_qty = production.product_qty * material.product_qty or 0.0

                state_product_lines.update({material.product_id:{'sequence': material.sequence, 'product_id': material.product_id.id,'product_uom':material.product_uom.id, 'product_qty': product_qty}})
                total_product_line[material.product_id]['product_qty'] += product_qty
                
            product_lines = []
            for key, state_product_line_vals in state_product_lines.items():
                product_lines.append((0, 0, state_product_line_vals))
            semi_product = bom_line.bom_stage_output_line and bom_line.bom_stage_output_line[0] or False
            if not semi_product:
                error = "Information about Semi – finished produce products is invalid./n/Please review the norms ( %s ) on Schedule Product ." % (str(production.bom_id.code))
                raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
            workcenter_ids = workcenter_obj.search(cr, uid, [('production_stage_id', '=', bom_line.production_stage_id.id)])
            workcenter_line_vals = {'name': list_operation_code.get(bom_line.production_stage_id.id, '/'),'congdoan_id': bom_line.production_stage_id.id, 
                'sequence': bom_line.seq, 'workcenter_id': workcenter_ids and workcenter_ids[0] or False, 'priority': priority, 
                'cycle': False, 'hour': False, 'production_id': production.id, 'location_src_id': production.location_src_id.id or False,
                'location_dest_id': production.location_dest_id.id or False,  'product_id': semi_product.product_id.id or False,
                'product_qty': total_qty, 'product_uom': semi_product.product_uom.id or False, 'product_lines': product_lines}
            workcenter_line_obj.create(cr, uid, workcenter_line_vals)
        
        for key, prod_line_vals in total_product_line.items():
            prod_line_vals.update({'production_id': production.id})
            prod_line_obj.create(cr, uid, prod_line_vals)
            
        return True
    
    def compute_norms_produced(self, cr, uid, production):
        for bom_state in production.bom_stage_replace_lines:
            for semi_product in bom_state.bom_stage_output_line:
                operation_finished = False
                if semi_product.product_id.id == production.product_id.id:
                    operation_finished = True
                sql = ''' SELECT sum(mbsml.product_qty) product_qty FROM mrp_bom_stage_line mbsl inner join mrp_bom_stage_material_line mbsml
                     on mbsml.bom_stage_line_id = mbsl.id  WHERE mbsml.bom_stage_line_id = %s
                ''' % (semi_product.bom_stage_line_id.id)
                cr.execute(sql)
                result = cr.dictfetchall()
                material_qty = result and result[0] and result[0]['product_qty'] or 1
                product_qty = production.product_qty / material_qty
                cr.execute(''' UPDATE mrp_production_workcenter_line SET product_id=%s, product_uom=%s, product_qty=%s, operation_finished=%s
                    WHERE production_id=%sAND workcenter_id in (select id from mrp_workcenter where congdoan_id=%s)
                ''' %(semi_product.product_id.id, semi_product.product_uom.id, product_qty, operation_finished,
                     production.id, bom_state.production_stage_id.id))
                cr.execute('''UPDATE mrp_production_product_line  SET product_uom=%s, product_qty=%s WHERE production_id=%s AND product_id=%s
                ''' %(semi_product.product_uom.id, product_qty, production.id, semi_product.product_id.id))
        return True
    
    def action_compute(self, cr, uid, ids, properties=None, context=None):
        return self._action_compute_lines(cr, uid, ids, properties=properties, context=context)
    
    def _action_compute_lines(self, cr, uid, ids, properties=None, context=None):
        prod_line_pool = self.pool.get('mrp.production.product.line')
        workcenter_line_pool = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids):
            list_operation_code = {}
            prod_line_pool.unlink(cr, SUPERUSER_ID, [line.id for line in production.product_lines], context=context)
            if production.workcenter_lines:
                workcenter_line_pool.unlink(cr, SUPERUSER_ID, [line.id for line in production.workcenter_lines], context=context)
            if production.bom_id:
                if not production.bom_stage_replace_lines:
                    self.button_load_mrp(cr, uid, production.id,context=context)
                self.compute_speculate_production(cr, uid, production, list_operation_code=list_operation_code)
                production.refresh()
                self.compute_norms_produced(cr, uid, production)
                cr.execute('commit;')
        return True
    
    def action_planned(self, cr, uid, ids, context=None):
        for production in self.browse(cr, uid, ids):
            self._compute_planned_workcenter(cr, uid, ids, context=NameError)
        return True
    
    def check_work_order(self, cr, uid, production, context=None):
        for work_order in production.workcenter_lines:
            if work_order.state not in ('cancel', 'draft'): 
                raise osv.except_osv(unicode('Error', 'utf8'), unicode('Unable to cancel MO.\n\t You must first cancel related Work Orders', 'utf8'))
            return True
    
    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        move_pool = self.pool.get('stock.move')
        proc_pool = self.pool.get('procurement.order')
        workcenter_line_pool = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids, context=context):
            self.check_work_order(cr, uid, production, context=context)
            for work_order in production.workcenter_lines:
                workcenter_line_pool.action_cancel(cr, uid, work_order.id)
            if production.move_created_ids2:
                move_pool.action_cancel(cr, uid, [x.id for x in production.move_created_ids2])
            if production.move_created_ids:
                move_pool.action_cancel(cr, uid, [x.id for x in production.move_created_ids])
            procs = proc_pool.search(cr, uid, [('move_dest_id', 'in', [x.id for x in production.move_lines])], context=context)
            if procs:
                proc_pool.cancel(cr, uid, procs, context=context)
            move_pool.action_cancel(cr, uid, [x.id for x in production.move_lines])
        self.write(cr, uid, ids, {'state': 'cancel'})
        # Put related procurements in exception
        proc_pool = self.pool.get("procurement.order")
        procs = proc_pool.search(cr, uid, [('production_id', 'in', ids)], context=context)
        if procs:
            proc_pool.message_post(cr, uid, procs, body=_('Manufacturing Order cancelled.'), context=context)
            proc_pool.write(cr, uid, procs, {'state': 'exception'}, context=context)
        return True
