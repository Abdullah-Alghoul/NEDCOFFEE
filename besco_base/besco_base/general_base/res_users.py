# -*- coding: utf-8 -*-
import openerp.addons.decimal_precision as dp
from datetime import date, datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.exceptions import UserError, ValidationError
from openerp import SUPERUSER_ID

from openerp.addons.general_base import amount_to_text_vn
from openerp.addons.general_base import amount_to_text_en

class ResUsers(models.Model):
    _inherit = "res.users"
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    
    @api.constrains('employee_id')
    def _check_employee_id(self):
        for this in self:
            if this.employee_id:
                user_id = self.search([('employee_id','=',this.employee_id.id),('id','!=',this.id)], limit=1) or False
                if user_id:
                    raise UserError(_("Configuration error!\nEmployee has been set up for users '%s'.")%(this.name))
    
    def amount_to_text(self, nbr, lang='vn'):
        if lang == 'vn':
            return amount_to_text_vn.amount_to_text(nbr, lang=lang)
        else:
            return amount_to_text_en.amount_to_text(nbr, 'en',lang)
    
    @api.model
    def create(self, vals):         
        new_user = super(ResUsers, self).create(vals)
        #THANH: Update company partner into related partner of this user
        update_related_partner = {'email': new_user.login or False}
        if not new_user.share: #THANH: check if user is internal user, not portal user then auto update parent is company partner
            update_related_partner.update({'parent_id': new_user.company_id.partner_id.id or False})
        new_user.partner_id.write(update_related_partner)
        
        #THANH: update user_id to employee exist
        if new_user.employee_id:
            new_user.employee_id.write({'user_id': new_user.employee_id.id})
        return new_user
    
    @api.multi
    def write(self, vals):
        for user in self:
            if vals.get('employee_id', False):
                user.employee_id.write({'user_id': vals['employee_id'] or False})
        res = super(ResUsers, self).write(vals)
        
        for user in self:
            if not user.share and not user.partner_id.parent_id: #THANH: check if user is internal user, not portal user then auto update parent is company partner
                user.partner_id.write({'parent_id': user.company_id.partner_id.id or False})
        return res 
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
