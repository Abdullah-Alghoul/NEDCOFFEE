# -*- coding: utf-8 -*-
from datetime import datetime

import openerp
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID, api, models
import openerp.addons.decimal_precision as dp
from openerp.addons.procurement import procurement
from openerp.exceptions import UserError
from lxml import etree

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
#     
#     def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
#         if context is None:
#             context = {}
#         res = super(stock_picking,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
#            
#         if view_type == 'form':
#             doc = etree.XML(res['arch'])
#             for node in doc.xpath("//field[@name='request_materials_id']"):
#                 node.set('attrs', "{'invisible': [('picking_type_code','not in',('production_out'))]}")
#                 #node.set('attrs', "{'required': [('picking_type_code','in',('production_out'))]}")
#              
#             xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res