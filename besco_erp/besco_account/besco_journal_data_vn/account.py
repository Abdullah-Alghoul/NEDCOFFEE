# -*- coding: utf-8 -*-
# #############################################################################
# 
# #############################################################################
from openerp import _, api, fields, models, SUPERUSER_ID

class ir_sequence(models.Model):
    _inherit = 'ir.sequence'
    
    def init(self, cr):
#         cr.execute('''
#         UPDATE ir_sequence
#         SET implementation='standard'
#         WHERE implementation='no_gap';
#         
#         UPDATE ir_sequence
#         SET use_date_range=False
#         WHERE use_date_range=True;
#         ''')
        return True
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
