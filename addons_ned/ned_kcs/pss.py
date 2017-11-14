# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from openerp import SUPERUSER_ID
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class PssManagement(models.Model):
	_name="pss.management"

	name = fields.Char(string="PSS name")
	shipping_id = fields.Many2one("shipping.instruction", string="SI No.")
	created_date =  fields.Date(string="Date")
	date_sent = fields.Date(string="Date sent")
	pss_status = fields.Selection([('pending', 'Pending'), ('sent', 'Sent'), ('approved', 'Approved'), ('rejected','Rejected')], string="PSS status")
	date_result = fields.Char(string="Date result")
	product_id = fields.Many2one("product.product", string="Product")
	buyer_ref = fields.Char(string="Buyer ref.")
	lot_quantity = fields.Float(string="Quantity")
	cont_quantity = fields.Float(string="Cont. qty.")
	mc = fields.Float(string="MC")
	fm = fields.Float(string="FM")
	black = fields.Float(string="Black")
	broken = fields.Float(string="Broken")
	brown = fields.Float(string="Brown")
	moldy = fields.Float(string="Moldy")
	burned = fields.Float(string="Burned")
	scr18 = fields.Float(string="Screen 18")
	scr16 = fields.Float(string="Screen 16")
	scr13 = fields.Float(string="Screen 13")
	scr12 = fields.Float(string="Screen 12")
	blscr12 = fields.Float(string="Below scr.12")
	stack = fields.Many2one("stock.stack", string="Stack no.")
	ref_no = fields.Char(string="Reference")
	inspector = fields.Char(string="Inspector")
	buyer_comment = fields.Char(string="Buyer's comment")
	our_comment = fields.Char(string="Our comment")
	note = fields.Char(string="Note")
	qc_staff = fields.Char(string="QC staff")
	partner_id = fields.Many2one("res.partner", string="Customer")

	# function to load SI information
	@api.multi
	def load_si_info(self):
		if self.id:
			self.partner_id = self.shipping_id.partner_id
			self.product_id = self.shipping_id.product_id
		# self.write(val)
		return True
        # if self.contract_id:
        #     name = 'SI-' + self.contract_id.name
        #     val ={
        #           'name':name,
        #           'port_of_loading':self.contract_id.port_of_loading and self.contract_id.port_of_loading.id or False,
        #           'port_of_discharge':self.contract_id.port_of_discharge and self.contract_id.port_of_discharge.id or False,
        #           'shipment_date':self.contract_id.shipment_date or False,
        #           'incoterms_id':self.contract_id.incoterms_id.id  or False
        #           }
        #     self.write(val)
            
        #     self.partner_id = self.contract_id.partner_id.id
        #     self.env.cr.execute('''DELETE FROM shipping_instruction_line WHERE shipping_id = %s''' % (self.id))
        #     for contract in self.contract_id.contract_line:
        #         var = {
        #                'certificate_id':contract.certificate_id.id,
        #                'packing_id': contract.packing_id.id,
        #                'name': contract.name or False, 'shipping_id': self.id or False, 'partner_id': self.partner_id.id or False,
        #                'tax_id': [(6, 0, [x.id for x in contract.tax_id])] or False, 'company_id': self.company_id.id or False,
        #                'price_unit': contract.price_unit or 0.0, 'product_id': contract.product_id.id or False, 
        #                'product_qty': contract.product_qty or 0.0,
        #                'product_uom': contract.product_uom.id or False, 'state': 'draft', 
        #                'certificate_id': contract.certificate_id.id or False}
        #         self.env['shipping.instruction.line'].create(var)
        

