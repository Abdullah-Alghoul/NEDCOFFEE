# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time

class wizard_report_partner_balance_confirmation(osv.osv_memory):
    _name = "wizard.report.partner.balance.confirmation"
    _columns = {
        'partner_id': fields.many2one("res.partner", "Supplier"),
        'date':fields.date("Date")
    }
    
    def printf_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.report.partner.balance.confirmation'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_partner_balance_confirmation' , 'datas': datas} 

