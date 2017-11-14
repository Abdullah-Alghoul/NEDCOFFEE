# -*- coding: utf-8 -*-
from Code128 import Code128
import base64
from StringIO import StringIO

import time
from openerp.osv import osv
from openerp.report import report_sxw


class product_barcode_print(report_sxw.rml_parse):
    
    def _getLabelRows(self, form):
        product_obj = self.pool.get('product.product')
        data = []
        product_ids = form['product_ids']
        if not product_ids:
            return {}
        
        products_data = product_obj.read(self.cr, self.uid, product_ids, ['name','barcode','list_price'])
        for product in products_data:
            if product['barcode']:
                i = 0
                label_row = []
                for product_row in range(form['qty']):
                    i += 1
                    label_data = {
                        'name': product['name'],
                        'barcode': product['barcode'],
                        'price': product['list_price'],
                    }
                    label_row.append(label_data)
                    if i == 3:
                        i = 0
                        data.append(label_row)
                        label_row = []
                        
                data.append(label_row)
                
        if data:
            return data
        else:
            return {}

    def _generateBarcode(self, barcode_string):  #, height, width):
        fp = StringIO()
        #generate('CODE39', barcode_string, writer=ImageWriter(), add_checksum=False, output=fp)
        #barcode_data = base64.b64encode(fp.getvalue())
        #return '<img style="width: 25mm;height: 7mm;" src="data:image/png;base64,%s" />'%(barcode_data)
        #return barcode_data
        Code128().getImage(barcode_string, path="/opt/odoo/barcode/").save(fp,"PNG")
        barcode_data = base64.b64encode(fp.getvalue())
        return barcode_data

    def __init__(self, cr, uid, name, context):
        super(product_barcode_print, self).__init__(cr, uid, name, context=context)
        self.total = 0.0
        self.qty = 0.0
        self.total_invoiced = 0.0
        self.discount = 0.0
        self.total_discount = 0.0
        self.localcontext.update({
            'time': time,
            'getLabelRows':self._getLabelRows,
            'generateBarcode':self._generateBarcode,
        })


class report_product_barcode_print(osv.AbstractModel):
    _name = 'report.product_barcode_qweb.report_product_barcode'
    _inherit = 'report.abstract_report'
    _template = 'product_barcode_qweb.report_product_barcode'
    _wrapped_report_class = product_barcode_print
    
class report_product_label_print(osv.AbstractModel):
    _name = 'report.product_barcode_qweb.report_product_label'
    _inherit = 'report.abstract_report'
    _template = 'product_barcode_qweb.report_product_label'
    _wrapped_report_class = product_barcode_print

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
