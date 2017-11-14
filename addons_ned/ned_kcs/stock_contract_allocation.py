from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from datetime import datetime
import time
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
#

class StockContractAllocation(models.Model):
	_name = "stock.contract.allocation"

	allocation_date = fields.Datetime(string='Date')
	stack_no = fields.Many2one('stock.stack', string='Stack')
	shipping_id = fields.Many2one('shipping.instruction', string='SI no.')
	allocating_quantity = fields.Float(string='Allocating quantity')

	@api.multi
	def load_stack_info(self):
		if self.id:
			self.allocating_quantity = self.stack_no.remaining_qty
			# self.product_id = self.shipping_id.product_id
			# self.write(val)
		return True