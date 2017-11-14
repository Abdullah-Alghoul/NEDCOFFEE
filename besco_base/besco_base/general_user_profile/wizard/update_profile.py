# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class update_profile(osv.osv_memory):
    _name = "update.profile"
    _columns = {
    }
    
    def update_profile(self, cr, uid, ids, context=None):
        user_ids = self.pool.get('res.users').search(cr, uid, [])
        self.pool.get('profile').update_groups(cr, uid, user_ids)
        return {'type': 'ir.actions.act_window_close'}
    
update_profile()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
