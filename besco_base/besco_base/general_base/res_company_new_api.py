# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class ResCompany(models.Model):
    _inherit = "res.company"
    
    
    @api.onchange('country_id')
    def _onchange_country(self):
        self.state_id = False
        self.district_id = False
        self.ward_id = False
        
    @api.onchange('state_id')
    def _onchange_state(self):
        self.district_id = False
        self.ward_id = False
        
    @api.onchange('district_id')
    def _onchange_district(self):
        self.ward_id = False