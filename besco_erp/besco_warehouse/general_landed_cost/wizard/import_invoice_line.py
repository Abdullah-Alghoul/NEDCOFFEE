# -*- coding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
# from openerp import models, fields, api
from openerp.osv import fields, osv

class ImportInvoiceLine(osv.osv_memory):
    _name = "import.invoice.line.wizard"
    _description = "Import supplier invoice line"
    
    _columns = {
        'supplier': fields.many2one('res.partner', string='Supplier', required=True,
            domain="[('supplier',  '=', True)]"),
        
        'invoice': fields.many2one('account.voucher', string="Invoice", required=True,
            domain="[('partner_id', '=', supplier),('is_landed_cost', '=', False),"
                   "('state', '=', ['posted'])]"),
        
#         'invoice_line': fields.many2one('account.invoice.line', string="Invoice line",
#             required=True, domain="[('invoice_id', '=', invoice),('is_landed_cost', '=', False)]"),
#         
#         'expense_type': fields.many2one('purchase.expense.type', string='Expense type',
#             required=True),
    }

#     @api.multi
#     def action_import_invoice_line(self):
#         self.ensure_one()
#         self.env['purchase.cost.distribution.expense'].create({
#             'distribution': self.env.context['active_id'],
#             'invoice_line': self.invoice_line.id,
#             'ref': self.invoice_line.name,
#             'expense_amount': self.invoice_line.price_subtotal,
#             'type': self.expense_type.id,
#         })
    def action_import_invoice_line(self, cr, uid, ids, context=None):
        context = context or {}
        this = self.browse(cr, uid, ids[0])
        expense_type = self.pool.get('purchase.expense.type')
        expense_ids = expense_type.search(cr,uid,[('default_expense','=',True)])
        
        for line in this.invoice.line_ids:
            self.pool.get('purchase.cost.distribution.expense').create(cr,uid,{
                'distribution': context['active_id'],
                'invoice_line': line.id,
                'ref': line.name,
                'expense_amount': line.price_included,
                'type': expense_ids[0],
            })
    
