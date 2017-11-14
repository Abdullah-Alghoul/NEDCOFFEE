# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

LABEL_TYPE = [
    ('label_big', 'Big'),
    ('label_small', 'Small'),
]

class product_barcode_print(models.TransientModel):
    _name = 'product.barcode.print'
    _description = 'Product Barcode Print'

    qty = fields.Integer(string='Number of labels', default=1)
    product_ids = fields.Many2many('product.product', 'product_barcode_print_product_product_rel', 'product_id', 'wizard_id', 
                                   string='Products to print labels')
    label_type = fields.Selection(LABEL_TYPE, string='Label Type', default='label_big')
    
    
    @api.multi
    def print_report(self):
        context = self._context or {}
        datas = {'ids': context.get('active_ids', ['qty','product_ids'])}
        res = self.read(['qty', 'product_ids'])
        res = res and res[0] or {}
        datas['form'] = res
        datas['ids'] = [self.id]
        return self.env['report'].get_action(self, 'product_barcode_qweb.report_product_barcode', data=datas)
    
#     @api.multi
    def print_label(self, cr, uid, ids,context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, [], context=context)
        res = res and res[0] or {}
        datas['form'] = res
        if res.get('id',False):
            datas['ids']=[res['id']]
        if res['label_type'] == 'label_big':
            return {'type': 'ir.actions.report.xml', 'report_name': 'product_label' , 'datas': datas}
        else:
            return {'type': 'ir.actions.report.xml', 'report_name': 'product_label_smaller' , 'datas': datas}
    
#     def print_label_bigger(self, cr, uid, ids,context=None):
#         if context is None:
#             context = {}
#         datas = {'ids': context.get('active_ids', [])}
#         res = self.read(cr, uid, ids, [], context=context)
#         res = res and res[0] or {}
#         datas['form'] = res
#         if res.get('id',False):
#             datas['ids']=[res['id']]
#         return {'type': 'ir.actions.report.xml', 'report_name': 'product_label_bigger' , 'datas': datas}
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
