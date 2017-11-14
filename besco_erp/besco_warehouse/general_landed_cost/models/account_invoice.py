# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from openerp import api, fields, models, _


class AccountVoucher(models.Model):
    _inherit = "account.voucher"
    
    is_landed_cost = fields.Boolean('is_landed_cost',default=False)

class account_voucher_line(models.Model):
    _inherit = 'account.voucher.line'
    
    @api.one
    @api.depends('price_unit', 'tax_ids', 'quantity', 'product_id', 'voucher_id.currency_id')
    def _compute_subtotal(self):
        self.price_subtotal = self.quantity * self.price_unit
        if self.tax_ids:
            taxes = self.tax_ids.compute_all(self.price_unit, self.voucher_id.currency_id, self.quantity, product=self.product_id, partner=self.voucher_id.partner_id)
            self.price_subtotal = taxes['total_excluded']
            self.price_included = taxes['total_included']
            
    price_subtotal = fields.Monetary(string='Amount',
        store=True, readonly=True, compute='_compute_subtotal')
    
    price_included = fields.Monetary(string='Amount Include',
        store=True, readonly=True, compute='_compute_subtotal')
    
class account_invoice(models.Model):
    _inherit = "account.invoice"
    
    #kiet: Hàm Phân bổ chi phí:
    
    def _prepare_distribution_line(self, move,distribution_id, context=None):
        context = context or {}
        return {
            'distribution': distribution_id,
            'move_id': move.id,
        }
    
    @api.multi
    def action_view_invoice(self):
        invoice_ids = self.mapped('invoice_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('account.action_invoice_tree1')
        list_view_id = imd.xmlid_to_res_id('account.invoice_tree')
        form_view_id = imd.xmlid_to_res_id('account.invoice_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(invoice_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
        elif len(invoice_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = invoice_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
    @api.multi
    def distribution(self):
        this = self
        distribution_ids = self.env['purchase.cost.distribution'].search([('invoice_id', '=', this.id)])
        if distribution_ids:
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('general_landed_cost.action_purchase_cost_distribution')
            list_view_id = imd.xmlid_to_res_id('general_landed_cost.view_purchase_cost_distribution_tree')
            form_view_id = imd.xmlid_to_res_id('general_landed_cost.purchase_cost_distribution_form')
    
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            if len(distribution_ids) > 1:
                result['domain'] = "[('id','in',%s)]" % distribution_ids.id
            elif len(distribution_ids) == 1:
                result['views'] = [(form_view_id, 'form')]
                result['res_id'] = distribution_ids.id
            return result
        
        else:
            fiels_list =['currency_id', 'total_weight', 'total_volume', 'company_id', 'note', 'state', 'amount_total', 
                        'cost_lines', 'date', 'total_purchase', 'name', 'expense_lines', 'total_uom_qty', 'total_expense']
            res = self.env['purchase.cost.distribution'].default_get(fiels_list)
            res['invoice_id'] = this.id
            distribution_id = res = self.env['purchase.cost.distribution'].create(res)
            
            for picking in this.picking_ids:
                for move in picking.move_lines:
                    self.env['purchase.cost.distribution.line'].create(self._prepare_distribution_line(move,distribution_id))
            
                
            imd = self.env['ir.model.data']
            action = imd.xmlid_to_object('general_landed_cost.action_purchase_cost_distribution')
            list_view_id = imd.xmlid_to_res_id('general_landed_cost.view_purchase_cost_distribution_tree')
            form_view_id = imd.xmlid_to_res_id('general_landed_cost.purchase_cost_distribution_form')
    
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
                'target': action.target,
                'context': action.context,
                'res_model': action.res_model,
            }
            if len(distribution_id) > 1:
                result['domain'] = "[('id','in',%s)]" % distribution_id
            elif len(distribution_id) == 1:
                result['views'] = [(form_view_id, 'form')]
                result['res_id'] = distribution_id
            return result
    
    
    @api.one
    def _landed_cost_line(self):
        result = {}
        if not self.id: 
            return result
        sql ='''
                SELECT ai.id, pcdl.id 
                FROM account_invoice ai join stock_invoice_rel sir on ai.id = sir.invoice_id
                    JOIN purchase_cost_distribution_line pcdl on sir.picking_id = pcdl.picking_id
                WHERE ai.id = %s 
        '''%(self.id)
        
        self.env.cr.execute(sql)
        res = self.env.cr.fetchall()
        landed_cost_ids = []
        for r in res:
            landed_cost_ids.append(r[1])
        self.landed_cost_ids = self.env['purchase.cost.distribution.line'].browse(landed_cost_ids)
    
    # Kiet: add Related landed cost Invoice
    landed_cost_ids = fields.One2many('purchase.cost.distribution.line', 
                                      compute='_landed_cost_line', 
                                      string='Landed Cost Distribution', readonly=True)
    is_landed_cost = fields.Boolean(string='Is Landed Cost', default=False)