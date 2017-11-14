# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.relativedelta import relativedelta

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
from openerp.exceptions import UserError, RedirectWarning, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time


class AccountInvoice(models.Model):
    _inherit = "account.invoice" 
    
    purchase_contract_id = fields.Many2one('purchase.contract', string='Purchase Contract')
    

class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
    
    @api.depends('invoice_ids')
    def _compute_invoice(self):
        for order in self:
            invoices = self.env['account.invoice']
            moves = (order.invoice_ids.filtered(lambda r: r.state != 'cancel'))
            invoices |= moves
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)
            

    invoice_ids = fields.One2many('account.invoice', 'purchase_contract_id' , 'Invoiced', readonly=True)
    invoice_count = fields.Integer(compute='_compute_invoice', string='Invoiced', default=0)

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
