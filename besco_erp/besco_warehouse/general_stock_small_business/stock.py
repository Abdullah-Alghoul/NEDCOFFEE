# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from lxml import etree

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_picking,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
         
        if view_type in ['tree', 'form']:
            doc = etree.XML(res['arch'])
            
            for node in doc.xpath("//field[@name='min_date']"):
                node.set('invisible', "True")
                        
            #THANH: 
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
class stock_move(osv.osv):
    _inherit = 'stock.move'
    
    def _compute_sale_subtotal(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {
                            'sale_price_subtotal': line.sale_price_unit * line.product_uom_qty,
                            }
        return res
    
    _columns = {
        'sale_price_unit': fields.float('Sale Price'),
        'sale_price_subtotal': fields.function(_compute_sale_subtotal, string='Sale Subtotal', digits= (16,2), 
                                               type='float', readonly=True, multi='total_sale_info'),
    }
    
    def onchange_quantity(self, cr, uid, ids, product_id, product_qty, product_uom, price_unit=0.0, sale_price_unit=0.0):
        """ On change of product quantity finds UoM
        @param product_id: Product id
        @param product_qty: Changed Quantity of product
        @param product_uom: Unit of measure of product
        @return: Dictionary of values
        """
        res = super(stock_move, self).onchange_quantity(cr, uid, ids, product_id, product_qty, product_uom, price_unit=price_unit)
        res['value'].update({'sale_price_subtotal': product_qty * sale_price_unit})
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_move,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        mod_obj = self.pool.get('ir.model.data')
        dummy, except_view_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', "view_move_tree"))
        
        if view_type == 'tree':
            doc = etree.XML(res['arch'])
            
            if view_id != except_view_id:
                for node in doc.xpath("//field[@name='location_id']"):
                    node.set('invisible', "True")
                for node in doc.xpath("//field[@name='location_dest_id']"):
                    node.set('invisible', "True")
                    
            for node in doc.xpath("//field[@name='date_expected']"):
                node.set('invisible', "True")
                        
            location_dest_id = context.get('default_location_dest_id', False)
            if location_dest_id:
                location_dest = self.pool.get('stock.location').browse(cr, uid, location_dest_id)
                if location_dest.usage in ['supplier', 'customer']:
                    for node in doc.xpath("//field[@name='price_unit']"):
                        node.set('invisible', "True")
                    for node in doc.xpath("//field[@name='price_subtotal']"):
                        node.set('invisible', "True")
                    for node in doc.xpath("//field[@name='is_promotion']"):
                        node.set('invisible', "True")
                    
                    for node in doc.xpath("//field[@name='sale_price_unit']"):
                        node.set('invisible', "False")
                    for node in doc.xpath("//field[@name='sale_price_subtotal']"):
                        node.set('invisible', "False")
                        
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res