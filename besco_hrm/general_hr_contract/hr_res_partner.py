# -*- coding: utf-8 -*-
import openerp
from openerp import tools, api
from openerp.osv import osv, fields
from openerp.osv.expression import get_unaccent_wrapper
from openerp.tools.translate import _
from openerp.exceptions import UserError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

from xlrd import open_workbook
import os
from openerp import modules

class res_partner(osv.Model):
    _inherit = "res.partner"
    _columns = {
        'contract_code' : fields.char('Contract Code')
    }
    
