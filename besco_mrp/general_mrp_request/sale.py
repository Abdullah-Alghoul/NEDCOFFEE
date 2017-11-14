# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.tools import float_is_zero
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    @api.depends('mrp_request_ids')
    def _compute_mrp_request(self):
        for order in self:
            requests = self.env['mrp.request'] 
            for line in order.mrp_request_ids: 
                requests = (line.filtered(lambda r: r.state != 'cancel'))
            order.request_count = len(requests)
            order.mrp_request_ids = requests
    
    request_count = fields.Integer(string='# of Requirement', compute='_compute_mrp_request', readonly=True)
    mrp_request_ids = fields.One2many('mrp.request', 'sale_id', string='Produced Request', readonly=True, copy=False)
    
    
    @api.multi
    def action_view_mrp_request(self):
        mrp_request_ids = self.mapped('mrp_request_ids')
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('general_mrp_request.action_mrp_request')
        list_view_id = imd.xmlid_to_res_id('general_mrp_request.view_mrp_request_tree')
        form_view_id = imd.xmlid_to_res_id('general_mrp_request.view_mrp_request_form')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(mrp_request_ids) > 1:
            result['domain'] = "[('id','in',%s)]" % mrp_request_ids.ids
        elif len(mrp_request_ids) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = mrp_request_ids.ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    mrp_request_id = fields.Many2one('mrp.request', string='Produced Request', copy=False)
    
    @api.multi
    def button_create_mrp_request(self):
        if self.mrp_request_id and self.mrp_request_id.state != 'cancel':
            raise UserError(_('Produced Requirements has been generated.\nYou can not create new a sale Produced Requirements.'))
        vals = {}
        var = {'name':'New', 'state':'draft', 'sale_id': self.order_id.id,
               'sale_line_id': self.id, 'product_id': self.product_id.id,
               'create_date':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
               'product_qty': self.product_uom_qty, 'product_uom': self.product_uom.id}
        new_id = self.env['mrp.request'].create(var)
        self.write({'mrp_request_id': new_id.id})
        
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('sale.action_orders')
        form_view_id = imd.xmlid_to_res_id('sale.view_order_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'res_id':  self.order_id.id
            }
        return result
        
        
