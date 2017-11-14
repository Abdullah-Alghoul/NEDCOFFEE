# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
import tools
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class weekly_sales_report(osv.osv_memory):
    _name = "weekly.sales.report"
    _columns = {
        'sale_team': fields.many2one("crm.case.section", 'Sale Team', required=True),
        'salesman_id': fields.many2one('res.users', 'Sales Man', required=False),
        'salesman_ids': fields.many2many('res.users', 'weekly_sales_report_user', 'wizard_id', 'user_id', 'Sales Man', domain="[('context_section_id','=',sale_team)]", required=True),
        'from_date': fields.date('From Date', required=True),
        'to_date': fields.date('To Date', required=True),
    }
    
    _defaults = {
        'from_date': fields.date.context_today,
    }
    
    def _check_date(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        check_ids = []
        for data in self.browse(cr, uid, ids, context=context):
            if data.from_date > data.to_date:
                return False
        return True
    
    _constraints = [
        (_check_date, 'From Date must be smaller than To Date', []),

    ]
    
    def onchange_sale_team(self, cr, uid, ids, sale_team, context=None):
        value = {}
        dom = {}
#        if not sale_team:
#            return {}
#        sales_team_pool = self.pool.get('crm.case.section')
#        salesman_ids = [x.id  for x in sales_team_pool.browse(cr, uid, sale_team).member_ids]
#        dom.update({'salesman_id': [('id','in',salesman_ids)]})
#        value.update({'salesman_id':salesman_ids and salesman_ids[0] or False})
        value.update({'salesman_ids':[]})
        return {'value': value, 'domain': dom}
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'weekly.sales.report'
        datas['form'] = self.read(cr, uid, ids)[0]
        if datas['form']['to_date']:
            datas['form']['to_date'] = (datetime.strptime(datas['form']['to_date'], DEFAULT_SERVER_DATE_FORMAT) + relativedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)  
        return {'type': 'ir.actions.report.xml', 'report_name': 'weekly_sales_report', 'datas': datas}

weekly_sales_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
