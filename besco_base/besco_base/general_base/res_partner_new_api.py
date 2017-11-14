# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    property_purchase_currency_id = fields.Many2one(
        'res.currency', string="Supplier Currency", company_dependent=True,
        help="This currency will be used, instead of the default one, for purchases from the current partner")
    
    identification_id = fields.Char(string='Personal ID')
    identification_date_issue = fields.Date(string='ID Date Issue')
    identification_place_issue = fields.Char(string='ID Place Issue')
        
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('other', 'Other')], string='Gender')
    marital = fields.Selection([('married', 'Married'), ('single', 'Single'), ('divorced', 'Divorced')
                                 , ('widower', 'Widower')], string='Marital')
    partner_code = fields.Char(string='Partner Code')
    mobile = fields.Char(string='Mobile')
    phone = fields.Char(string='Phone')
    shortname = fields.Char(string='Short Name')
    
    @api.one
    @api.constrains('email','mobile','phone','identification_id','vat','ref','partner_code')
    def check_duplicate_data(self):
        for partner in self:
            if partner.email:
                exist_partner = self.search([('email', '=', partner.email),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("Email %s was exist. Duplicated from partner %s.")%(partner.email,exist_partner.name))
                
            if partner.mobile:
                exist_partner = self.search([('mobile', '=', partner.mobile),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("Mobile number %s was exist. Duplicated from partner %s.")%(partner.mobile,exist_partner.name))
             
            if partner.phone:
                exist_partner = self.search([('phone', '=', partner.phone),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("Phone number %s was exist. Duplicated from partner %s.")%(partner.phone,exist_partner.name))
             
            if partner.identification_id:
                exist_partner = self.search([('identification_id', '=', partner.identification_id),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("Personal ID %s was exist. Duplicated from partner %s.")%(partner.identification_id,exist_partner.name))
             
            if not partner.parent_id and partner.vat:
                exist_partner = self.search([('vat', '=', partner.vat),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("VAT %s was exist. Duplicated from partner %s.")%(partner.vat,exist_partner.name))
             
            if partner.ref:
                exist_partner = self.search([('ref', '=', partner.ref),('id','!=',partner.id)], limit=1)
                if exist_partner:
                    raise ValidationError(_("Internal number %s was exist. Duplicated from partner %s.")%(partner.mobile,exist_partner.name))
             
            if partner.partner_code:
                exist_partner = self.search([('partner_code', '=', partner.partner_code),('id','!=',partner.id)], limit=1)
                if exist_partner:                    
                    raise ValidationError(_("Partner Code %s was exist. Duplicated from partner %s.")%(partner.partner_code,exist_partner.name))

        
class res_partner_category(models.Model):
    _name = 'res.partner.category'
    _inherit = 'res.partner.category'
    
    #THANH: rm translation
    name = fields.Char('Category Name', required=True, translate=False)
    
class res_company(models.Model):
    _name = 'res.company'
    _inherit = "res.company"
    
    district_imported = fields.Boolean(string='Districts Imported', default=False)
    state_imported = fields.Boolean(string='States Imported', default=False)
    bank_imported = fields.Boolean(string='Banks Imported', default=False)
    
    #THANH: this field used to get data from Javascript (FE)
    short_name = fields.Char(related='partner_id.shortname', string='Short Name', store=False, readonly=True)
    
    @api.multi
    def name_get(self):
        #THANH: Show short name
        result = []
        for c in self:
            result.append((c.id, "%s" % (c.short_name or c.name)))
        return result
    