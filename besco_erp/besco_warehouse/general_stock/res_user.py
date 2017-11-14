# -*- coding: utf-8 -*-
import openerp
from openerp import tools, api
from openerp.osv import osv, fields
from openerp.osv.expression import get_unaccent_wrapper
from openerp.tools.translate import _
from openerp.exceptions import UserError

from openerp.addons.general_base import amount_to_text_vn
from openerp.addons.general_base import amount_to_text_en

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class res_users(osv.Model):
    _inherit = "res.users"
    
    def _default_warehouse(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context)
        res = self.pool.get('stock.warehouse').search(cr, uid, [('company_id', '=', user.company_id.id)], limit=1, context=context)
        return res and res[0] or False
    
    _columns = {
        'current_warehouse_id': fields.many2one('stock.warehouse', 'Current Warehouse', required=True),
        'supply_warehouse_ids': fields.many2many('stock.warehouse', 'stock_warehouse_supply_rel', 'user_id', 'wid','Supply Warehouses'),
        'warehouse_ids':fields.many2many('stock.warehouse', 'stock_warehouse_users_rel', 'user_id', 'wid', 'Allow Warehouses'),
            }
    
    _defaults = {'current_warehouse_id': _default_warehouse}
        
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
