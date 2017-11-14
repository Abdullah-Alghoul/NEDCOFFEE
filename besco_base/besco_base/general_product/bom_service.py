# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

from openerp.tools.float_utils import float_round, float_compare
from openerp.exceptions import UserError, AccessError

import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class product_bom_service_line(osv.osv):
    _name = 'product.bom.service.line'
    _order = "sequence"
    _rec_name = "product_id"
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_uom': fields.many2one('product.uom', 'UoM', required=True),
         
        'date_start': fields.date('Valid From', help="Validity of component. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of component. Keep empty if it's always valid."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying."),
        'tolerance' : fields.float('Tolerance'),
        'bom_id': fields.many2one('product.bom.service', 'Product BOM', ondelete='cascade', select=True, required=True),
    }
    
    def product_id_change(self, cr, uid, ids, product_id):
        product_obj = self.pool.get('product.product')
        if not product_id:
            return {'value': {'product_qty': 0.0, 'product_uom': False}}
        
        product = product_obj.browse(cr, uid, product_id)
        return {'value': {'product_qty': 0.0, 'product_uom': product.uom_id.id}}

class product_bom_service(osv.osv):
    _name = 'product.bom.service'
    _description = 'Product BOM Service'
    
    _columns = {
        'sequence' :fields.integer('Sequence'),
        'name': fields.char('Name'),
        'code': fields.char('Reference', size=16),
        'product_qty': fields.float('Product Quantity', required=True, digits_compute=dp.get_precision('Product Unit of Measure')),
        'product_tmpl_id': fields.many2one('product.template', 'Product', domain="[('type', '=', 'service')]", required=True),
        'product_id': fields.many2one('product.product', 'Product Variant',
            domain="['&', ('product_tmpl_id','=',product_tmpl_id), ('type','=', 'service')]",
            help="If a product variant is defined the BOM is available only for this product."),
        'bom_line_ids': fields.one2many('product.bom.service.line', 'bom_id', 'BoM Lines', copy=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control"),
        'date_start': fields.date('Valid From', help="Validity of this BoM. Keep empty if it's always valid."),
        'date_stop': fields.date('Valid Until', help="Validity of this BoM. Keep empty if it's always valid."),
    }
    def _bom_find(self, cr, uid, product_tmpl_id=None, product_id=None, context=None):
        """ Finds BoM for particular product and product uom.
        @param product_tmpl_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        if product_id:
            if not product_tmpl_id:
                product_tmpl_id = self.pool['product.product'].browse(cr, uid, product_id, context=context).product_tmpl_id.id
            domain = [
                '|',
                    ('product_id', '=', product_id),
                    '&',
                        ('product_id', '=', False),
                        ('product_tmpl_id', '=', product_tmpl_id)
            ]
        elif product_tmpl_id:
            domain = [('product_id', '=', False), ('product_tmpl_id', '=', product_tmpl_id)]
        else:
            # neither product nor template, makes no sense to search
            return False
        domain = domain + [ '|', ('date_start', '=', False), ('date_start', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT)),
                            '|', ('date_stop', '=', False), ('date_stop', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT))]
        # order to prioritize bom with product_id over the one without
        ids = self.search(cr, uid, domain, order='product_id', context=context)
        # Search a BoM which has all properties specified, or if you can not find one, you could
        # pass a BoM without any properties
        return ids

class product_template(osv.osv):
    _inherit="product.template"
    
    def _pos_bom_sale_count(self, cr, uid, ids, field_name, arg, context=None):
        bom_pool = self.pool('product.bom.service')
        res = {}
        for product_tmpl_id in ids:
            nb = bom_pool.search_count(cr, uid, [('product_tmpl_id', '=', product_tmpl_id)], context=context)
            res[product_tmpl_id] = {
                'pos_bom_count': nb,
            }
        return res
    
    _columns= {
        'pos_bom_count' : fields.function(_pos_bom_sale_count,string='#BOM Service ', type='integer', multi="_pos_bom_sale_count")
    }
    def get_sale_bom(self, cr, uid, ids, context):
        Bom_pool = self.pool('product.bom.service')
        bom_id = Bom_pool.search(cr, uid, [('product_tmpl_id', '=', ids)], context=context)
        template = self.browse(cr, uid, ids[0])
        context = context and context.copy() or {}
        context.update({'default_product_tmpl_id': ids[0],
                        'default_product_qty': 1.0,
                        'default_product_uom': template.uom_id.id})
        if len(bom_id) == 1:
            return {
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'product.bom.service',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': bom_id[0],
                'context': context,
            }
        else:
            return {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'product.bom.service',
                'domain':"[('product_tmpl_id','=',%d)]"%ids[0],
                'type': 'ir.actions.act_window',
                'context': context,
            }
