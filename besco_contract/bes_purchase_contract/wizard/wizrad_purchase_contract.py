# -*- coding: utf-8 -*-

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class wizard_purchase_contract(models.TransientModel):
    _name = "wizard.purchase.contract"
    _description = "Wizard Purchase Contract"

    purchase_contract_id = fields.Many2one('purchase.contract', required=False, readonly=True)
    date_order = fields.Date(string='Date Order')
    contract_line_ids = fields.One2many('wizard.purchase.contract.line', 'contract_id', 'Product Line', required=False)
    name = fields.Char('Name', size=128)
    price_unit = fields.Float(string='Price Unit', required=False)

    @api.multi
    def button_convert(self):
        npe_nvp_relation = self.env['npe.nvp.relation']
        
#         for line in self.contract_line_ids:
#             if line.product_qty > line.product_remain_qty:
#                 raise UserError('Cannot create a NVP if product Qty > product Remain Qty')
            
        active_id = self._context.get('active_id')
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        npe = self.env['purchase.contract'].browse(active_id)
        npe_line = npe.contract_line[0]
        new_id = npe.copy({'warehouse_id':warehouse_id.id, 'name': 'New','nvp_ids':[], 'contract_line':[], 'type':'purchase', 'npe_contract_id':active_id})
        
        # ràng buộc dữ liệu.
        
        
        for line in self.contract_line_ids:
            vals ={
                   'npe_contract_id':line.purchase_contract_id.id,
                   'contract_id':new_id.id,
                   'product_qty':line.product_qty or 0.0,
                   }
            npe_nvp_relation.create(vals)
                    
        sql ='''
            select product_id,price_unit, sum(product_qty) product_qty 
            FROM wizard_purchase_contract_line 
            WHERE contract_id = %s
            Group By product_id, product_uom,price_unit
        '''%(self.id)
        self.env.cr.execute(sql)
        for r in self.env.cr.dictfetchall():
            npe_line.copy({'product_qty':r['product_qty'],'price_unit':r['price_unit'] ,'contract_id':new_id.id})
            
        if new_id:                 
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('bes_purchase_contract.action_purchase_contract')
            form_view_id = imd.xmlid_to_res_id('action_purchase_contract.view_purchase_contract_form')
            list_view_id = imd.xmlid_to_res_id('action_purchase_contract.view_purchase_contract_tree')
            result = {
                    'name': action.name,
                    'help': action.help,
                    'type': action.type,
                    'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
                    'target': action.target,
                    'context': action.context,
                    'res_model': action.res_model,
                    'res_id': new_id.ids[0],
                    'views' : [(form_view_id, 'form')],
                }
        return result

    @api.model
    def default_get(self, fields):
        res = {}
        val = []
        sql ='''
            SELECT count(distinct partner_id)count_partner
            FROM purchase_contract
            WHERE id in (%s)
        '''%(','.join(map(str, self._context.get('active_ids'))))
        self.env.cr.execute(sql)
        for r in self.env.cr.dictfetchall():
            if r['count_partner']>1:
                raise UserError('You must select NPE with the same Vendor.')
            
        for active_id in self._context.get('active_ids'):
            contract_obj = self.env['purchase.contract'].browse(active_id)
            for line in contract_obj.contract_line:
                product_remain_qty =0.0
                for relation in  self.env['npe.nvp.relation'].search([('npe_contract_id','=',line.contract_id.id)]):
                    product_remain_qty += relation.product_qty or 0.0
                
                val.append((0, 0, {
                     'product_id':line.product_id.id,
                     'product_uom':line.product_uom.id,
                     'price_unit':line.price_unit or 0.0,
                     'product_qty':line.product_qty - product_remain_qty,
                     'purchase_contract_id':line.contract_id.id,
                     'product_remain_qty':line.product_qty - product_remain_qty
                     }))
            res.update({'contract_line_ids':val})
        return res
    
class wizard_purchase_contract_line(models.TransientModel):
    _name = "wizard.purchase.contract.line"
    _description = "Wizard Purchase Contract Line"
    
    @api.multi
    @api.depends('product_id')  
    def _product_remain_qty(self):
        for order in self:
            product_remain_qty = 0.0
            if order.purchase_contract_id:
                for relation in  self.env['npe.nvp.relation'].search([('npe_contract_id','=',order.purchase_contract_id.id)]):
                    product_remain_qty += relation.product_qty or 0.0
                
                order.product_remain_qty = order.product_qty - product_remain_qty
            
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], change_default=True, ondelete='restrict', required=True)
    product_uom = fields.Many2one('product.uom', string='UoM', required=True)
    product_qty = fields.Float(string='Contract Qty', digits=(16, 0), required=True, default=1.0)
    price_unit = fields.Float(string='Price Unit', required=False,digits=(16, 0))
    contract_id = fields.Many2one('wizard.purchase.contract', 'Purchase Contract', required=False)
    purchase_contract_id = fields.Many2one('purchase.contract', 'Purchase Contract', required=False)
    product_remain_qty = fields.Float(compute='_product_remain_qty', string='Product Remain', default=0,  store= True,digits=(16, 0))
    
    
