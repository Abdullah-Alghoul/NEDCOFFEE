# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
from openerp.exceptions import UserError

import xlrd
from lxml import etree
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_product'))

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _get_product_accounts(self):
        """ Add the stock accounts related to product to the result of super()
        @return: dictionary which contains information regarding stock accounts and super (income+expense accounts)
        """
        accounts = super(ProductTemplate, self)._get_product_accounts()
        accounts.update({
            'cogs_export': self.categ_id.property_account_cogs_export.id,
            'cogs_local': self.categ_id.property_account_cogs_local.id,
            'account_loss':self.categ_id.property_stock_account_loss_categ.id,
            'wip_account':self.categ_id.property_wip_account.id,
        })
        return accounts
#     code = fields.Char(string='Code', size=64, copy='/')
#     seq = fields.Integer(string='Sequence')
#     
#     property_account_refund_categ = fields.Many2one('account.account', company_dependent=True,
#         string="Refund Account",
#         domain=[('deprecated', '=', False)])
#     
#     property_stock_account_loss_categ = fields.Many2one('account.account', company_dependent=True,
#         string="Stock Account Loss",
#         domain=[('deprecated', '=', False)])
#     
#     property_stock_account_scrap_categ = fields.Many2one('account.account', company_dependent=True,
#         string="Stock Account Loss",
#         domain=[('deprecated', '=', False)])
#     
#         
#     def get_latest_parent(self, categ):
#         if not categ.parent_id:
#             return categ.code
#         parent_id = categ.parent_id
#         while parent_id:
#             if parent_id.parent_id:
#                 parent_id = parent_id.parent_id
#             else:
#                 break
#         return parent_id.code
#     
#     def is_code_uniq(self):
#         for categ in self:
#             if categ.code and categ.default_code != '/':
#                 category_ids = self.search([('code','=', categ.code),
#                                                   ('id','<>', categ.id)])
#                 if category_ids:
#                     return False
#         return True
#      
#     _constraints = [(is_code_uniq, 'Lỗi: Mã danh mục đã tồn tại !!!', [''])]
#     
#     
#     def onchange_parent_id(self, cr, uid, ids, parent_id):
#         value = {'value': {}}
#         if parent_id:
#             parent_obj = self.browse(cr, uid, parent_id)
#             value['value'].update({'property_account_refund_categ': parent_obj.property_account_refund_categ.id or False,
#                                    'property_stock_account_loss_categ': parent_obj.property_stock_account_loss_categ.id or False,
#                                    'property_stock_account_scrap_categ': parent_obj.property_stock_account_scrap_categ.id or False,
#                                    'property_stock_valuation_account_id': parent_obj.property_stock_valuation_account_id.id or False,
#                                    'property_account_income_categ_id': parent_obj.property_account_income_categ_id.id or False,
#                                    'property_account_expense_categ_id': parent_obj.property_account_expense_categ_id.id or False,})
#         return value
#     
#     def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
#         if context is None:
#             context = {}
#          
#         if context.has_key('search_finished_goods'):
#             categ_ids = self.search(cr, uid, [('code','=','TP')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#         
#         if context.has_key('search_service'):
#             categ_ids = self.search(cr, uid, [('code','=','DV')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#                 
#         if context.has_key('search_product'):
#             categ_ids = self.search(cr, uid, [('code','=','HH')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#                  
#         if context.has_key('search_materials'):
#             categ_ids = self.search(cr, uid, [('code','=','NVL')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#          
#         if context.has_key('search_semi_finished_goods'):
#             categ_ids = self.search(cr, uid, [('code','=','BTP')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#          
#         if context.has_key('search_congcudungcu'):
#             categ_ids = self.search(cr, uid, [('code','=','CCDC')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#          
#         if context.has_key('search_nguyenlieutieuhao'):
#             categ_ids = self.search(cr, uid, [('code','=','NLTH')])
#             if len(categ_ids):
#                 args.append(('id','child_of',categ_ids))
#                  
#         return super(product_category, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
# 
#     def init(self, cr):
#         wb = xlrd.open_workbook(base_path + '/general_product/data/product_category.xls')
#         wb.sheet_names()
#         sh = wb.sheet_by_index(0)
#         account_pool = self.pool.get('account.account')
#         i = -1
#         for rownum in range(sh.nrows):
#             i += 1
#             row_values = sh.row_values(rownum)
#              
#             if i == 0:
#                 continue
#             try:
#                 exist_ids = self.search(cr, SUPERUSER_ID, [('code','=',row_values[7])])
#                 if not len(exist_ids):
#                     vals = {'name': row_values[0], 'code':row_values[7]}
#                      
#                     if row_values[8]:
#                         parent_ids = self.search(cr, SUPERUSER_ID, [('code','=',row_values[8])])
#                         vals.update({'parent_id': parent_ids and parent_ids[0] or False})
#                          
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[1])])
#                     if len(account_ids):
#                         vals.update({'property_account_income_categ': account_ids[0]})
#                      
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[2])])
#                     if len(account_ids):
#                         vals.update({'property_account_refund_categ': account_ids[0]})
#                      
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[3])])
#                     if len(account_ids):
#                         vals.update({'property_account_expense_categ': account_ids[0]})
#                      
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[4])])
#                     if len(account_ids):
#                         vals.update({'property_stock_valuation_account_id': account_ids[0]})
#                      
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[5])])
#                     if len(account_ids):
#                         vals.update({'property_stock_account_loss_categ': account_ids[0]})
#                      
#                     account_ids = account_pool.search(cr, SUPERUSER_ID, [('code','=',row_values[6])])
#                     if len(account_ids):
#                         vals.update({'property_stock_account_scrap_categ': account_ids[0]})
#                      
#                     self.create(cr, SUPERUSER_ID, vals)
#             except Exception, e:
#                 continue
        
        #Thanh: Fix parent left and parent right
#         def browse_rec(root, pos=0):
#             cr.execute("SELECT id FROM product_category WHERE parent_id=%s order by sequence"%(root))
#             pos2 = pos + 1
#             for id in cr.fetchall():
#                 pos2 = browse_rec(id[0], pos2)
#             cr.execute('update product_category set parent_left=%s, parent_right=%s where id=%s', (pos, pos2, root))
#             return pos2 + 1  
#         query = "SELECT id FROM product_category WHERE parent_id IS NULL order by sequence"
#         pos = 0
#         cr.execute(query)
#         for (root,) in cr.fetchall():
#             pos = browse_rec(root, pos)
#         return True