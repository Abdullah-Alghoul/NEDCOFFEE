# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.float_utils import float_compare, float_round

from openerp.tools.misc import formatLang
import time
from openerp.tools import append_content_to_html
from openerp import SUPERUSER_ID
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    scale_ids = fields.One2many('stock.scale','picking_id',string="Scale")
        
        
class StockScale(models.Model):
    _name = 'stock.scale'
    
    @api.model
    def create(self, vals):
        if vals.get('picking_id',False):
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            vals['product_id'] = picking.product_id.id
            if picking.state =='draft':
                picking.action_confirm()
        result = super(StockScale, self).create(vals)
        return result
    
    picking_id = fields.Many2one('stock.picking',string="Scale")
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float('Product qty')
    bag_no = fields.Float('Bag nos.')
    tare_weight  = fields.Float('Tare Weight ')
