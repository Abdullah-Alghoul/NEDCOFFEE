# -*- coding: utf-8 -*-
from openerp import api, fields, models, _

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    property_vendor_advance_acc_id = fields.Many2one('account.account', company_dependent=True,
        string="Vendor advance account", oldname="property_vendor_advance_acc",
        domain="[('internal_type', '=', 'payable'), ('deprecated', '=', False)]",
        required=False)
    property_customer_advance_acc_id = fields.Many2one('account.account', company_dependent=True,
        string="Customer advance account", oldname="property_customer_advance_acc",
        domain="[('internal_type', '=', 'receivable'), ('deprecated', '=', False)]",
        required=False)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
