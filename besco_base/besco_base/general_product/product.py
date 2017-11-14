# -*- coding: utf-8 -*-
from openerp import api, SUPERUSER_ID
from openerp import tools
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _

from openerp.tools.float_utils import float_round, float_compare
from openerp.exceptions import UserError, AccessError

import xlrd
from lxml import etree
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_product'))

class product_uom(osv.osv):
    _inherit = "product.uom"
    
    def write(self, cr, uid, ids, vals, context=None):
#         if isinstance(ids, (int, long)):
#             ids = [ids]
#         if 'category_id' in vals:
#             for uom in self.browse(cr, uid, ids, context=context):
#                 if uom.category_id.id != vals['category_id']:
#                     raise UserError(_("Cannot change the category of existing Unit of Measure '%s'.") % (uom.name,))
        return super(osv.osv, self).write(cr, uid, ids, vals, context=context)
    
    #Thanh: Pass Product to get exact conversion
    def _compute_qty(self, cr, uid, from_uom_id, qty, to_uom_id=False, round=True, rounding_method='UP', product_id=False):
        if not from_uom_id or not qty or not to_uom_id:
            return qty
        uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
        return self._compute_qty_obj(cr, uid, from_unit, qty, to_unit, round=round, rounding_method=rounding_method, product_id=product_id)
    
    def _compute_qty_obj(self, cr, uid, from_unit, qty, to_unit, round=True, rounding_method='UP', product_id=False, context=None):
        if context is None:
            context = {}
        
        #Thanh kiem tra neu co product thi` su dung table UoM Conversion
        if from_unit.id == to_unit.id:
            factor = 1
            return factor * qty
        
        if product_id:
            check_from_uom = False
            check_to_uom = False
            factor = 1
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            if product.uom_id.id != from_unit.id and not len(product.uom_ids):
                #THANH: Convert UoM in the same Category (Kg, Tan)
                if from_unit.category_id.id == to_unit.category_id.id and (from_unit.uom_type != 'reference' or to_unit.uom_type != 'reference'):
                    amount = qty/from_unit.factor
                    amount = amount * to_unit.factor
                    if round:
                        amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
                    return amount
                raise UserError(_("Conversion from UoM '%s' to Product UoM '%s' is not defined for Product '%s'\n or From UoM and To UoM are the same type Reference (Please check from Menu Product UoM)!.") % (from_unit.name, product.uom_id.name, product.name))
            
            if product.uom_id.id == from_unit.id:
                check_from_uom = True
            if product.uom_id.id == to_unit.id:
                check_to_uom = True
                
            for line in product.uom_ids:
                if check_from_uom and check_to_uom:
                    break
                
                line_factor = 1
                if line.uom_type == 'bigger' and line.factor:
                    line_factor = 1 / line.factor
                if line.uom_type == 'smaller' and line.factor:
                    line_factor = 1 * line.factor
                if line.uom_id.id == from_unit.id and line.factor and not check_from_uom:
                    factor = factor / line_factor
                    check_from_uom = True
                if line.uom_id.id == to_unit.id and line.factor and not check_to_uom:
                    factor = factor * line_factor
                    check_to_uom = True
            if check_from_uom and check_to_uom:
                return (factor * qty)
            else:
                raise UserError(_("Conversion from UoM '%s' to Product UoM '%s' is not defined for Product '%s'\n or From UoM and To UoM are the same type Reference (Please check from Menu Product UoM)!.") % (from_unit.name, product.uom_id.name, product.name))
        #Thanh kiem tra neu co product thi` su dung table UoM Conversion
        
        if from_unit.category_id.id != to_unit.category_id.id:
#             if context.get('raise-exception', True):
#                 raise UserError(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (from_unit.name,to_unit.name))
#             else:
#                 return qty
#             return qty
            #Thanh kiem tra neu co product thi` su dung table UoM Conversion
            raise UserError(_('Conversion Table of this Product is not defined!'))
        
        amount = qty/from_unit.factor
        if to_unit:
            amount = amount * to_unit.factor
            if round:
                amount = float_round(amount, precision_rounding=to_unit.rounding, rounding_method=rounding_method)
        return amount

    def _compute_price(self, cr, uid, from_uom_id, price, to_uom_id=False, product_id=False):
        #Thanh kiem tra neu co product thi` su dung table UoM Conversion
        if not from_uom_id or not price or not to_uom_id:
            return price
        
        if from_uom_id == to_uom_id:
            factor = 1
            return factor * price
        
        if product_id:
            uoms = self.browse(cr, uid, [from_uom_id, to_uom_id])
            from_unit, to_unit = uoms[0], uoms[1]
            
            check_from_uom = False
            check_to_uom = False
            factor = 1
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            if from_unit.category_id.id == to_unit.category_id.id and (from_unit.uom_type != 'reference' or to_unit.uom_type != 'reference'):
                amount = price/from_unit.factor
                amount = amount * to_unit.factor
                return amount
            raise UserError(_("Conversion from UoM '%s' to Product UoM '%s' is not defined for Product '%s'\n or From UoM and To UoM are the same type Reference (Please check from Menu Product UoM)!.") % (from_unit.name, product.uom_id.name, product.name))
            
            if product.uom_id.id == from_unit.id:
                check_from_uom = True
            if product.uom_id.id == to_unit.id:
                check_to_uom = True
                
            for line in product.uom_ids:
                if check_from_uom and check_to_uom:
                    break
                
                line_factor = 1
                if line.uom_type == 'bigger' and line.factor:
                    line_factor = 1 / line.factor
                if line.uom_type == 'smaller' and line.factor:
                    line_factor = 1 * line.factor
                if line.uom_id.id == from_unit.id and line.factor and not check_from_uom:
                    factor = factor / line_factor
                    check_from_uom = True
                if line.uom_id.id == to_unit.id and line.factor and not check_to_uom:
                    factor = factor * line_factor
                    check_to_uom = True
            if check_from_uom and check_to_uom:
                return (factor * price)
            else:
                raise UserError(_("Conversion from UoM '%s' to Product UoM '%s' is not defined for Product '%s'\n or From UoM and To UoM are the same type Reference (Please check from Menu Product UoM)!.") % (from_unit.name, product.uom_id.name, product.name))
        #Thanh kiem tra neu co product thi` su dung table UoM Conversion
        
        if (not from_uom_id or not price or not to_uom_id
                or (to_uom_id == from_uom_id)):
            return price
        from_unit, to_unit = self.browse(cr, uid, [from_uom_id, to_uom_id])
        if from_unit.category_id.id != to_unit.category_id.id:
#             return price
            #Thanh kiem tra neu co product thi` su dung table UoM Conversion
            raise UserError(_('Conversion Table of this Product is not defined!'))
        
        amount = price * from_unit.factor
        if to_uom_id:
            amount = amount / to_unit.factor
        return amount
    
product_uom()

class product_category(osv.osv):
    _inherit = "product.category"
    _order = 'seq asc,name'
    
    @api.multi
    def name_get(self):
        def get_names(cat):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = [cat.name]
#             while cat:
#                 res.append(cat.name)
#                 cat = cat.parent_id
            return res
        res = [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]
        return res
    
    _columns = {
        'code': fields.char('Code', size=64),
        'seq':fields.integer('Sequence'),
        
        'property_account_refund_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Refund Account",
            help="This account will be used for invoices return to value sales for the current product category"),
        'property_stock_account_loss_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Stock Account Loss",
            help="This account will hold the current value of the loss products for the current product category"),
        'property_stock_account_scrap_categ': fields.property(
            type='many2one',
            relation='account.account',
            string="Stock Account Scrap",
            help="This account will hold the current value of the scrap products for the current product category"),
        
        'property_account_cogs_export': fields.property(
            type='many2one',
            relation='account.account',
            string="COGS Export Account",
            domain=[('type', '!=', 'view')]),
        
        'property_account_cogs_local': fields.property(
            type='many2one',
            relation='account.account',
            string="COGS Local Account",
            domain=[('type', '!=', 'view')]),
        
        'property_wip_account': fields.property(
            type='many2one',
            relation='account.account',
            string="WIP Account",
            domain=[('type', '!=', 'view')]),
    }
    
    def get_latest_parent(self, categ):
        if not categ.parent_id:
            return categ.code
        parent_id = categ.parent_id
        while parent_id:
            if parent_id.parent_id:
                parent_id = parent_id.parent_id
            else:
                break
        return parent_id.code
    
    def copy(self, cr, uid, id, default=None, context=None, done_list=None, local=False):
        default = {} if default is None else default.copy()
        default.update({'code': '/'})
        return super(product_category, self).copy(cr, uid, id, default, context=context)

    def is_code_uniq(self,cr,uid,ids):
        for categ in self.browse(cr,uid,ids):
            if categ.code and categ.default_code != '/':
                category_ids = self.search(cr, uid, [('code','=', categ.code),
                                                  ('id','<>', categ.id)])
                if len(category_ids):
                    return False
        return True

    _constraints = [(is_code_uniq, 'Lỗi: Mã danh mục đã tồn tại !!!', [''])]

    def onchange_parent_id(self, cr, uid, ids, parent_id):
        value = {'value': {}}
        if parent_id:
            parent_obj = self.browse(cr, uid, parent_id)
            value['value'].update({'property_account_refund_categ': parent_obj.property_account_refund_categ.id or False,
                                   'property_stock_account_loss_categ': parent_obj.property_stock_account_loss_categ.id or False,
                                   'property_stock_account_scrap_categ': parent_obj.property_stock_account_scrap_categ.id or False,
                                   'property_stock_valuation_account_id': parent_obj.property_stock_valuation_account_id.id or False,
                                   'property_account_income_categ_id': parent_obj.property_account_income_categ_id.id or False,
                                   'property_account_expense_categ_id': parent_obj.property_account_expense_categ_id.id or False,})
        return value
    
#     def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
#         if context is None:
#             context = {}
#         res = super(product_category,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
#          
#         if view_type == 'form':
#             doc = etree.XML(res['arch'])
#              
#             if context.has_key('search_finished_goods'):
#                 categ_ids = self.search(cr, uid, [('code','=','TP')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                     res['arch'] = etree.tostring(doc)
#             
#             if context.has_key('search_service'):
#                 categ_ids = self.search(cr, uid, [('code','=','DV')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                     res['arch'] = etree.tostring(doc)
#                     
#             if context.has_key('search_product'):
#                 categ_ids = self.search(cr, uid, [('code','=','HH')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                     res['arch'] = etree.tostring(doc)
#                      
#             if context.has_key('search_materials'):
#                 categ_ids = self.search(cr, uid, [('code','=','NVL')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                 res['arch'] = etree.tostring(doc)
#                  
#             if context.has_key('search_semi_finished_goods'):
#                 categ_ids = self.search(cr, uid, [('code','=','BTP')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                 res['arch'] = etree.tostring(doc)
#              
#             if context.has_key('search_congcudungcu'):
#                 categ_ids = self.search(cr, uid, [('code','=','CCDC')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                 res['arch'] = etree.tostring(doc)
#              
#             if context.has_key('search_nguyenlieutieuhao'):
#                 categ_ids = self.search(cr, uid, [('code','=','NLTH')])
#                 for node in doc.xpath("//field[@name='parent_id']"):
#                     node.set('domain', "[('parent_id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
#                      
#                 res['arch'] = etree.tostring(doc)
#         return res
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('code', False):
            for categ in self.browse(cr, uid, ids):
                if categ.code in ('HB', 'TP', 'NVL', 'BTP', 'CCDC', 'NLTH', 'DV'):
                    raise AccessError(_("You're not able to delete default configuration !!!"))
        return super(product_category, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        for categ in self.browse(cr, uid, ids):
            if categ.code in ('HB', 'TP', 'NVL', 'BTP', 'CCDC', 'NLTH', 'DV'):
                raise AccessError(_("You're not able to delete default configuration !!!"))
        return super(product_category, self).unlink(cr, uid, ids, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
         
        if context.has_key('search_finished_goods'):
            categ_ids = self.search(cr, uid, [('code','=','TP')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
        
        if context.has_key('search_service'):
            categ_ids = self.search(cr, uid, [('code','=','DV')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
                
        if context.has_key('search_product'):
            categ_ids = self.search(cr, uid, [('code','=','HH')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
                 
        if context.has_key('search_materials'):
            categ_ids = self.search(cr, uid, [('code','=','NVL')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
         
        if context.has_key('search_semi_finished_goods'):
            categ_ids = self.search(cr, uid, [('code','=','BTP')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
         
        if context.has_key('search_congcudungcu'):
            categ_ids = self.search(cr, uid, [('code','=','CCDC')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
         
        if context.has_key('search_nguyenlieutieuhao'):
            categ_ids = self.search(cr, uid, [('code','=','NLTH')])
            if len(categ_ids):
                args.append(('id','child_of',categ_ids))
                 
        return super(product_category, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def init(self, cr):
        wb = xlrd.open_workbook(base_path + '/general_product/data/product_category.xls')
        wb.sheet_names()
        sh = wb.sheet_by_index(0)
        account_pool = self.pool.get('account.account')
        i = -1
        for rownum in range(sh.nrows):
            i += 1
            row_values = sh.row_values(rownum)
             
            if i == 0:
                continue
            try:
                exist_ids = self.search(cr, SUPERUSER_ID, [('code','=',row_values[7])])
                if not len(exist_ids):
                    vals = {'name': row_values[0], 'code':row_values[7]}
                     
                    if row_values[8]:
                        parent_ids = self.search(cr, SUPERUSER_ID, [('code','=',row_values[8])])
                        vals.update({'parent_id': parent_ids and parent_ids[0] or False})
                         
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[1])])
                    if len(account_ids):
                        vals.update({'property_account_income_categ_id': account_ids[0]})
                     
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[2])])
                    if len(account_ids):
                        vals.update({'property_account_refund_categ': account_ids[0]})
                     
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[3])])
                    if len(account_ids):
                        vals.update({'property_account_expense_categ_id': account_ids[0]})
                     
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[4])])
                    if len(account_ids):
                        vals.update({'property_stock_valuation_account_id': account_ids[0]})
                     
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[5])])
                    if len(account_ids):
                        vals.update({'property_stock_account_loss_categ': account_ids[0]})
                     
                    account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[6])])
                    if len(account_ids):
                        vals.update({'property_stock_account_scrap_categ': account_ids[0]})
                     
                    self.create(cr, SUPERUSER_ID, vals)
            except Exception, e:
                continue
        
        #Thanh: Fix parent left and parent right
        def browse_rec(root, pos=0):
            cr.execute("SELECT id FROM product_category WHERE parent_id=%s order by sequence"%(root))
            pos2 = pos + 1
            for id in cr.fetchall():
                pos2 = browse_rec(id[0], pos2)
            cr.execute('update product_category set parent_left=%s, parent_right=%s where id=%s', (pos, pos2, root))
            return pos2 + 1  
        query = "SELECT id FROM product_category WHERE parent_id IS NULL order by sequence"
        pos = 0
        cr.execute(query)
        for (root,) in cr.fetchall():
            pos = browse_rec(root, pos)
        return True
    
product_category()

class product_uom_relation(osv.osv):
    _name='product.uom.relation'
    _columns={
      'product_id': fields.many2one('product.template', 'Product', required=True, ondelete='cascade'),
      'uom_id': fields.many2one('product.uom', 'UoM', required=True),
      'uom_type': fields.selection([('bigger','Bigger than the reference Unit of Measure'),
                                      ('reference','Reference Unit of Measure for this category'),
                                      ('smaller','Smaller than the reference Unit of Measure')],'Type', required=1),
      'factor':fields.float('Factor', digits=(12, 6),),
    }
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.has_key('factor') and vals['factor'] > 1:
            vals.update({'uom_type': 'bigger'})
        if vals.has_key('factor') and vals['factor'] < 1:
            vals.update({'uom_type': 'smaller'})
        if vals.has_key('factor') and vals['factor'] == 1:
            vals.update({'uom_type': 'reference'})
        return super(product_uom_relation, self).write(cr, uid, ids, vals, context)
        
product_uom_relation()


class product_product(osv.osv):
    _inherit = "product.product"
    
    _columns = {
        #Thanh: Set code readonly
        'default_code' : fields.char('Internal Reference', select=True, readonly=True),
        
        #Kiet: Mã của hệ thống cũ:
        'company_code':fields.char('Partner Code', select=True, readonly=False),
    }
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
         
#         categ_pool = self.pool.get('product.category')
#         new_args = []
#               
#         if context.has_key('search_finished_goods'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','TP')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#          
#         if context.has_key('search_service'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','DV')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#                   
#         if context.has_key('search_product'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','HH')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#                   
#         if context.has_key('search_materials'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','NVL')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#           
#         if context.has_key('search_semi_finished_goods'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','BTP')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#           
#         if context.has_key('search_congcudungcu'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','CCDC')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#           
#         if context.has_key('search_nguyenlieutieuhao'):
#             categ_ids = categ_pool.search(cr, uid, [('code','=','NLTH')])
#             if len(categ_ids):
#                 new_args.append(('categ_id','child_of',categ_ids))
#                   
#         if len(new_args):
#             if len(new_args) > 1:
#                 for i in range(0,len(new_args)-1):
#                     args.append('|')
#             args += new_args
#         
        #Thanh: Search barcode
        
        operator = False
        value = False
        pos = 0
        # Kiet domain Product theo Picking type
        product_ids =[]
        if context.has_key('picking_type_id'):
            categ_pool = self.pool.get('product.category')
            picking_type = self.pool.get('stock.picking.type').browse(cr,uid,context['picking_type_id'])
            is_service = picking_type.is_service or False
            is_materials = picking_type.is_materials or False
            is_tools = picking_type.is_tools or False
            is_product = picking_type.is_product or False
            
            if is_service:
                categ_ids = categ_pool.search(cr, uid, [('code','=','DV')])
                categ_ids = categ_pool.search(cr, uid, [('id','child_of',categ_ids)])
                product_ids += self.pool.get('product.product').search(cr,uid,[('categ_id','in',categ_ids)])
            
            if is_materials:
                categ_ids = categ_pool.search(cr, uid, [('code','=','NVL')])
                categ_ids = categ_pool.search(cr, uid, [('id','child_of',categ_ids)])
                product_ids += self.pool.get('product.product').search(cr,uid,[('categ_id','in',categ_ids)])
            
            if is_tools:
                categ_ids = categ_pool.search(cr, uid, [('code','=','CCDC')])
                categ_ids = categ_pool.search(cr, uid, [('id','child_of',categ_ids)])
                product_ids += self.pool.get('product.product').search(cr,uid,[('categ_id','in',categ_ids)])
            
            if is_product:
                categ_ids = categ_pool.search(cr, uid, [('code','=','HH')])
                categ_ids = categ_pool.search(cr, uid, [('id','child_of',categ_ids)])
                product_ids += self.pool.get('product.product').search(cr,uid,[('categ_id','in',categ_ids)])
                
        if product_ids: 
            args += [('id', 'in', product_ids)]
        while pos < len(args):
            if args[pos][0] == 'name' and args[pos][1] in ('like', 'ilike', '=') and args[pos][2]:
                operator = args[pos][1]
                value = args[pos][2]
                args.pop(pos)
                break
            pos += 1
        if operator:
            args.append('|')
            args.append('|')
            args.append(['name', operator, value])
            args.append(['barcode', operator, value])
            args.append(['default_code', operator, value])
        return super(product_product, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        ids = self.search(cr, user, domain + args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        #Thanh: Only User has group Product Creation can create a product
        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "general_product.group_product_creation"):
            raise AccessError(_("You're not able to update a product!!!"))
        return super(product_product, self).write(cr, uid, ids, vals, context=context)
    
    def create(self, cr, uid, vals, context=None):
        #Thanh: Only User has group Product Creation can create a product
        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "general_product.group_product_creation"):
            raise AccessError(_("You're not able to create a product!!!"))
        system_sequence_obj = self.pool.get('system.sequence')
        categ_pool = self.pool.get('product.category')
        template_pool = self.pool.get('product.template')
            
        if vals.get('product_tmpl_id',False):
            template = template_pool.browse(cr, uid, vals['product_tmpl_id'])
                
            latest_parent_code = categ_pool.get_latest_parent(template.categ_id)
                
            if latest_parent_code == 'HB':
                code = system_sequence_obj.get_current_sequence(cr, 'product_code')
                vals.update({'default_code': code})
                
            if latest_parent_code == 'TP':
                code = system_sequence_obj.get_current_sequence(cr, 'finished_good_code')
                vals.update({'default_code': code})
                
            if latest_parent_code == 'NVL':
                code = system_sequence_obj.get_current_sequence(cr, 'material_code')
                vals.update({'default_code': code})
                
            if latest_parent_code == 'BTP':
                code = system_sequence_obj.get_current_sequence(cr, 'semi_finished_good_code')
                vals.update({'default_code': code})
                
            if latest_parent_code == 'CCDC':
                code = system_sequence_obj.get_current_sequence(cr, 'tools_code')
                vals.update({'default_code': code})
                
            if latest_parent_code == 'NLTH':
                code = system_sequence_obj.get_current_sequence(cr, 'consumable_item_code')
                vals.update({'default_code': code})
        return super(product_product, self).create(cr, uid, vals, context=context)
    
#     def init(self, cr):
#         system_sequence_obj = self.pool.get('system.sequence')
#         categ_pool = self.pool.get('product.category')
#         product_ids = self.search(cr, SUPERUSER_ID, [('default_code', '=', False)])
#         if len(product_ids):
#             products = self.read(cr, SUPERUSER_ID, product_ids, ['id', 'categ_id'])
#             for product in products:
#                 categ = categ_pool.browse(cr, SUPERUSER_ID, product['categ_id'][0])
#                 latest_parent_code = categ_pool.get_latest_parent(categ)
#                 
#                 code = False
#                 if latest_parent_code == 'HB':
#                     code = system_sequence_obj.get_current_sequence(cr, 'product_code')
#                  
#                 if latest_parent_code == 'TP':
#                     code = system_sequence_obj.get_current_sequence(cr, 'finished_good_code')
#                  
#                 if latest_parent_code == 'NVL':
#                     code = system_sequence_obj.get_current_sequence(cr, 'material_code')
#                  
#                 if latest_parent_code == 'BTP':
#                     code = system_sequence_obj.get_current_sequence(cr, 'semi_finished_good_code')
#                  
#                 if latest_parent_code == 'CCDC':
#                     code = system_sequence_obj.get_current_sequence(cr, 'tools_code')
#                  
#                 if latest_parent_code == 'NLTH':
#                     code = system_sequence_obj.get_current_sequence(cr, 'consumable_item_code')
#                 
#                 if code:
#                     cr.execute('''
#                     UPDATE product_product
#                     SET default_code='%s'
#                     WHERE id=%s
#                     '''%(code, product['id']))
#         return True
    
class product_template(osv.osv):
    _inherit = "product.template"
    
    
    
    #THANH: Overwrite, because in stock module, type product is exist
    def _get_product_template_type(self, cr, uid, context=None):
        res = super(product_template, self)._get_product_template_type(cr, uid, context=context)
        return [('product', 'Stockable Product'),
                ('consu', 'Consumable'), 
                ('service', 'Service')]
    
    _columns = {
        #Thanh: Readonly this field
        'default_code': fields.related('product_variant_ids', 'default_code', type='char', string='Internal Reference', readonly=True),
        
        #Thanh: required for Code
        'uom_ids': fields.one2many('product.uom.relation', 'product_id', "Related UoMs"),
    }
    _defaults = {
#          'valuation':'real_time'
        'cost_method': 'average',
    }
    
    def is_default_uniq(self,cr,uid,ids):
        for product in self.browse(cr,uid,ids):
            if product.default_code and product.default_code != '/':
                product_obj_ids = self.search(cr, uid, [('default_code','=',product.default_code),
                                                  ('id','<>',product.id),('active','=',True)])
                if product_obj_ids:
                    return False
        return True
    
    _constraints = [(is_default_uniq, 'Lỗi: Mã sản phẩm đã tồn tại!!!', ['default_code'])]
    
    def write(self, cr, uid, ids, vals, context=None):
        #Thanh: Only User has group Product Creation can create a product
        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "general_product.group_product_creation"):
            raise AccessError(_("You're not able to update a product!!!"))
        return super(product_template, self).write(cr, uid, ids, vals, context=context)
    
    def create(self, cr, uid, vals, context=None):
        #Thanh: Only User has group Product Creation can create a product
        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "general_product.group_product_creation"):
            raise AccessError(_("You're not able to create a product!!!"))
        return super(product_template, self).create(cr, uid, vals, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
         
        categ_pool = self.pool.get('product.category')
        new_args = []
             
        if context.has_key('search_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','TP')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
        
        if context.has_key('search_service'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','DV')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
                 
        if context.has_key('search_product'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','HH')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
                 
        if context.has_key('search_materials'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','NVL')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
         
        if context.has_key('search_semi_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','BTP')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
         
        if context.has_key('search_congcudungcu'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','CCDC')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
         
        if context.has_key('search_nguyenlieutieuhao'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','NLTH')])
            if len(categ_ids):
                new_args.append(('categ_id','child_of',categ_ids))
                 
        if len(new_args):
            if len(new_args) > 1:
                for i in range(0,len(new_args)-1):
                    args.append('|')
            args += new_args
        
        #Thanh: Search barcode
        operator = False
        value = False
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'name' and args[pos][1] in ('like', 'ilike', '=') and args[pos][2]:
                operator = args[pos][1]
                value = args[pos][2]
                args.pop(pos)
                break
            pos += 1
        if operator:
            args.append('|')
            args.append('|')
            args.append(['name', operator, value])
            args.append(['barcode', operator, value])
            args.append(['default_code', operator, value])
        return super(product_template, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        ids = self.search(cr, user, domain + args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(product_template, self).default_get(cr, uid, fields, context=context)
        
        #Thanh: Always use average cost
        res.update({'cost_method':'average'})
        
        categ_pool = self.pool.get('product.category')
        categ_ids = []
        if context.has_key('search_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','TP')])
            res.update({'type':'product'})
        
        if context.has_key('search_service'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','DV')])
            res.update({'type':'service'})
            
        if context.has_key('search_product'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','HH')])
            res.update({'type':'product'})
            
        if context.has_key('search_materials'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','NVL')])
            res.update({'type':'consu',
                        'sale_ok': False,})
            
        if context.has_key('search_semi_finished_goods'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','BTP')])
            res.update({'type':'product',
                        'sale_ok': False,
                        })
            
        if context.has_key('search_congcudungcu'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','CCDC')])
            res.update({'type':'consu',
                        'sale_ok': False,
                        })
            
        if context.has_key('search_nguyenlieutieuhao'):
            categ_ids = categ_pool.search(cr, uid, [('code','=','NLTH')])
            res.update({'type':'consu',
                        'sale_ok': False,
                        })
            
        if len(categ_ids):
            res.update({'categ_id':categ_ids[0]})
        return res
     
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(product_template,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            categ_pool = self.pool.get('product.category')
             
#             for node in doc.xpath("//field[@name='type']"):
#                 node.set('readonly', '1')
                 
            if context.has_key('search_finished_goods'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','TP')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
             
            if context.has_key('search_service'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','DV')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
            if context.has_key('search_product'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','HH')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
            if context.has_key('search_materials'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','NVL')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
            if context.has_key('search_semi_finished_goods'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','BTP')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
            if context.has_key('search_congcudungcu'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','CCDC')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
            if context.has_key('search_nguyenlieutieuhao'):
                categ_ids = categ_pool.search(cr, uid, [('code','=','NLTH')])
                for node in doc.xpath("//field[@name='categ_id']"):
                    node.set('domain', "[('id', 'child_of', [%s])]"%(','.join(map(str, categ_ids))))
                     
#             xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
            res['arch'] = etree.tostring(doc)
                  
        return res
    
    
