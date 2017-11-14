# -*- coding: utf-8 -*-
from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp import fields, models
from openerp.tools.translate import _
from openerp.exceptions import UserError
from datetime import datetime, timedelta, date
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
from docutils.nodes import document

class VProcessingBatchlist(models.Model):
    _name = 'v.processing.batch.list'
    _description = 'Processing List'
    _auto =False

    mrp_id = fields.Many2one('mrp.production', string = 'MRP')
    batch_type = fields.Char(string = 'Batch type')
    date_planned = fields.Datetime(string = 'Start date')
    date_finished = fields.Datetime(string = 'End date')
    issued = fields.Float(string = 'Input qty.', digits=(12, 0))
    receivednet = fields.Float(string = 'Output qty.', digits=(12, 0))
    wip = fields.Float(string = 'WIP', digits=(12, 0))
    notes = fields.Text(string = 'Notes')

   #  def init(self, cr):
   #  	tools.drop_view_if_exists(cr, 'v_processing_batch_list')
   #   	cr.execute("""
			# CREATE OR REPLACE VIEW public.v_processing_batch_list AS
			# 	SELECT 
			# 	 	ROW_NUMBER() OVER() id,
			# 	 	mrp.name AS mrp,
			# 	    bom.code AS batch_type,
			# 	    mrp.date_planned,
			# 	    mrp.date_finished,
			# 	    mrp.product_issued AS issued,
			# 	    mrp.product_received AS receivednet,
			# 	    mrp.product_balance AS wip,
			# 	    mrp.notes,
			# 	    mrp.id as mrp_id
			#    	FROM mrp_production mrp
			#     JOIN mrp_bom bom ON mrp.bom_id = bom.id;
			#         """)
