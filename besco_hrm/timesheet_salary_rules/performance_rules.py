# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID


class expro_hr_timesheet_salary_performance_rules(osv.osv):
    _name = 'hr.timesheet.salary.performance.rules'
    
    _columns = {
        'name': fields.char('Calculation', required=True),
        'update_date': fields.date('Update Date'),
        'start_date': fields.date('Date From'),
        'end_date': fields.date('Date To'),
        'levels_ids': fields.one2many('hr.timesheet.salary.performance.rules.levels', 'performance_rules_id', string='List Levels'),
        'state_ids':  fields.many2many('hr.work.location', 'salary_performance_rules_res_cou_state_rel', 'salary_performance_rules_id', 'state_id', string='State'),
        'job_id':  fields.many2one('hr.job', 'Job', required=True),
    }
    
    _defaults = {
        'update_date': (date.today() + timedelta(days=28)).strftime(DEFAULT_SERVER_DATE_FORMAT),
    }

class expro_hr_sales_supports_levels(osv.osv):
    _name = 'hr.timesheet.salary.performance.rules.levels'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        if context.get('level_hr', False) and context.get('calculations_id'):
            arg = ('calculations_id', '=', context.get('calculations_id'))
            args.append(arg)
        return super(expro_hr_sales_supports_levels, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    _columns = {
        'name': fields.char('Name', required=True),
        'operator': fields.selection([
                                ('=', '='),
                                ('!=', '!='),
                                ('>', '>'),
                                ('>=', '>='),
                                ('<', '<'),
                                ('<=', '<='),
                                ('between', 'between')                                                      
                                ], string='Operator', default='between', required=True),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'uom': fields.many2one('product.uom', 'UoM', required=True),
        'value_from': fields.integer('Value From', required=True),
        'value_to': fields.integer('Value To'),
        'apply': fields.boolean('Apply', required=True),
        'performance_rules_id': fields.many2one('hr.timesheet.salary.performance.rules', 'Performance Rules'),
        'levels_lines_ids': fields.one2many('hr.timesheet.salary.performance.rules.levels.lines', 'level_id', string='Lines'),
    }
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM for changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            d = {'uom': [('category_id', '=', prod.uom_id.category_id.id)]}
            v = {'uom': prod.uom_id.id}
            return {'value': v, 'domain': d}
        return {'domain': {'uom': []}}
    
class expro_hr_sales_supports_levels_lines(osv.osv):
    _name = 'hr.timesheet.salary.performance.rules.levels.lines'
    _columns = {
        'area_id': fields.many2one('res.area.define', 'Area'),
        'state_id': fields.many2one('res.country.state', 'State'),
        'value': fields.float('Value'),
        'level_id': fields.many2one('hr.timesheet.salary.performance.rules.levels', 'Levels'),
    }
