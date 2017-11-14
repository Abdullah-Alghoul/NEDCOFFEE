# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from collections import OrderedDict

import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.exceptions import UserError, AccessError

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
     
    def do_transfer(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        res = super(stock_picking, self).do_transfer(cr, uid, ids, context=context)
          
        for picking in self.browse(cr, uid, ids, context=context):
            # Kim: Update field move_lines on mrp_production
            if picking.production_id and picking.picking_type_id.code == 'production_out' and picking.location_id.usage == 'internal':
                cr.execute(''' DELETE FROM mrp_production_move_ids WHERE production_id = %s 
                        And move_id in (select stm.id FROM stock_move stm join stock_picking sp on stm.picking_id=sp.id WHERE sp.id=%s);
                ''' % (picking.production_id.id, picking.id))
                cr.execute('''INSERT INTO mrp_production_move_ids
                SELECT sp.production_id, stm.id FROM stock_move stm join stock_picking sp on stm.picking_id=sp.id WHERE sp.id=%s
                ''' % (picking.id))
        return res
