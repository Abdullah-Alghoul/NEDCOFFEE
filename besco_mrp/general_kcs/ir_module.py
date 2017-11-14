# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

class ir_module_module(osv.osv):
    _inherit = "ir.module.module"
    
    def init(self, cr):
        cr.execute("update ir_module_module set overwrite=True where name='general_kcs'")
        return True