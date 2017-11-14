# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################

from osv import fields, osv
import decimal_precision as dp
from tools.translate import _
import tools

class salesteam_sales_target_report(osv.osv_memory):
    _name = "salesteam.sales.target.report"
    _columns = {
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
    
    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'salesteam.sales.target.report'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'salesteam_sales_target_report', 'datas': datas}

salesteam_sales_target_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
