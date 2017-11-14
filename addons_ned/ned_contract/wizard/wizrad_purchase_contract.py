# -*- coding: utf-8 -*-

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

class WizardReportGainLoss(models.TransientModel):
    _name = "wizard.report.gain.loss"
    
    from_date =fields.Date(string="From Date")
    to_date =fields.Date(string="To Date")
    picking_type_id = fields.Many2one('stock.picking.type',string="Tram")
    
    
    @api.multi
    def create_gain_loss(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'wizard.report.gain.loss'
        data['form'] = self.read([])[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'mau_hao_hut_tram_report' , 'datas': data}
    
    
class wizard_purchase_contract(models.TransientModel):
    _inherit = "wizard.purchase.contract"
    
    
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
                     'product_qty':line.contract_id.qty_received - line.contract_id.total_qty_fixed,
                     'purchase_contract_id':line.contract_id.id,
                     'qty_received':line.contract_id.qty_received or 0.0,
                     'total_qty_fixed': line.contract_id.total_qty_fixed or 0.0,
                     'qty_unreceived': line.contract_id.qty_received - product_remain_qty or 0.0,
                     'product_remain_qty':line.product_qty - product_remain_qty
                     }))
            res.update({'contract_line_ids':val})
        return res
    
    @api.multi
    def button_convert(self):
        
        npe_nvp_relation = self.env['npe.nvp.relation']
        
        for line in self.contract_line_ids:
            if line.qty_received < line.product_qty+ line.total_qty_fixed:
                raise UserError('Cannot create a NVP if Qty Received > Fixed + Qty Fix')
        origin =''
        for line in self._context.get('active_ids'):
            origin += self.env['purchase.contract'].browse(line).name
            origin +=';'
            
        active_id = self._context.get('active_id')
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        npe = self.env['purchase.contract'].browse(active_id)
        npe_line = npe.contract_line[0]
        new_id = npe.copy({'warehouse_id':warehouse_id.id, 'name': 'New','nvp_ids':[],
            'contract_line':[], 'type':'purchase', 'npe_contract_id':active_id,'origin':origin})
        # ràng buộc dữ liệu
        
        for line in self.contract_line_ids:
            vals ={
                   'npe_contract_id':line.purchase_contract_id.id,
                   'contract_id':new_id.id,
                   'product_qty':line.product_qty or 0.0,
                   'type':'fixed'
                   }
            npe_nvp_relation.create(vals)
                    
        sql ='''
            select product_id,sum(product_qty) product_qty 
            FROM wizard_purchase_contract_line 
            WHERE contract_id = %s
            Group By product_id
        '''%(self.id)
        self.env.cr.execute(sql)
        for r in self.env.cr.dictfetchall():
            npe_line.copy({'product_qty':r['product_qty'],'price_unit':self.price_unit ,'contract_id':new_id.id})
            new_id.qty_received += r['product_qty']
            
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
    
    


class wizard_purchase_contract_line(models.TransientModel):
    _inherit = "wizard.purchase.contract.line"
    
    qty_received = fields.Float(string ='Received',digits=(12, 0))
    total_qty_fixed = fields.Float(string ='Fixed',digits=(12, 0))
    qty_unreceived = fields.Float(string ='Unfixed',digits=(12, 0))
    
