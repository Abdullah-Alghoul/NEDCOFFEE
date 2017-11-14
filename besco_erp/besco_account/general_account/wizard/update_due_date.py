from openerp import models, fields, api, _
from openerp.exceptions import UserError


class UpdateDuedate(models.TransientModel):
    _name = "update.duedate"
    
    due_date = fields.Date('Due Date', required=True)
    
    @api.multi
    def update(self):
        context = dict(self._context or {})
        invoices = self.env['account.invoice'].browse(context.get('active_ids'))
        for invoice in invoices:
            invoice.date_due = self.due_date
        return True
    