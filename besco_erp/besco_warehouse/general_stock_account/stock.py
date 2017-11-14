# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################

from openerp.osv import fields, osv, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime, timedelta
import time
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class average_cost_history(osv.osv):
    _name = "average.cost.history"
    _columns = {
        'period_id': fields.many2one('account.period', 'Period', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        #'journal_id': fields.many2one('account.journal', 'Account Journal', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'detail_history_ids': fields.one2many('average.cost.detail.history', 'cost_history_id', 'Detail History', readonly=True),
        'move_id': fields.many2one('account.move', 'Account Move'),
        'company_id': fields.related('period_id', 'company_id', type='many2one', relation='res.company', string='Company', readonly=True),
        
        'state': fields.selection([
            ('draft','Draft'),
            ('done','Done'),
            ('cancel','Cancelled'),
            ],'Status', select=True, readonly=True, track_visibility='onchange'),
    }
    
    _defaults = {
         'state':'draft',
    }
    
    _sql_constraints = [
        ('name_uniq', 'unique(period_id, company_id)', 'Order Reference must be unique per Company!'),
    ]
    _order = 'period_id desc'
    
    def cron_average_cost(self, cr, uid, context=None):
        context = context or {}
        flag = False
        try:
            sql='''
                SELECT id, date_start, date_stop, company_id
                FROM account_period
                WHERE date_start >=
                    (SELECT max(date_start)
                    FROM account_period
                    WHERE date_start <=
                        (SELECT min(date(timezone('UTC',sm.date))) date
                        FROM stock_move sm
                        WHERE state ='done'
                        and (costed is null  or costed = false)))
                AND date_stop <= (select date_stop from account_period where current_date between date_start and date_stop)
            '''
            cr.execute(sql)
            periods = cr.dictfetchall()
            for period in periods:
                average_ids = self.search(cr,uid,[('period_id','=',period['id'])])
                if average_ids:
                    self.compute_cost(cr, uid, average_ids, context)
                else:
                    average_id = self.pool.get('average.cost.history').create(cr,uid, {'period_id': period['id']})
                    self.compute_cost(cr, uid, [average_id], context)
        except Exception, ex:
            pass
        return True
    
            
    def compute_cost(self,cr,uid,ids,context=None):
        his_pool = self.pool.get('average.cost.detail.history')
        sql = False
        his_real_time_ids =[]
        his_periodic_ids=[]
        #if history.product_id.valuation=='real_time':
        for period in self.browse(cr, uid, ids):
            sql ='''
                SELECT distinct product_id
                FROM stock_move sm 
                WHERE 
                    (costed is null  or costed = false)
                    and sm.state ='done'
                    and date(timezone('UTC',sm.date::timestamp)) between '%s' and '%s'
                    and sm.company_id = %s
            '''%(period.period_id.date_start, period.period_id.date_stop, period.period_id.company_id.id)
            cr.execute(sql)
            for line in cr.dictfetchall():
                detail_ids = his_pool.search(cr,uid, [('cost_history_id','=',ids[0]),
                                                      ('product_id','=',line['product_id'])])
                if not detail_ids:
                    vals ={
                       'cost_history_id':ids and ids[0],
                       'product_id': line['product_id'],
                       }
                    his_pool.create(cr,uid,vals)
                
                #Thanh: Pass product_id and date to compute average cost
                his_pool.compute_cost_periodic(cr, uid, line['product_id'], period.period_id.date_start, period.period_id.date_stop, period.period_id.company_id.id)

#         for period in self.browse(cr, uid, ids):
#             for line in period.detail_history_ids:
#                 his_periodic_ids.append(line.id)
#             if his_periodic_ids:
#                 his_pool.compute_cost_periodic(cr,uid,his_periodic_ids)
#                 if line.product_id.valuation == 'real_time':
#                     his_real_time_ids.append(line.id)
#                 else:
#                     his_periodic_ids.append(line.id)
#             if his_periodic_ids:
#                 his_pool.compute_cost_periodic(cr,uid,his_periodic_ids)
#             if his_real_time_ids:
#                 his_pool.compute_cost_real_time(cr,uid,his_real_time_ids)
                
        return True
    
    #Thanh: Generate or update Stock Journal Entry for Stock valuation and COGS
    def post(self, cr, uid, ids, context=None):
        context = context or {}
        his_pool = self.pool.get('average.cost.detail.history')
        cost_history = self.browse(cr,uid,ids[0])
        his_ids = [x.id for x in cost_history.detail_history_ids]
        his_pool.post(cr,uid,his_ids)
        self.write(cr,uid,ids,{'state':'done'})
        return True
    
average_cost_history()

class average_cost_detail_history(osv.osv):
    _name = "average.cost.detail.history"
    
    def post(self, cr, uid, ids,  context=None):
        context = context or {}
        move_obj = self.pool.get('stock.move')
        for detail_history in self.browse(cr,uid,ids):
            for move in detail_history.move_ids:
                if move.stock_journal_id and move.stock_journal_id and move.stock_journal_id.source_type !='in':
                    move_obj._create_product_valuation_moves(cr, uid, move, context=context)
#             if move.stock_journal_id and move.stock_journal_id and move.stock_journal_id.source_type =='phys_adj':
#                 context.update({'internal':'internal'})
        return True
    
    def compute_cost_periodic(self, cr, uid, product_id, date_start, date_stop, company_id):
        #Thanh: Compute average periodical cost
        if not product_id:
            return True
        
        product = self.pool.get('product.product').browse(cr, uid, product_id)
        
        #Thanh: Step 1: Get current qty and cost from previous period (before date_start)
        sql='''
                SELECT cur_cost, cur_qty
                FROM
                    stock_move
                WHERE 
                    product_id = %s
                    and state = 'done'
                    and costed = true
                    and date(timezone('UTC',date)) < '%s'
                    and company_id = %s
                ORDER BY date desc
                LIMIT 1
            '''%(product_id, date_start, company_id)
        cr.execute(sql)
        previous = cr.fetchone()
        previous_cost = previous and previous[0] or 0.0  # Gia von ky truoc (dc luu o lastes stock_move)
        previous_qty = previous and previous[1] or 0.0   # Số lượng tồn kho ky truoc (dc luu o lastes stock_move)
        
        if previous_qty > 0.0:
            #Thanh: Step 2: SUM all incoming value (except 'transit' move) in this period and previous value to compute average cost for this period
            sql='''
                SELECT sum(product_qty) qty, sum(price_unit * product_qty / coalesce(uom_conversion,1.0)) total
                FROM
                    stock_move stm 
                        join stock_location sl1 on stm.location_id = sl1.id 
                        join stock_location sl2 on stm.location_dest_id = sl2.id 
                WHERE
                    product_id = %s
                    and date(timezone('UTC',stm.date)) between '%s' and '%s'
                    and stm.state = 'done'
                    and stm.company_id = %s
                    and sl1.usage not in ('internal', 'transit')
                    and sl2.usage = 'internal'
             '''%(product_id, date_start, date_stop, company_id)
            cr.execute(sql)
            this_period = cr.fetchone()
            this_qty = this_period and this_period[0] or 0
            this_value = this_period and this_period[1] or 0
            peridical_cost = (this_qty + previous_qty) and (this_value + (previous_cost * previous_qty)) / (this_qty + previous_qty) or 0.0
            peridical_cost = peridical_cost or previous_cost
        else:
            peridical_cost = product.standard_price
        if peridical_cost <= 0.0:
            peridical_cost = product.standard_price
            
        #Update field cur_cost cho tat ca cac giao dich trong ky
        try:
            sql = '''
                UPDATE 
                    stock_move
                SET cur_cost = %s, costed = true
                WHERE product_id = %s and date(timezone('UTC',date)) between '%s' and '%s'
                and company_id=%s;
                COMMIT;
            '''%(peridical_cost, product_id, date_start, date_stop, company_id)
            cr.execute(sql)
        except Exception, ex:
            pass
        
        #kiet: Update lai fields tính cost_price 
        try:
            sql='''
                UPDATE 
                    pos_order_line
                    SET cost_price = %s, profit = price_subtotal - (%s * qty)
                WHERE product_id = %s and date(timezone('UTC',date_order)) between '%s' and '%s'
                    and %s <= price_unit
                    and company_id=%s;
                COMMIT;
            '''%(peridical_cost, peridical_cost, product_id, date_start, date_stop, peridical_cost, company_id)
            cr.execute(sql)
            
            sql='''
                UPDATE 
                    pos_order_line
                    SET cost_price = %s, profit = price_subtotal - (%s * qty)
                WHERE product_id = %s and date(timezone('UTC',date_order)) between '%s' and '%s'
                    and %s > price_unit
                    and company_id=%s;
                COMMIT;
            '''%(product.standard_price, product.standard_price, product_id, date_start, date_stop, peridical_cost, company_id)
            cr.execute(sql)
        except Exception, ex:
            pass
        
        # kiet: Update stock Quat
        try:
            sql = '''
                UPDATE stock_quant
                    SET cost = %s, inventory_value = %s * qty
                    WHERE id in(  
                        SELECT  his.quant_id 
                        FROM stock_quant sq
                            join stock_quant_move_rel his on sq.id = his.quant_id
                            join 
                            (SELECT stm.id
                                FROM
                                stock_move stm 
                                WHERE 
                                    product_id = %s and date(timezone('UTC',stm.date)) between '%s' and '%s'
                                and stm.state = 'done'
                                and costed = true
                                and company_id=%s) x on his.move_id = x.id)
            '''%(peridical_cost, peridical_cost, product_id, date_start, date_stop, company_id)
            cr.execute(sql)
        except Exception, ex:
            pass
        
        #Thanh: Step 3: Update average cost to other issue stock transactions
        #Update field price_unit from table stock_move 
        #Các giao dịch xuất kho + Chuyển kho nội bộ (trong cung warehouse hoac ngoai warehouse)
        try:
            sql = '''
                UPDATE 
                    stock_move
                SET price_unit = %s
                WHERE id in 
                    (SELECT stm.id
                        FROM
                        stock_move stm 
                            join stock_location loc1 on stm.location_id = loc1.id
                            join stock_location loc2 on stm.location_dest_id = loc2.id
                        WHERE 
                            product_id = %s and date(timezone('UTC',stm.date)) between '%s' and '%s'
                        and stm.state = 'done'
                        and ((loc1.usage = 'internal' and loc2.usage != 'internal')
                            or (loc1.usage = 'internal' and loc2.usage = 'internal'))
                        and stm.company_id=%s);
                COMMIT;
            '''%(peridical_cost, product_id, date_start, date_stop, company_id)
            cr.execute(sql)
        except Exception, ex:
            pass
        
        #Cac giao dich kiem ke  
        try:
            sql ='''
                UPDATE 
                    stock_inventory_line 
                SET freeze_cost = %s
                WHERE
                    move_id in 
                    (SELECT stm.id
                        FROM
                        stock_move stm join stock_location loc1 on stm.location_id = loc1.id
                        WHERE 
                            product_id = %s
                        and date(timezone('UTC',stm.date)) between '%s' and '%s'
                        and stm.state = 'done'
                        and stm.company_id = %s 
                        and loc1.usage = 'internal');
                COMMIT;
            '''%(peridical_cost, product_id, date_start, date_stop, company_id)
            cr.execute(sql)
            
            #Thanh: Step 4: Update the lastest stock_move with current_qty for the next period computation
            sql = '''
                UPDATE stock_move
                SET cur_qty = %s + (SELECT sum(onhand_qty)
                                FROM
                                (
                                    SELECT  case when loc1.usage not in ('internal','transit') and loc2.usage = 'internal'
                                            then stm.product_qty
                                        else
                                            case when loc1.usage = 'internal' and loc2.usage not in ('internal','transit')
                                                then -1*stm.product_qty 
                                            else 0.0 end
                                        end onhand_qty
                                    FROM
                                        stock_move stm 
                                            join stock_location loc1 on stm.location_id = loc1.id
                                            join stock_location loc2 on stm.location_dest_id = loc2.id
                                    WHERE 
                                    product_id = %s and date(timezone('UTC',stm.date)) between '%s' and '%s'
                                    and stm.state = 'done' and stm.company_id = %s
                                ) foo)
                WHERE id in (select id 
                             from stock_move 
                             where product_id = %s and date = (select date 
                                            from stock_move
                                            where
                                                product_id = %s and date(timezone('UTC',date)) between '%s' and '%s'
                                                and state = 'done' and company_id = %s
                                            order by date desc
                                            limit 1)
                            );
                COMMIT;
            '''%(previous_qty,
                 product_id, date_start, date_stop, company_id,
                 product_id,
                 product_id, date_start, date_stop, company_id)
            cr.execute(sql)
        except Exception, ex:
            pass
        return True
    
    def compute_cost_real_time(self, cr, uid, ids,context=None):
        for history in self.browse(cr, uid, ids, context=context):
            qty_previous = 0.0
            previous_value = 0.0
            average_cost =False
            if history.product_id:
                sql='''
                    SELECT cur_cost,cur_qty
                    FROM
                        stock_move
                    WHERE 
                        product_id = %s
                        and state = 'done'
                        and costed = true
                    ORDER BY date desc
                    LIMIT 1
                '''%(history.product_id.id)
                cr.execute(sql)
                previous = cr.fetchone()
                previous_value = previous and previous[0] or 0.0
                qty_previous = previous and previous[1] or 0.0
                
                sql='''
                    SELECT sm.id,(product_qty * price_unit) as total,product_qty,uom_conversion,sm.type,price_unit,product_qty
                    FROM
                        stock_move sm 
                    WHERE 
                        product_id = %s
                        and sm.state = 'done'
                        and costed != true
                    Order by timezone('UTC',sm.date),id
                '''%(history.product_id.id)
#                 '''%(history.product_id.id,history.cost_history_id.period_id.date_start,history.cost_history_id.period_id.date_stop)
                cr.execute(sql)
                res = cr.dictfetchall()
                
                current_qty = qty_previous
                current_value = previous_value
                for line in res:
                    if line['type']=='in':
                        if line['product_qty'] + current_qty != 0:
                            average_cost = (line['total'] + (qty_previous * previous_value))/(line['product_qty'] +current_qty) or 0.0
                        else:
                            average_cost = line['price_unit']
                        current_qty += line['product_qty']
                        sql ='''
                             UPDATE stock_move
                             SET cur_cost = %s,
                                 cur_qty = %s,
                                 costed = true
                             WHERE id = %s    
                        '''%(average_cost,current_qty,line['id'])
                        cr.execute(sql)
                        previous_value = average_cost or 0.0
                        qty_previous = current_qty or 0.0
                        current_value = (average_cost * current_qty) or 0.0
#                         Phat sinh bút toán kho
#                         stock_move = self.pool.get('stock.move').browse(cr,uid,line['id'])
#                         if not stock_move.valuation_move_id:
#                             move_obj._create_product_valuation_moves(cr, uid, stock_move, context=context)
#                         else:
#                             for account_move_line in stock_move.valuation_move_id.line_id:
#                                 if account_move_line.debit == 0:
#                                     sql='''
#                                         Update account_move_line set credit = %s
#                                         WHERE id = %s
#                                     '''%(average_cost,account_move_line.id)
#                                     cr.execute(sql)
#                                 else:
#                                     sql='''
#                                         Update account_move_line set debit = %s
#                                         WHERE id = %s
#                                     '''%(average_cost,account_move_line.id)
#                                     cr.execute(sql)
#                             #self.pool.get('account.move').post(cr, uid, [stock_move.valuation_move_id.id], context)
                            
                    if line['type'] in ['internal','out']:
                        if not average_cost:
                            average_cost = current_value  or 0.0
                        
                        if line['type'] == 'out':
                            #Trường hợp Xuất bán
                            current_qty -= line['product_qty']
                            sql ='''
                                UPDATE 
                                    stock_move 
                                SET price_unit = %s,
                                    cur_qty = %s,
                                    cur_cost = %s,
                                    costed = true
                                WHERE
                                    id = %s
                            '''%(average_cost * (line['uom_conversion'] or 1),current_qty,average_cost,line['id'])
                            cr.execute(sql)
                            qty_previous = current_qty
                            previous_value = average_cost
                            #Phat sinh bút toán kho
#                             stock_move = self.pool.get('stock.move').browse(cr,uid,line['id'])
#                             if not stock_move.valuation_move_id:
#                                 move_obj._create_product_valuation_moves(cr, uid, stock_move, context=context)
#                             else:
#                                 for account_move_line in stock_move.valuation_move_id.line_id:
#                                     if account_move_line.debit == 0:
#                                         sql='''
#                                             Update account_move_line set credit = %s
#                                             WHERE id = %s
#                                         '''%(average_cost,account_move_line.id)
#                                         cr.execute(sql)
#                                     else:
#                                         sql='''
#                                             Update account_move_line set debit = %s
#                                             WHERE id = %s
#                                         '''%(average_cost,account_move_line.id)
#                                         cr.execute(sql)
#                                 self.pool.get('account.move').post(cr, uid, [stock_move.valuation_move_id.id], context)
                            
                        #Trường hợp Interal
                        else:
                            sql='''
                            SELECT sl.usage lo_usage,sd.usage des_usage 
                            FROM
                                stock_move sm join stock_location sl on sm.location_id = sl.id
                                              join stock_location sd on sm.location_dest_id = sd.id
                            WHERE sm.id = %s
                            '''%(line['id'])
                            cr.execute(sql)
                            usage = cr.fetchone()
                            lo_usage = usage and usage[0] or False
                            des_usage = usage and usage[1] or False
                            # trường hợp chuyển kho nội bộ
                            if lo_usage == des_usage:
                                sql ='''
                                    UPDATE 
                                        stock_move 
                                    SET price_unit = %s,
                                        cur_qty = %s,
                                        cur_cost = %s,
                                        costed = true
                                    WHERE
                                        id = %s and ini_flag=False
                                '''%(average_cost * (line['uom_conversion'] or 1),current_qty,average_cost,line['id'])
                                cr.execute(sql)
                                qty_previous = current_qty
                                previous_value = average_cost
                            else:
                                #Trường hợp xuất điều chỉnh 
                                if des_usage != 'internal':
                                    current_qty -= line['product_qty'] or 0.0
                                    sql ='''
                                        UPDATE 
                                            stock_move 
                                        SET price_unit = %s,
                                            cur_qty = %s,
                                            cur_cost = %s,
                                            costed = true
                                        WHERE
                                            id = %s and ini_flag=False
                                    '''%(average_cost * (line['uom_conversion'] or 1),current_qty,average_cost,line['id'])
                                    cr.execute(sql)
                                    qty_previous = current_qty
                                    previous_value = average_cost
#                                     #Phat sinh bút toán kho
#                                     stock_move = self.pool.get('stock.move').browse(cr,uid,line['id'])
#                                     if not stock_move.valuation_move_id:
#                                         move_obj._create_product_valuation_moves(cr, uid, stock_move, context=context)
#                                     else:
#                                         for account_move_line in stock_move.valuation_move_id.line_id:
#                                             if account_move_line.debit == 0:
#                                                 sql='''
#                                                     Update account_move_line set credit = %s
#                                                     WHERE id = %s
#                                                 '''%(average_cost,account_move_line.id)
#                                                 cr.execute(sql)
#                                             else:
#                                                 sql='''
#                                                     Update account_move_line set debit = %s
#                                                     WHERE id = %s
#                                                 '''%(average_cost,account_move_line.id)
#                                                 cr.execute(sql)
#                                         self.pool.get('account.move').post(cr, uid, [stock_move.valuation_move_id.id], context)
                                # Trường hợp nhap điều chỉnh
                                else:
                                    current_qty += line['product_qty']
                                    cr.execute('commit;')
                                    sql ='''
                                        UPDATE 
                                            stock_move 
                                        SET price_unit = %s,
                                            cur_qty = %s,
                                            cur_cost = %s,
                                            costed = true
                                        WHERE
                                            id = %s;
                                        commit;
                                    '''%(average_cost * line['product_qty'],current_qty,average_cost,line['id'])
                                    cr.execute(sql)
                                    qty_previous = current_qty
                                    previous_value = average_cost
                                    #Phat sinh bút toán kho
#                                     stock_move = self.pool.get('stock.move').browse(cr,uid,line['id'])
#                                     if not stock_move.valuation_move_id:
#                                         move_obj._create_product_valuation_moves(cr, uid, stock_move, context=context)
#                                     else:
#                                         for account_move_line in stock_move.valuation_move_id.line_id:
#                                             if account_move_line.debit == 0:
#                                                 cr.execute('commit;')
#                                                 sql='''
#                                                     Update account_move_line set credit = %s
#                                                     WHERE id = %s;
#                                                     commit;
#                                                 '''%(average_cost,account_move_line.id)
#                                                 cr.execute(sql)
#                                             else:
#                                                 cr.execute('commit;')
#                                                 sql='''
#                                                     Update account_move_line set debit = %s
#                                                     WHERE id = %s;
#                                                     commit;
#                                                 '''%(average_cost,account_move_line.id)
#                                                 cr.execute(sql)
#                                         self.pool.get('account.move').post(cr, uid, [stock_move.valuation_move_id.id], context)
                            
                            sql ='''
                                commit;
                                
                                UPDATE 
                                    stock_inventory_line
                                SET freeze_cost = %s
                                WHERE
                                    move_id = %s;
                                commit;
                            '''%(average_cost,line['id'])
                            cr.execute(sql)
                sql='''
                    SELECT cur_cost,cur_qty
                    FROM
                        stock_move
                    WHERE 
                        product_id = %s
                        and state = 'done'
                        and costed = true
                    ORDER BY date desc
                    LIMIT 1
                    '''%(history.product_id.id)
                cr.execute(sql)
                this = cr.fetchone()
                this_cost =this and this[0] or 0.0
                sql='''
                    commit;
                    UPDATE product_template SET standard_price = %s
                        WHERE id = (SELECT pt.id FROM
                                    product_product pp inner join product_template pt on
                                    pt.id = pp.product_tmpl_id and pp.id = %s);
                    commit;
                '''%(this_cost,history.product_id.id)  
                cr.execute(sql)
                
                # Viet tip ham
                
        return True 
    
    def _average_cost(self, cr, uid, ids, name, args, context=None):
        res = {}
        for average in self.browse(cr, uid, ids, context=context):
            res[average.id] = {
                'this_cost': 0.0,
                'this_value':0.0,
                'qty_onhand':0.0,
                'qty_previous':0.0,
                'previous_value':0.0,
                'previous_cost':0.0
            }
            if average.product_id:
                sql='''
                SELECT cur_cost, cur_qty
                        FROM
                            stock_move
                        WHERE 
                            product_id = %s
                            and state = 'done'
                            and costed = true
                            and date(timezone('UTC',date)) < '%s'
                        ORDER BY date desc
                        LIMIT 1
                    '''%(average.product_id.id, average.cost_history_id.period_id.date_start)
                cr.execute(sql)
                previous = cr.fetchone()
                previous_cost = previous and previous[0] or 0.0  # Gia von ky truoc (dc luu o lastes stock_move)
                previous_qty = previous and previous[1] or 0.0   # Số lượng tồn kho ky truoc (dc luu o lastes stock_move)
        
                res[average.id]['previous_cost']= previous_cost or 0.0
                res[average.id]['previous_value']= previous_qty * previous_cost or 0.0
                res[average.id]['qty_previous']= previous_qty or 0.0
                
                sql='''
                    SELECT cur_cost, cur_qty
                    FROM
                        stock_move
                    WHERE 
                        product_id = %s
                        and state = 'done'
                        and costed = true
                        and date(timezone('UTC',date)) < '%s'
                    ORDER BY date desc
                    LIMIT 1
                '''%(average.product_id.id , average.cost_history_id.period_id.date_stop)
                cr.execute(sql)
                this = cr.fetchone()
                this_cost =this and this[0] or 0.0
                qty_this = this and this[1] or 0.0
                
                res[average.id]['this_cost'] = this_cost or 0.0
                res[average.id]['this_value'] = this_cost * qty_this or 0.0
                res[average.id]['qty_onhand'] = qty_this or 0.0
        return res
    
    def _compute_lines(self, cr, uid, ids, name, args, context=None):
        result = {}
        for average in self.browse(cr, uid, ids, context=context):
            result[average.id]= []
            if average.product_id:
                sql='''
                    SELECT id
                    FROM
                        stock_move
                    WHERE 
                        product_id = %s
                        and date(timezone('UTC',date)) between '%s' and '%s'
                        and state = 'done'
                        --and costed = true
                    Order by date,id
                '''%(average.product_id.id , average.cost_history_id.period_id.date_start,average.cost_history_id.period_id.date_stop)
                cr.execute(sql)
                move_ids = [x[0] for x in cr.fetchall()]
                result[average.id] =move_ids 
        return result
    
    
    _columns = {
        'cost_history_id':fields.many2one('average.cost.history', 'Cost History'),
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom_id': fields.related('product_id','uom_id', type="many2one", relation="product.uom", 
                                         string="UoM", store=True, readonly=True),
        
        'previous_value': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='Previous Value',
                multi='sums'),
        'previous_cost': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='Previous Cost',
                multi='sums'),
        'qty_previous': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='Previous Onhand Qty',
                multi='sums'),
                
        
        'this_cost': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='This Cost',
                multi='sums'),
        'this_value': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='This Value',
                multi='sums'),
        'qty_onhand': fields.function(_average_cost, digits_compute=dp.get_precision('Account'), string='This Onhand Qty',
                multi='sums'),
                
        'move_ids': fields.function(_compute_lines, relation='stock.move', type="many2many", string='Move'),
        'valuation':fields.related('product_id', 'valuation', type='char', string='Phương thức tính cost')
    }
    _defaults = {
    }
    
average_cost_detail_history()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _order = 'picking_id, sequence, id'
    
    _columns = {
        'cur_qty':fields.float('Cur Qty'),
        'cur_cost':fields.float('Cur Cost'),
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        if ids:
            move = self.browse(cr,uid,ids[0])
            if vals and vals.get('date',False) and vals.get('state') =='done':
                date = datetime.strptime(vals['date'], DATETIME_FORMAT) + relativedelta(hours=7)
                date = date.strftime('%Y-%m-%d') 
                
                period_ids = self.pool.get('account.period').find(cr, uid, dt=date, context=context)
                period = self.pool.get('account.period').browse(cr,uid,period_ids[0])
                if not period:
                    raise
                cr.execute('commit;')
                sql='''
                    UPDATE stock_move 
                    SET costed = false,  cur_cost =0 ,cur_qty = 0
                    WHERE id in (
                        SELECT sm.id
                            FROM stock_move sm 
                            WHERE 
                            '%s' <= timezone('UTC',sm.date)::date
                            and sm.state ='done'
                            and product_id = %s);
                '''%(period.date_start,move.product_id.id)
                cr.execute(sql)
            if vals and 'costed' in vals:
                if vals.get('date',False):
                    date = vals['date']
                else:
                    date = move.date or move.picking_id.date_done
                
                date = datetime.strptime(date, DATETIME_FORMAT) + relativedelta(hours=7)
                period_ids = self.pool.get('account.period').find(cr, uid, dt=date.strftime('%Y-%m-%d') , context=context)
                period = self.pool.get('account.period').browse(cr,uid,period_ids[0])
                if not period:
                    raise
                
                cr.execute('commit;')
                sql='''
                    UPDATE stock_move 
                    SET costed = false , cur_cost =0 ,cur_qty = 0
                    WHERE id in (
                        SELECT sm.id
                            FROM stock_move sm
                            WHERE 
                            '%s' <= timezone('UTC',sm.date)::date
                            and sm.state ='done'
                            and product_id = %s);
                    commit;
                '''%(period.date_start,move.product_id.id)
                cr.execute(sql)
        return super(stock_move, self).write(cr, uid,ids, vals, context)
    
stock_move()    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
