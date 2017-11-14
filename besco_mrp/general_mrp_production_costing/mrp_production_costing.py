# -*- coding: utf-8 -*-
from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp.tools import float_compare
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp

class mrp_periodical_production_costing(osv.osv):
    _name= 'mrp.periodical.production.costing'
    _description = 'Periodical Production Costing'
    
    _columns={
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'warehouse_id':fields.many2one('stock.warehouse','Warehouse', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'production_order_ids': fields.many2many('mrp.production', 'mo_periodical_production_costing_rel', 'periodical_costing_id', 'production_id', 'Production orders', required=False),
        
        #Thanh: Related Production Order Allocation
        'mo_cost_collection_lines': fields.one2many('mrp.production.order.cost.collection', 'periodical_costing_id', 'Production Orders', readonly=True),
        
        #Thanh: Group Factory Overhead Control
        'periodical_overhead_lines': fields.one2many('periodical.overhead', 'periodical_costing_id', 'Overhead Details'),
        
        'state': fields.selection([
            ('draft','Draft'),
            ('posted','Posted'),
            ('cancel','Cancelled'),
            ],'Status', select=True, readonly=True),
    }
    
    _defaults = {
         'state':'draft',
    }
    
    def compute_cost(self, cr, uid, ids, context=None):
        periodical_overhead_obj = self.pool.get('periodical.overhead')
        mo_cost_collection_obj = self.pool.get('mrp.production.order.cost.collection')
        account_config_ids = self.pool.get('mrp.account.config').search(cr, uid, [])
        if not len(account_config_ids):
            raise osv.except_osv(_('Configuration Error!'), _('Please define MRP Costing Configuration!'))
        account_config = self.pool.get('mrp.account.config').browse(cr, uid, account_config_ids[0])
        for this in self.browse(cr, uid, ids):
            #Thanh: Calculate Overheads
            cr.execute('''
                UPDATE mrp_production_order_cost_collection
                SET periodical_costing_id=%s
                WHERE period_id=%s AND warehouse_id=%s
                '''%(this.id, this.period_id.id, this.warehouse_id.id))
            
            for oh_type in ['indirect_material', 'indirect_labour', 
                            'factory_utilities', 'factory_depreciation', 
                            'other_indirect']:
                periodical_overhead_ids = periodical_overhead_obj.search(cr, uid, [('type', '=', oh_type),
                                                                                   ('periodical_costing_id', '=', this.id)])
                if not len(periodical_overhead_ids):
                    vals = {'type': oh_type,
                            'periodical_costing_id': this.id}
                    periodical_overhead_new_id = periodical_overhead_obj.create(cr, uid, vals)
                else:
                    periodical_overhead_new_id = periodical_overhead_ids[0]
                periodical_overhead_obj.calculate_overhead(cr, uid, [periodical_overhead_new_id], account_config, this.period_id)
            
            #Thanh: Generate MO Cost Collection
            
            #Kiet add MO theo ngay
            date_start = this.period_id.date_start
            date_stop = this.period_id.date_stop
            production_ids =[]
            sql ='''
                SELECT * FROM
                    mrp_production 
                    where date_finished between '%s' and '%s'
                    and state = 'done'
            '''%(date_start,date_stop)
            cr.execute(sql)
            production_ids = [x[0] for x in cr.fetchall()]
            self.write(cr,uid,[this.id],{'production_order_ids':[[6,0,production_ids]]})
            new_mo_cost_collection_ids = []
#             cr.execute('''
#                 SELECT production_id
#                 FROM mo_periodical_production_costing_rel
#                 WHERE production_id not in (select production_id from mrp_production_order_cost_collection where periodical_costing_id=%s)
#             '''%(this.id))
            #production_order_ids = [x[0] for x in cr.fetchall()]
            for mo_id in production_ids:
                vals = {
                        'period_id': this.period_id.id,
                        'warehouse_id': this.warehouse_id.id,
                        'periodical_costing_id': this.id,
                        'production_id': mo_id}
                
                new_mo_cost_collection_ids.append(mo_cost_collection_obj.create(cr, uid, vals))
            if len(new_mo_cost_collection_ids):
                mo_cost_collection_obj.compute_cost(cr, uid, new_mo_cost_collection_ids)
                
            ## Tinh add
            for over_head in this.mo_cost_collection_lines:
                sql ='''
                    DELETE FROM mo_overhead_absorbed WHERE COST_COLLECTION_ID = %s
                '''%(over_head.id)
                cr.execute(sql)
                    
            for over_head in this.periodical_overhead_lines:
                if over_head.allocation_type =='direct_material':
                    total = 0
                    sql='''
                        SELECT mpoc.id, sum(mo_material.product_qty* mo_material.price_unit) nvl,
                            (SELECT sum(mo_material.product_qty* mo_material.price_unit)
                                FROM mo_direct_material_collection mo_material 
                                    join mo_direct_cost_collection mp_dir on mp_dir.id = mo_material.material_id
                                    join mrp_production_order_cost_collection mpoc on mpoc.id = mp_dir.cost_collection_id
                            WHERE periodical_costing_id = %s) as sum_nvl         
                            FROM mo_direct_material_collection mo_material 
                                join mo_direct_cost_collection mp_dir on mp_dir.id = mo_material.material_id
                                join mrp_production_order_cost_collection mpoc on mpoc.id = mp_dir.cost_collection_id
                        WHERE periodical_costing_id = %s
                        GROUP BY mpoc.id'''%(this.id,this.id)
                    cr.execute(sql)
                    for material in cr.dictfetchall():
                        if material['sum_nvl'] == 0:
                            total = 0
                        else:
                            total = material['nvl']/material['sum_nvl'] or 0.0
                        var ={
                              'cost_collection_id':material['id'],
                              'absorbed_type': over_head.allocation_type,
                              'type':over_head.type,
                              'periodical_amount':over_head.balance or 0,
                              'absorbed_amount': over_head.balance * total
                              }
                        self.pool.get('mo.overhead.absorbed').create(cr,uid,var)
                if over_head.allocation_type =='direct_labour':
                    hour = 0
                    sql='''
                        SELECT direct.cost_collection_id,sum(labor.hours) hours,
                            (SELECT sum(hours) total_hours FROM mrp_periodical_production_costing per 
                            join mrp_production_order_cost_collection orders on orders.periodical_costing_id = per.id 
                            join mo_direct_cost_collection direct on direct.cost_collection_id = orders.id
                            join mo_direct_labor_collection labor on labor.labor_id = direct.id
                            WHERE per.id = %s
                            group by per.id) sum_hours
                        FROM mo_direct_labor_collection labor 
                        JOIN mo_direct_cost_collection direct on labor.labor_id = direct.id
                        JOIN mrp_production_order_cost_collection orders on direct.cost_collection_id = orders.id
                        where orders.periodical_costing_id = %s
                        GROUP BY direct.cost_collection_id
                        '''%(this.id,this.id)
                    cr.execute(sql)
                    for hours in cr.dictfetchall():
                        if hours['sum_hours'] == 0:
                            hour = 0
                        else:
                            hour = hours['hours']/hours['sum_hours'] or 0.0
                        var ={
                              'cost_collection_id':hours['cost_collection_id'],
                              'absorbed_type': over_head.allocation_type,
                              'type':over_head.type,
                              'periodical_amount':over_head.balance or 0,
                              'absorbed_amount': over_head.balance * hour
                              }
                        self.pool.get('mo.overhead.absorbed').create(cr,uid,var)
                        
                if over_head.allocation_type =='direct_machine':
                    hour = 0
                    sql ='''
                        SELECT direct.cost_collection_id,sum(marchine.hours) hours ,
                            (SELECT sum(hours) total_hours FROM mrp_periodical_production_costing per 
                                join mrp_production_order_cost_collection orders on orders.periodical_costing_id = per.id 
                                join mo_direct_cost_collection direct on direct.cost_collection_id = orders.id
                                join mo_direct_marchine marchine on marchine.marchine_id = direct.id
                                WHERE per.id = %s
                                group by per.id) sum_hours
                        FROM mo_direct_marchine marchine 
                        JOIN mo_direct_cost_collection direct on marchine.marchine_id = direct.id
                        JOIN mrp_production_order_cost_collection orders on direct.cost_collection_id = orders.id
                        where orders.periodical_costing_id = %s
                        GROUP BY direct.cost_collection_id
                    '''%(this.id,this.id)
                    cr.execute(sql)
                    for hours in cr.dictfetchall():
                        if hours['sum_hours'] == 0:
                            hour = 0
                        else:
                            hour = hours['hours']/hours['sum_hours'] or 0.0
                        var ={
                              'cost_collection_id':hours['cost_collection_id'],
                              'absorbed_type': over_head.allocation_type,
                              'type':over_head.type,
                              'periodical_amount':over_head.balance or 0,
                              'absorbed_amount': over_head.balance * hour
                              }
                        self.pool.get('mo.overhead.absorbed').create(cr,uid,var)
            for over_head in this.mo_cost_collection_lines:
                self.compute_mo_cost(cr, uid, ids, this.mo_cost_collection_lines)
        return True
    
    def compute_mo_cost (self,cr,uid,ids,mo_cost_collection_lines):
        for line in mo_cost_collection_lines:
            absorbed_amount = 0
            sql='''
                SELECT sum(absorbed_amount) absorbed_amount 
                FROM mo_overhead_absorbed 
                WHERE  cost_collection_id = %s
            '''%(line.id)
            cr.execute(sql)
            for i in cr.dictfetchall():
                absorbed_amount = i['absorbed_amount'] or 0.0
            for direct_cost in line.direct_cost_lines:
                price_unit = 0
                sql='''
                    SELECT sum(price_unit)  price_unit
                    FROM mo_direct_material_collection
                    WHERE material_id =%s
                '''%(direct_cost.id)
                cr.execute(sql)
                for i in cr.dictfetchall():
                    price_unit = i['price_unit'] or 0.0
                if direct_cost.produced_qty:
                    price = (price_unit +absorbed_amount)/direct_cost.produced_qty
                else:
                    price = 0
                # update lai price thành phẩm or bán thành phẩm
                sql='''
                    UPDATE stock_move set
                      price_unit = %s
                    WHERE  id in 
                        (SELECT sm.id
                            FROM stock_picking sp join stock_move sm on sp.id = sm.picking_id
                            WHERE sp.production_id = %s 
                            AND sp.result_id is not null
                            AND sp.state not in ('draft','cancel')
                            AND sm.product_id = %s)
                '''%(price,direct_cost.cost_collection_id.production_id.id,direct_cost.product_id.id)
                cr.execute(sql)
                self.pool.get('mo.direct.cost.collection').write(cr,uid,direct_cost.id,{'price_unit':price,'price_subtotal':price_unit +absorbed_amount})
    def post(self, cr, uid, ids, context=None):
        return True

mrp_periodical_production_costing()

class periodical_overhead(osv.osv):
    _name= 'periodical.overhead'
    def _compute_balance(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0.0
            if line.type == 'indirect_material':
                for balance_line in line.indirect_material_lines:
                    res[line.id] += balance_line.balance
            if line.type == 'indirect_labour':
                for balance_line in line.indirect_labour_lines:
                    res[line.id] += balance_line.balance
            if line.type == 'factory_utilities':
                for balance_line in line.factory_utilities_lines:
                    res[line.id] += balance_line.balance
            if line.type == 'factory_depreciation':
                for balance_line in line.factory_depreciation_lines:
                    res[line.id] += balance_line.balance
            if line.type == 'other_indirect':
                for balance_line in line.other_indirect_lines:
                    res[line.id] += balance_line.balance
        return res
    
    _columns={
        'periodical_costing_id': fields.many2one('mrp.periodical.production.costing', 'Related Periodical Costing', required=False),
        
        'type': fields.selection([
          ('indirect_material','Indirect Material'),
          ('indirect_labour','Indirect Labour'),
          ('factory_utilities','Factory Utilities'),
          ('factory_depreciation','Factory Depreciation'),
          ('other_indirect','Other Indirect'),
          ],'Overhead', select=True, required=True, readonly=True),
              
        'allocation_type': fields.selection([
          ('direct_material','Direct Material'),
          ('direct_labour','Direct Labour Hours'),
          ('direct_machine','Direct Machine Hours'),
          ],'Allocation Type', select=True, required=True),
        
        'balance': fields.function(_compute_balance, string='Balance', digits_compute= dp.get_precision('Account')),
#         'balance': fields.float('Balance', digits_compute=dp.get_precision('Account')),
        
        'indirect_material_lines': fields.one2many('periodical.overhead.balance', 'periodical_costing_im_id', 'Indirect Materials'),
        'indirect_labour_lines': fields.one2many('periodical.overhead.balance', 'periodical_costing_il_id', 'Indirect Labours'),
        'factory_utilities_lines': fields.one2many('periodical.overhead.balance', 'periodical_costing_fu_id', 'Factory Utilities'),
        'factory_depreciation_lines': fields.one2many('periodical.overhead.balance', 'periodical_costing_fd_id', 'Factory Depreciation'),
        'other_indirect_lines': fields.one2many('periodical.overhead.balance', 'periodical_costing_oi_id', 'Other Indirect'),
    }
    
    _defaults = {
         'allocation_type': 'direct_material',
    }
    
    def calculate_overhead(self, cr, uid, ids, account_config, period, context=None):
        account_obj = self.pool.get('account.account')
        for this in self.browse(cr, uid, ids):
            #Thanh: IM
            if account_config.indirect_material_account_ids:
                indirect_material_account_ids = [x.id for x in account_config.indirect_material_account_ids]
                indirect_material_account_ids = account_obj.search(cr, uid, [('id','child_of',indirect_material_account_ids)])
                
                cr.execute('''
                DELETE
                FROM periodical_overhead_balance
                WHERE periodical_costing_im_id=%s
                '''%(this.id))
                
                cr.execute('''
                INSERT INTO periodical_overhead_balance(ref, date, account_id, debit, credit, balance, periodical_costing_im_id)
                SELECT am.ref , aml.date, aml.account_id, aml.debit, aml.credit, (aml.debit - aml.credit) as balance, %s
                    FROM account_move_line aml join account_move am on aml.move_id=am.id and am.state='posted'
                    WHERE am.date >= '%s' AND am.date <= '%s'
                        AND aml.account_id in (%s)
                '''%(this.id,
                     period.date_start, period.date_stop,
                     ','.join(map(str,indirect_material_account_ids))))
                
#                 cr.execute('''
#                 UPDATE periodical_overhead
#                 SET balance = (select sum(balance) from periodical_overhead_balance where periodical_costing_im_id=%s)
#                 WHERE id=%s
#                 '''%(this.id, this.id))

            #Thanh: IL
            if account_config.indirect_labour_account_ids:
                indirect_labour_account_ids = [x.id for x in account_config.indirect_labour_account_ids]
                indirect_labour_account_ids = account_obj.search(cr, uid, [('id','child_of',indirect_labour_account_ids)])
                
                cr.execute('''
                DELETE
                FROM periodical_overhead_balance
                WHERE periodical_costing_il_id=%s
                '''%(this.id))
                
                cr.execute('''
                INSERT INTO periodical_overhead_balance(ref, date, account_id, debit, credit, balance, periodical_costing_il_id)
                SELECT am.ref , aml.date, aml.account_id, aml.debit, aml.credit, (aml.debit - aml.credit) as balance, %s
                    FROM account_move_line aml join account_move am on aml.move_id=am.id and am.state='posted'
                    WHERE am.date >= '%s' AND am.date <= '%s'
                        AND aml.account_id in (%s)
                '''%(this.id,
                     period.date_start, period.date_stop,
                     ','.join(map(str,indirect_labour_account_ids))))
            
            #Thanh: FU
            if account_config.factory_utilities_account_ids:
                factory_utilities_account_ids = [x.id for x in account_config.factory_utilities_account_ids]
                factory_utilities_account_ids = account_obj.search(cr, uid, [('id','child_of',factory_utilities_account_ids)])
                
                cr.execute('''
                DELETE
                FROM periodical_overhead_balance
                WHERE periodical_costing_fu_id=%s
                '''%(this.id))
                
                cr.execute('''
                INSERT INTO periodical_overhead_balance(ref, date, account_id, debit, credit, balance, periodical_costing_fu_id)
                SELECT am.ref , aml.date, aml.account_id, aml.debit, aml.credit, (aml.debit - aml.credit) as balance, %s
                    FROM account_move_line aml join account_move am on aml.move_id=am.id and am.state='posted'
                    WHERE am.date >= '%s' AND am.date <= '%s'
                        AND aml.account_id in (%s)
                '''%(this.id,
                     period.date_start, period.date_stop,
                     ','.join(map(str,factory_utilities_account_ids))))
            
            #Thanh: FD
            if account_config.factory_depreciation_account_ids:
                factory_depreciation_account_ids = [x.id for x in account_config.factory_depreciation_account_ids]
                factory_depreciation_account_ids = account_obj.search(cr, uid, [('id','child_of',factory_depreciation_account_ids)])
                
                cr.execute('''
                DELETE
                FROM periodical_overhead_balance
                WHERE periodical_costing_fd_id=%s
                '''%(this.id))
                
                cr.execute('''
                INSERT INTO periodical_overhead_balance(ref, date, account_id, debit, credit, balance, periodical_costing_fd_id)
                SELECT am.ref , aml.date, aml.account_id, aml.debit, aml.credit, (aml.debit - aml.credit) as balance, %s
                    FROM account_move_line aml join account_move am on aml.move_id=am.id and am.state='posted'
                    WHERE am.date >= '%s' AND am.date <= '%s'
                        AND aml.account_id in (%s)
                '''%(this.id,
                     period.date_start, period.date_stop,
                     ','.join(map(str,factory_depreciation_account_ids))))
            
            #Thanh: OI
            if account_config.other_indirect_account_ids:
                other_indirect_account_ids = [x.id for x in account_config.other_indirect_account_ids]
                other_indirect_account_ids = account_obj.search(cr, uid, [('id','child_of',other_indirect_account_ids)])
                
                cr.execute('''
                DELETE
                FROM periodical_overhead_balance
                WHERE periodical_costing_oi_id=%s
                '''%(this.id))
                
                cr.execute('''
                INSERT INTO periodical_overhead_balance(ref, date, account_id, debit, credit, balance, periodical_costing_oi_id)
                SELECT am.ref , aml.date, aml.account_id, aml.debit, aml.credit, (aml.debit - aml.credit) as balance, %s
                    FROM account_move_line aml join account_move am on aml.move_id=am.id and am.state='posted'
                    WHERE am.date >= '%s' AND am.date <= '%s'
                        AND aml.account_id in (%s)
                '''%(this.id,
                     period.date_start, period.date_stop,
                     ','.join(map(str,other_indirect_account_ids))))
                
#                 cr.execute('''
#                 UPDATE periodical_overhead
#                 SET balance = (select sum(balance) from periodical_overhead_balance where periodical_costing_oi_id=%s)
#                 WHERE id=%s
#                 '''%(this.id, this.id))

        return True
    
    def compute_cost(self, cr, uid, ids, account_config, period, context=None):
        account_config_ids = self.pool.get('mrp.account.config').search(cr, uid, [])
        if not len(account_config_ids):
            raise osv.except_osv(_('Configuration Error!'), _('Please define MRP Costing Configuration!'))
        account_config = self.pool.get('mrp.account.config').browse(cr, uid, account_config_ids[0])
        for this in self.browse(cr, uid, ids):
            self.calculate_overhead(cr, uid, ids, account_config, this.period_id, context)
        return True
    
periodical_overhead()

class periodical_overhead_balance(osv.osv):
    _name= 'periodical.overhead.balance'
    
    _columns={
          'ref': fields.char('Ref', size=64, required=False),
          'date': fields.date('Date', required=True),
          'account_id': fields.many2one('account.account', 'Account', required=True),
          'debit': fields.float('Debit', digits_compute=dp.get_precision('Account')),
          'credit': fields.float('Credit', digits_compute=dp.get_precision('Account')),
          'balance': fields.float('Balance', digits_compute=dp.get_precision('Account')),
          
          'periodical_costing_im_id': fields.many2one('periodical.overhead', 'Related Periodical Costing'),
          'periodical_costing_il_id': fields.many2one('periodical.overhead', 'Related Periodical Costing'),
          'periodical_costing_fu_id': fields.many2one('periodical.overhead', 'Related Periodical Costing'),
          'periodical_costing_fd_id': fields.many2one('periodical.overhead', 'Related Periodical Costing'),
          'periodical_costing_oi_id': fields.many2one('periodical.overhead', 'Related Periodical Costing'),
    }
    
periodical_overhead_balance()

class mrp_production_order_cost_collection(osv.osv):
    _name= 'mrp.production.order.cost.collection'
    _description = 'Production Order Cost Collection'
    
    
    def _get_total(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                'total_labor_hours': 0.0,
                'total_machine_hours': 0.0,
                'total_material': 0.0
            }
            for labors in line.direct_cost_lines:
                for hour in labors.labor_ids:
                    res[line.id]['total_labor_hours'] += hour.hours
                
                for hour in labors.marchine_ids:
                    res[line.id]['total_machine_hours'] += hour.hours
                
                for value in labors.material_ids:
                    res[line.id]['total_labor_hours'] += value.product_qty * value.price_unit
        return res
    
    _columns={
        'production_id': fields.many2one('mrp.production', 'Production order', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'company_id': fields.related('production_id', 'company_id', type='many2one', relation='res.company', string='Company', readonly=True),
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'warehouse_id':fields.many2one('stock.warehouse','Warehouse', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        
        #Thanh: 
        'direct_cost_lines': fields.one2many('mo.direct.cost.collection', 'cost_collection_id', 'Direct costs', readonly=True),
        'overhead_absorbed_lines': fields.one2many('mo.overhead.absorbed', 'cost_collection_id', 'OH absorbed', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('posted','Posted'),
            ('cancel','Cancelled'),
            ],'Status', select=True, readonly=True),
        
        'periodical_costing_id': fields.many2one('mrp.periodical.production.costing', 'Related Periodical Costing'),
        'total_labor_hours':fields.function(_get_total, string='Total Labor Hours', type='float',readonly=True, multi='all'),
        'total_machine_hours':fields.function(_get_total, string='Total machine Hours', type='float',readonly=True,multi='all'),
        'total_material':fields.function(_get_total, string='Total material', type='float',readonly=True,multi='all'),
    }
    
    _defaults = {
         'state':'draft',
    }
    def add_marchine(self,cr,uid,marchine_id,production_id,workcenter_id,congdoan_id,date_start,date_stop):
        sql ='''
            SELECT result.resource_id,sum(result.hours) hours
                FROM mrp_production_workcenter_line workcenter join mrp_operation_result result on result.operation_id = workcenter.id
                WHERE workcenter.production_id = %(production_id)s
                    AND workcenter.congdoan_id = %(congdoan_id)s
                    AND date(timezone('UTC',result.end_date::timestamp)) between '%(date_start)s' and '%(date_stop)s'
                    AND result.state not in ('cancel','draft')
                    AND workcenter.state not in ('cancel','draft')
                GROUP BY workcenter.id,result.resource_id,workcenter.congdoan_id
        '''%({
          'date_start': date_start,
          'date_stop':date_stop,
          'production_id': production_id,
          'congdoan_id':congdoan_id,
          'operation_id':workcenter_id
          }) 
        cr.execute(sql)
        for marchine in cr.dictfetchall():
            var ={
                'marchine_id':marchine_id,
                'workcenter_id':marchine['resource_id'],
                'hours':marchine['hours'],
              } 
            self.pool.get('mo.direct.marchine').create(cr,uid,var)
        return True
        
    def add_nvl(self,cr,uid,material_id,production_id,workcenter_id,congdoan_id,date_start,date_stop):
        tile = 0
        sql='''
            SELECT  mor.production_id,mor.operation_id,mor.congdoan_id,mpw.product_qty qty_csx, sum(mor.product_qty) qt_sx
                FROM mrp_operation_result mor 
                    JOIN mrp_production_workcenter_line mpw on mor.operation_id = mpw.id
                WHERE  mor.production_id = %(production_id)s
                       and mor.operation_id = %(operation_id)s
                       and mor.congdoan_id = %(congdoan_id)s
                       and mor.state not in ('cancel','draft')
                       and mpw.state not in ('cancel','draft')
                       and date(timezone('UTC',mor.end_date::timestamp)) between '%(date_start)s' and '%(date_stop)s'
                GROUP BY  mor.operation_id, mor.congdoan_id,mor.production_id,mpw.product_qty
                ORDER BY mor.production_id,mor.operation_id,mor.congdoan_id
        '''%({
          'date_start': date_start,
          'date_stop':date_stop,
          'production_id': production_id,
          'congdoan_id':congdoan_id,
          'operation_id':workcenter_id
          }) 
        cr.execute(sql)
        for material in cr.dictfetchall():
            # Lấy cái sản xuất thực tế chia cho kế hoạch sản xuất
            tile = material['qty_csx'] and  material['qt_sx'] / material['qty_csx'] or 0 
            
        sql='''
            SELECT production_id,operation_id,product_id,product_uom,sum(received_qty) received_qty
                FROM mrp_production_workcenter_product_consumed
                WHERE 
                       production_id = %(production_id)s
                       and operation_id = %(operation_id)s
                GROUP BY production_id,operation_id,product_id,product_uom
        '''%({
          'date_start': date_start,
          'date_stop':date_stop,
          'production_id': production_id,
          'operation_id':workcenter_id
          }) 
        cr.execute(sql)
        for material in cr.dictfetchall():
            price_unit = 0
            sql='''
                SELECT sum(primary_qty *price_unit) /sum(primary_qty) price_unit
                FROM mrp_production_move_ids mrp join stock_move sm on sm.id = mrp.move_id 
                where mrp.production_id = %s
                    and product_id = %s
                GROUP BY mrp.production_id ,product_id,product_uom
            '''%(production_id,material['product_id'])
            cr.execute(sql)
            for price in cr.dictfetchall():
                price_unit = price['price_unit'] or 0.0
                
            var ={
                'material_id':material_id,
                'product_id':material['product_id'],
                'uom_id':material['product_uom'],
                'product_qty':material['received_qty'] * tile,
                'price_unit':price_unit or 0.0
              } 
            self.pool.get('mo.direct.material.collection').create(cr,uid,var)
        return True
    
    
    def add_labor_hours(self,cr,uid,labor_id,production_id,date_start,date_stop,congdoan_id,workcenter_id):
        sql='''
            SELECT    labour.emp_id emp,sum(labour.hour_nbr) sum_hours
                    FROM mrp_operation_result res join direct_labour labour on labour.result_id = res.id
                    WHERE production_id = %(production_id)s
                        and operation_id = %(operation_id)s
                        and congdoan_id = %(congdoan_id)s
                        and state not in ('cancel','draft')
                        and date(timezone('UTC',end_date::timestamp)) between '%(date_start)s' and '%(date_stop)s'
                    GROUP BY production_id,operation_id,congdoan_id,labour.emp_id
          '''%({
          'production_id': production_id,
          'date_start': date_start,
          'date_stop':date_stop,
          'congdoan_id':congdoan_id,
          'operation_id':workcenter_id
          }) 
        cr.execute(sql)
        for hours in cr.dictfetchall():
            var={
                    'labor_id':labor_id,
                    'emp_id':hours['emp'],
                    'hours':hours['sum_hours']
                        }
            self.pool.get('mo.direct.labor.collection').create(cr,uid,var)
    
        return True    
        
    def compute_cost(self, cr, uid, ids, context=None):
        uom_obj = self.pool.get('product.uom')
        
        ## delete table material Labor Marchine
        for this in self.browse(cr,uid,ids):
            for line in this.direct_cost_lines:
                sql ='''
                    DELETE FROM mo_direct_material_collection where material_id = %s
                '''%(line.id)
                cr.execute(sql)
                sql ='''
                    DELETE FROM mo_direct_labor_collection where labor_id = %s
                '''%(line.id)
                cr.execute(sql)
                sql='''
                    DELETE FROM mo_direct_marchine where marchine_id = %s
                '''%(line.id)
                cr.execute(sql)
            sql='''
                DELETE FROM mo_direct_cost_collection where cost_collection_id = %s
            '''%(this.id)
            cr.execute(sql)
                
        for this in self.browse(cr, uid, ids):
            for workcenter_line in this.production_id.workcenter_lines:
                #Thanh: Get produced qty in period
                produced_qty = 0.0
                sql = '''
                SELECT stm.product_id, stm.product_uom, sum(stm.product_qty)
                FROM stock_move as stm join stock_picking as sp on sp.id=stm.picking_id 
                    join mrp_operation_result mor on mor.id=sp.result_id and mor.operation_id=%s and mor.state='done'
                WHERE stm.state='done' 
                    AND date(timezone('UTC',stm.date::timestamp)) >= '%s'
                    AND date(timezone('UTC',stm.date::timestamp)) <= '%s'
                GROUP BY stm.product_id, stm.product_uom
                '''%(
                     workcenter_line.id,  
                     this.period_id.date_start, this.period_id.date_stop)
                cr.execute(sql)
                res = cr.fetchall()
                for res_line in res:
                    if workcenter_line.product_uom.id != res_line[1]:
                        if workcenter_line.product_id.__hasattr__('uom_ids'):
                            produced_qty += uom_obj._compute_qty(cr, uid, res_line[1], res_line[2], workcenter_line.product_uom.id, product_id=workcenter_line.product_id.id)
                        else:
                            produced_qty += uom_obj._compute_qty(cr, uid, res_line[1], res_line[2], workcenter_line.product_uom.id)
                    else:
                        produced_qty += res_line[2]
                var ={
                      'cost_collection_id':this.id,
                      'congdoan_id':workcenter_line.congdoan_id.id,
                      'workcenter_id':workcenter_line.workcenter_id.id,
                      'product_id':workcenter_line.product_id.id,
                      'product_uom_id':workcenter_line.product_uom.id, 
                      'planned_qty':workcenter_line.product_qty,
                      'produced_qty':produced_qty,
                      'state':workcenter_line.state
                      }
                new_id = self.pool.get('mo.direct.cost.collection').create(cr,uid,var)
                
                
                self.add_labor_hours(cr, uid, new_id, this.production_id.id,
                     this.period_id.date_start, this.period_id.date_stop, workcenter_line.congdoan_id.id, workcenter_line.id)
                
                self.add_nvl(cr, uid, new_id, this.production_id.id, workcenter_line.id, workcenter_line.congdoan_id.id, 
                                this.period_id.date_start, this.period_id.date_stop)
                
                self.add_marchine(cr, uid, new_id, this.production_id.id, workcenter_line.id,workcenter_line.congdoan_id.id, 
                                this.period_id.date_start, this.period_id.date_stop)
        return True
   
    def post(self, cr, uid, ids, context=None):
        return True
    
mrp_production_order_cost_collection()

class mo_direct_cost_collection(osv.osv):
    _name= 'mo.direct.cost.collection'
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.price_unit * line.produced_qty
        return res
    
    _columns={
        'cost_collection_id': fields.many2one('mrp.production.order.cost.collection', 'MO Cost collection', required=True, ondelete='cascade'),
        'congdoan_id': fields.many2one('mrp.production.stage', 'Production Stage', required=False),
        'workcenter_id': fields.many2one('mrp.workcenter', 'Work Center', required=False),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_uom_id': fields.many2one('product.uom', 'UoM', required=True),
        'planned_qty': fields.float('Planned Qty', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'produced_qty': fields.float('Produced Qty', digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'price_unit': fields.float('Unit Price', digits_compute= dp.get_precision('Product Price')),
        'price_subtotal': fields.float('Price Subtotal'),
        
        
        'state': fields.selection([('draft','Draft'),
                                   ('cancel','Cancelled'),
                                   ('pause','Pending'),
                                   ('startworking', 'In Progress'),
                                   ('done','Finished')],'Status', readonly=True),
        'material_ids':fields.one2many('mo.direct.material.collection','material_id','Direct Materials'),
        'labor_ids':fields.one2many('mo.direct.labor.collection','labor_id','Direct Labor Hours'),
        'marchine_ids':fields.one2many('mo.direct.marchine','marchine_id','Labor'),
    }
    
    _defaults = {
    }
    
mo_direct_cost_collection()

class mo_direct_marchine(osv.osv):
    _name= 'mo.direct.marchine'
    _columns={
        'marchine_id':fields.many2one('mo.direct.cost.collection','Labor direct',ondelete='cascade'),
        'workcenter_id':fields.many2one('mrp.workcenter','Máy móc'),
        'hours':fields.float('Giờ'),
          }
mo_direct_marchine()

class mo_direct_labor_collection(osv.osv):
    _name= 'mo.direct.labor.collection'
    _columns={
        'labor_id':fields.many2one('mo.direct.cost.collection','Labor direct',ondelete='cascade'),
        'emp_id':fields.many2one('hr.employee','Nhân viên'),
        'hours':fields.float('Giờ'),
          }
mo_direct_labor_collection()

class mo_direct_material_collection(osv.osv):
    _name= 'mo.direct.material.collection'
    _columns={
        'material_id':fields.many2one('mo.direct.cost.collection','Material direct',ondelete='cascade'),
        'product_id':fields.many2one('product.product','Product'),
        'uom_id':fields.many2one('product.uom','UoM'),
        'product_qty':fields.float('Qty'),
        'price_unit':fields.float('Price unit'),
      }
mo_direct_material_collection()

class mo_overhead_absorbed(osv.osv):
    _name= 'mo.overhead.absorbed'
    _columns={
        'cost_collection_id': fields.many2one('mrp.production.order.cost.collection', 'MO Cost collection', required=True, ondelete='cascade'),
        'absorbed_type': fields.selection([
              ('direct_material','Direct Material'),
              ('direct_labour','Direct Labour Hours'),
              ('direct_machine','Direct Machine Hours'),
              ],'Absorbed Type', select=True, required=True),
              
        'type': fields.selection([
          ('indirect_material','Indirect Material'),
          ('indirect_labour','Indirect Labour'),
          ('factory_utilities','Factory Utilities'),
          ('factory_depreciation','Factory Depreciation'),
          ('other_indirect','Other Indirect'),
          ],'Overhead', select=True, required=True, readonly=True),
              
        'periodical_amount': fields.float('Periodical Amount', digits_compute=dp.get_precision('Account')),
        'absorbed_amount': fields.float('Absorbed Amount', digits_compute=dp.get_precision('Account')),
    }
    
    _defaults = {
    }
    
mo_overhead_absorbed()