# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import time

class wizard_report_stock_quanlity(osv.osv_memory):
    _name = "wizard.report.stock.quanlity"
    _columns = {
        'date_from': fields.date(string="Date from"),
        'date_to': fields.date(string="Date to"),
        'production_id': fields.many2one("mrp.production", "Production"),
        'type':fields.selection([
                        ('all','All'),
                        ('Onhand','Onhand')], string='Type', required=True, default="Onhand" ),
        'product_id':fields.many2one("product.product", "Product"),
    }
    _defaults = { 
            'date_from': lambda *a: time.strftime('%Y-%m-%d'),
            'date_to': lambda *a: time.strftime('%Y-%m-%d'),
        }  
    
    def printf_report(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.report.stock.quanlity'
        datas['form'] = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_stock_with_quality_details' , 'datas': datas} 
    