# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID

class CountryState(osv.osv):
    _inherit = 'res.country.state'

    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        if context.get('state_country', False):
            user = self.pool.get('res.users').browse(cr, uid, uid)
            if user.company_id and user.company_id.country_id:
                arg = ('country_id', '=', user.company_id.country_id.id)
                args.append(arg)
        return super(CountryState, self).search(cr, uid, args, offset, limit, order, context=context, count=count)

    _columns = {
        'short_name': fields.char('Short Name', required=True),
    }
