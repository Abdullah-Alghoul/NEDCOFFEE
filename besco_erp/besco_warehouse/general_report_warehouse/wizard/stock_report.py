# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

from datetime import date, datetime
from dateutil import relativedelta
import json
import time
import sets

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models, fields as new_fields
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
import logging
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)
# 
 
class stock_balancesheet_report(osv.osv_memory):
    _name = "stock.balancesheet.report"
    
    def _get_default_shop(self, cr, uid, context=None):
        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        shop_ids = self.pool.get('sale.shop').search(cr, uid, [('company_id','=',company_id)], context=context)
        if not shop_ids:
            raise osv.except_osv(_('Error!'), _('There is no default shop for the current user\'s company!'))
        return shop_ids[0]
    
    _columns = {
        'short_by':fields.selection([
            (1 , 'By Category'),
            (2 , 'By Product')], 'Group By',required=True),
        'date_start':fields.date('Date Start',required=True),
        'date_end':fields.date('Date End',required=True),
        'categ_ids': fields.many2many('product.category', 'balancesheet_category_rel', 'balanceshe_id', 'categ_id', 'Categories',domain=[('type','<>','view')]),
        'product_ids': fields.many2many('product.product', 'balancesheet_product_rel', 'balanceshe_id', 'product_id', 'Products'),
        'location_id':fields.many2one('stock.location','Location',domain=[('usage','<>','view')]),
     }
    _defaults = {
        'date_start':time.strftime('%Y-%m-01'),
#         'date_end':time.strftime('%Y-%m-01 00:00:00'),
        'short_by':1,
        }
    
    
    def stock_report(self, cr, uid, ids, context=None): 
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'stock.balancesheet.report'
        datas['form'] = self.read(cr, uid, ids)[0]
        short_by = datas['form'] and datas['form']['short_by']
        if short_by and short_by==1:
            report_name = 'stock_balancesheet_categ_report'
        else:
            report_name = 'stock_balancesheet_product_report'
            
        return {'type': 'ir.actions.report.xml', 'report_name': report_name , 'datas': datas}
     
stock_balancesheet_report()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
