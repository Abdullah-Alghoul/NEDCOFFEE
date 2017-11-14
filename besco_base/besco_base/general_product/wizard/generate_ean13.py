# -*- coding: utf-8 -*-
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.tools.float_utils import float_round

class generate_product_ean13(models.TransientModel):

    _name = "generate.product.ean13"
    _description = "Generate Product EAN13"

    category_ids = fields.Many2many('product.category', 
                                    'wizard_generate_barcode_category_rel',
                                    'wizard_id', 'categ_id',
                                    string='Categories', required=True)
    
    @api.multi
    def action_generate(self):
        cr = self.env.cr
        
        categ_ids = [x.id for x in self.category_ids]
        
        sequence_obj = self.pool.get('ir.sequence')
        system_sequence_obj = self.env['system.sequence']
        categ_pool = self.env['product.category']
        product_pool = self.env['product.product']
        child_categ_ids = categ_pool.search([('id', 'child_of', categ_ids)])
        categ_ids += [x.id for x in child_categ_ids]
        
        products = product_pool.search([('barcode', '=', False), ('categ_id', 'in', categ_ids)])
        product_temp_ids = []
        if len(products):
            for product in products:
                product_temp_ids.append(product.product_tmpl_id.id)
                categ = categ_pool.browse(product.categ_id.id)
                latest_parent_code = categ_pool.get_latest_parent(categ)
                
                code = False
                if latest_parent_code == 'HB':
                    code = system_sequence_obj.get_current_sequence('product_barcode')
                 
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
                
                if code:
                    barcode = sequence_obj.seq_generate_ean13(code)
                    cr.execute('''
                    UPDATE product_product
                    SET barcode='%s'
                    WHERE id=%s
                    '''%(barcode, product.id))
        
#         if len(product_temp_ids):      
#             view = self.env.ref('product.product_template_kanban_view')
#             return {
#                 'name': _('Product'),
#                 'context': self._context,
#                 'view_type': 'form',
#                 'view_mode': 'kanban,form',
#                 'res_model': 'product',
#                 'views': [(view.id, 'kanban')],
#                 'domain': [('id', 'in', product_temp_ids)],
#                 'type': 'ir.actions.act_window',
#                 }
        
        return {'type': 'ir.actions.act_window_close'} 
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
