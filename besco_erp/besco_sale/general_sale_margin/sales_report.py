##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from osv import fields, osv
from openerp.tools.translate import _

class sales_fiscalyear(osv.osv):
    _name = "sales.fiscalyear"
    _description = "Sales Fiscal Year"
    
    def _get_total_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for this in self.browse(cr, uid, ids, context=context):
            res[this.id] = {
                'total_minimum_line': 0.0,
                'total_actual_line': 0.0,
                'percentage': 0.0,
            }
            for line in this.period_ids:
                res[this.id]['total_minimum_line'] += line.total_minimum_line
                res[this.id]['total_actual_line'] += line.total_actual_line
            res[this.id]['percentage'] = res[this.id]['total_minimum_line'] and round((res[this.id]['total_actual_line'] * 100 / res[this.id]['total_minimum_line']),3) or 0.0
        return res
    
    _columns = {
        'name': fields.char('Sales Fiscal Year', size=64, required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('sales.period', 'fiscalyear_id', 'Periods'),
        'state': fields.selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True),
        'sale_team': fields.many2many("crm.case.section", 'fiscalyear_salesteam', 'fiscalyear_id', 'salesteam_id', 'Sale Teams', required=False),
        
        'total_minimum_line': fields.function(_get_total_line, string='Total Min Sales', digits=(16,2), store = False, readonly=True, multi='fiscalyear'),
        'total_actual_line': fields.function(_get_total_line, string='Total Actual Sales', digits=(16,2), store = False, readonly=True, multi='fiscalyear'),
        'percentage': fields.function(_get_total_line, string='Percentage (%)', digits=(16,2), store = False, readonly=True, multi='fiscalyear'),
    }
    _defaults = {
        'state': 'draft',
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
    }
    _order = "date_start, id"

#    def name_get(self, cr, uid, ids, context=None):
#        if not ids:
#            return []
#        reads = self.browse(cr, uid, ids, context=context)
#        res = []
#        for record in reads:
#            name = record.name
#            if record.sale_team:
#                name = name + ' - ' + record.sale_team.name
#            res.append((record['id'], name))
#        return res
    
    def _check_duration(self, cr, uid, ids, context=None):
        obj_fy = self.browse(cr, uid, ids[0], context=context)
        if obj_fy.date_stop < obj_fy.date_start:
            return False
#        res = self.search(cr, uid, [('date_stop','>=',obj_fy.date_start),('date_start','<=',obj_fy.date_stop),('id','<>',obj_fy.id)])
        cr.execute('''
            SELECT * FROM fiscalyear_salesteam 
            WHERE fiscalyear_id in (SELECT id FROM sales_fiscalyear WHERE date_start <= '%s' AND date_stop >= '%s' AND id <> %s)
            AND salesteam_id in (SELECT salesteam_id FROM fiscalyear_salesteam WHERE fiscalyear_id = %s)
        '''%(obj_fy.date_stop,obj_fy.date_start,obj_fy.id,obj_fy.id))
        res = cr.fetchall()
        if res:
            raise osv.except_osv(_('Invalid Data!'), _("This Fiscal Year has been exist!\n It's duplicated for some Sales Teams!"))
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe start date of a sales fiscal year must precede its end date.', ['date_start','date_stop'])
    ]
    
#    def update_salesteam(self, cr, uid, ids, context=None):
#        period_line_obj = self.pool.get('sales.period.line')
#        for fy in self.browse(cr, uid, ids, context=context):
#            salesman_ids = []
#            for sale_team in fy.sale_team:
#                salesman_ids += [[sale_team,x.id] for x in sale_team.member_ids]
#            if salesman_ids == []:
#                 raise osv.except_osv(_('Error!'), _('There are no Sales team.\n Or there are no Salesman defined on Sales team'))
#            for perido in fy.period_ids:
#                for period_line in period.sales_period_line:
#                    for salesman_id in salesman_ids:
#                        if period_line.salesman_id.id == salesman_id[1]:
#                            if period_line.sale_team and period_line.sale_team.id == salesman_id[0]:
#                                continue
#                            
#        return True
    
    def create_period3(self, cr, uid, ids, context=None):
        return self.create_period(cr, uid, ids, context, 3)

    def create_period(self, cr, uid, ids, context=None, interval=1):
        period_obj = self.pool.get('sales.period')
        period_line_obj = self.pool.get('sales.period.line')
        for fy in self.browse(cr, uid, ids, context=context):
            salesman_ids = []
            for sale_team in fy.sale_team:
                salesman_ids += [[sale_team.id,x.id] for x in sale_team.member_ids]
            if salesman_ids == []:
                 raise osv.except_osv(_('Error!'), _('There are no Sales team.\n Or there are no Salesman defined on Sales team'))
            period_ids = []
            ds = datetime.strptime(fy.date_start, '%Y-%m-%d')
#            new_id = period_obj.create(cr, uid, {
#                    'name':  ds.strftime('%m/%Y'),
#                    'date_start': ds,
#                    'date_stop': ds,
#                    'fiscalyear_id': fy.id,
#                })
#            period_ids.append(new_id)
            while ds.strftime('%Y-%m-%d') < fy.date_stop:
                de = ds + relativedelta(months=interval, days=-1)

                if de.strftime('%Y-%m-%d') > fy.date_stop:
                    de = datetime.strptime(fy.date_stop, '%Y-%m-%d')

                new_id = period_obj.create(cr, uid, {
                    'name': de.strftime('%m/%Y'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': fy.id,
                })
                ds = ds + relativedelta(months=interval)
                period_ids.append(new_id)
            
            #Assign Sales Man to Period Line
            for period_id in period_ids:
                for salesman_id in salesman_ids:
                    period_line_obj.create(cr, uid, {
                            'salesman_id': salesman_id[1],
                            'sale_team': salesman_id[0],
                            'minimum_sales': 0.0,
                            'sales_period_id': period_id,
                        })
        return True

#    def find(self, cr, uid, dt=None, exception=True, context=None):
#        res = self.finds(cr, uid, dt, exception, context=context)
#        return res and res[0] or False
#
#    def finds(self, cr, uid, dt=None, exception=True, context=None):
#        if context is None: context = {}
#        if not dt:
#            dt = fields.date.context_today(self,cr,uid,context=context)
#        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
#        if context.get('company_id', False):
#            company_id = context['company_id']
#        else:
#            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
#        args.append(('company_id', '=', company_id))
#        ids = self.search(cr, uid, args, context=context)
#        if not ids:
#            if exception:
#                raise osv.except_osv(_('Error!'), _('There is no fiscal year defined for this date.\nPlease create one from the configuration of the accounting menu.'))
#            else:
#                return []
#        return ids
    
    def write(self, cr, uid, ids, vals, context=None):
        for line in self.browse(cr, uid, ids):
            if vals.get('sale_team',False) and line.period_ids:
                del(vals['sale_team'])
        return super(sales_fiscalyear, self).write(cr, uid, ids, vals, context)
    
sales_fiscalyear()

class sales_period(osv.osv):
    _name = "sales.period"
    _description = "Sales period"
    
    def _get_total_line(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for this in self.browse(cr, uid, ids, context=context):
            res[this.id] = {
                'total_minimum_line': 0.0,
                'total_actual_line': 0.0,
                'percentage': 0.0,
            }
            for line in this.sales_period_line:
                res[this.id]['total_minimum_line'] += line.minimum_sales
                res[this.id]['total_actual_line'] += line.actual_sales
            res[this.id]['percentage'] = res[this.id]['total_minimum_line'] and round((res[this.id]['total_actual_line'] * 100 / res[this.id]['total_minimum_line']),3) or 0.0
        return res
    
    _columns = {
        'name': fields.char('Period Name', size=64, required=True),
        'date_start': fields.date('Start of Period', required=True),# states={'done':[('readonly',True)]}),
        'date_stop': fields.date('End of Period', required=True),# states={'done':[('readonly',True)]}),
        'fiscalyear_id': fields.many2one('sales.fiscalyear', 'Sales Fiscal Year', required=True,ondelete='cascade'),# states={'done':[('readonly',True)]}),
#        'state': fields.selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True,
#                                  help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.'),
        'company_id': fields.related('fiscalyear_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'sales_period_line': fields.one2many('sales.period.line', 'sales_period_id', 'Period Lines'),
        'total_minimum_line': fields.function(_get_total_line, string='Total Minimum Sales', digits=(16,2), store = False, readonly=True, multi='period'),
        'total_actual_line': fields.function(_get_total_line, string='Total Actual Sales', digits=(16,2), store = False, readonly=True, multi='period'),
        'percentage': fields.function(_get_total_line, string='Percentage (%)', digits=(16,2), store = False, readonly=True, multi='period'),
    }
    _defaults = {
#        'state': 'draft',
    }
    _order = "date_start"
    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'The name of the period must be unique per company!'),
    ]

    def _check_duration(self,cr,uid,ids,context=None):
        obj_period = self.browse(cr, uid, ids[0], context=context)
        if obj_period.date_stop < obj_period.date_start:
            return False
        return True

    def _check_year_limit(self,cr,uid,ids,context=None):
        for obj_period in self.browse(cr, uid, ids, context=context):
            
            if obj_period.fiscalyear_id.date_stop < obj_period.date_stop or \
               obj_period.fiscalyear_id.date_stop < obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_start or \
               obj_period.fiscalyear_id.date_start > obj_period.date_stop:
                return False
            
            pids = self.search(cr, uid, [('date_stop','>=',obj_period.date_start),('date_start','<=',obj_period.date_stop),('id','<>',obj_period.id)])
            if pids:
                return False
        return True

    _constraints = [
        (_check_duration, 'Error!\nThe duration of the Period(s) is/are invalid.', ['date_stop']),
        (_check_year_limit, 'Error!\nThe period is invalid. Either some periods are overlapping or the period\'s dates are not matching the scope of the fiscal year.', ['date_stop'])
    ]
    
#    def find(self, cr, uid, dt=None, context=None):
#        if context is None: context = {}
#        if not dt:
#            dt = fields.date.context_today(self,cr,uid,context=context)
##CHECKME: shouldn't we check the state of the period?
#        args = [('date_start', '<=' ,dt), ('date_stop', '>=', dt)]
#        if context.get('company_id', False):
#            args.append(('company_id', '=', context['company_id']))
#        else:
#            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
#            args.append(('company_id', '=', company_id))
#        result = []
#        if context.get('account_period_prefer_normal'):
#            # look for non-special periods first, and fallback to all if no result is found
#            result = self.search(cr, uid, args + [('special', '=', False)], context=context)
#        if not result:
#            result = self.search(cr, uid, args, context=context)
#        if not result:
#            raise osv.except_osv(_('Error !'), _('There is no period defined for this date: %s.\nPlease create one.')%dt)
#        return result

#    def action_draft(self, cr, uid, ids, *args):
#        mode = 'draft'
#        cr.execute('update sales_period set state=%s where id in %s', (mode, tuple(ids),))
#        return True

sales_period()

class sales_period_line(osv.osv):
    _name = "sales.period.line"
    _order = "sale_team,sales_period_id"
    
    def _get_actual_sales(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        sale_order_obj = self.pool.get("sale.order")
        res = {}
        for this in self.browse(cr, uid, ids, context=context):
            res[this.id] = {
                'actual_sales': 0.0,
                'percentage': 0.0,
            }
            actual_sales = 0.0
            so_ids = sale_order_obj.search(cr, uid, [('date_order','>=',this.sales_period_id.date_start),('date_order','<=',this.sales_period_id.date_stop),('user_id','=', this.salesman_id.id),('state','not in',('draft','sent','cancel'))])
            for so in sale_order_obj.browse(cr, uid, so_ids):
                so_cur = so.pricelist_id.currency_id
                if so_cur.id == so.company_id.currency_id.id:
                    actual_sales += so.amount_total
                else:
                    actual_sales += cur_obj.compute(cr, uid, so_cur.id, so.company_id.currency_id.id, so.amount_total, context=context)
            res[this.id]['actual_sales'] = actual_sales
            res[this.id]['percentage'] = this.minimum_sales and round((actual_sales * 100 / this.minimum_sales),3) or 0.0
        return res
    
    _columns = {
        'name': fields.char('Description', size=128, required=False),
        'sale_team': fields.many2one('crm.case.section', 'Sale Team', required=True, ),
        'salesman_id': fields.many2one('res.users', 'Sales Man', required=True, domain="[sale_team and ('context_section_id','=',sale_team) or ('id','=',0)]"),
        'minimum_sales': fields.float('Min Sales', digits=(16,2), required=True),
        'actual_sales': fields.function(_get_actual_sales, string='Actual Sales', digits=(16,2), store = False, readonly=True, multi='sales'),
        'percentage': fields.function(_get_actual_sales, string='Percentage (%)', digits=(16,2), store = False, readonly=True, multi='sales'),
        'sales_period_id': fields.many2one('sales.period', 'Sales Period', required=True, ondelete='cascade')
    }
    
    _defaults = {
    }
    
    _sql_constraints = [
        ('salesman_period_uniq', 'unique(salesman_id, sales_period_id)', 'The Salesman must be unique per period!'),
    ]
    
sales_period_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
