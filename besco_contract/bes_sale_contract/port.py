# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class BesPort(models.Model):
    _name = "bes.port"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    name = fields.Char(string='Prot', required=True, copy=False, index=True, default='New')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip', size=24, change_default=True)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", 'State')
    country_id = fields.Many2one('res.country', 'Country')
    email = fields.Char('Email')
    phone = fields.Char('Phone')
    fax = fields.Char('Fax')
    
    @api.multi
    @api.onchange('state_id')
    def onchange_state(self):
        if not self.state_id:
            return 
        value = {'country_id': self.state_id.country_id.id}
        self.update(value)
        
class ResPartner(models.Model):
    _inherit = "res.partner"
    
    transfer = fields.Boolean(string='Is a Transporters')
    
    
class DeliveryPlace(models.Model):
    _name = "delivery.place"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    province_id = fields.Many2one("res.country.state", 'Province')
    name = fields.Char(string='Place Name', required=True, default="New")
    description = fields.Text(string='Description', required=False)
    type = fields.Selection([('sale', 'Sale'),('transport', 'Transport'), ('purchase', 'Purchase'),
                             ('port', 'Port'),('Loading Place', 'Loading Place')], string='Type', default='transport')
    partner_id = fields.Many2one('res.partner', string='Customer', required=False, domain=[('transfer', '=', True)])
    transit_cost = fields.Float(string='Transit Cost', default=0.0) 
    currency_id = fields.Many2one("res.currency", string="Currency", default=_default_currency_id)
    account_ids = fields.One2many('delivery.account','place_id',string="Account")
    active = fields.Boolean(string='Active', default=True)
    phone = fields.Char(string="Phone",size=128)
    fax = fields.Char(string="Fax",size=128)
    address =  fields.Char(string="Address",size=128)
    recipient = fields.Char(string="Recipient",size=128)
    
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.update({'province_id': False})
            return
        values = {
            'currency_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.currency_id.id or False,
            'province_id': self.partner_id.state_id and self.partner_id.state_id.id or False 
            }
        self.update(values)


class DeliveryAccount(models.Model):
    _name = "delivery.account"
    
    debit_acc_id = fields.Many2one('account.account', string='Debit Acc', required=True)
    credit_acc_id = fields.Many2one('account.account', string='Credit Acc', required=True)
    values = fields.Float(string='Values',required=True)
    description = fields.Char(string='Description',size=256)
    place_id = fields.Many2one('delivery.place', string='Account', required=False,)
    