# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp import modules

class system_sequence(models.Model):
    _inherit = "system.sequence"
    
    picking_code = fields.Many2one('ir.sequence', string='Picking Code')    
    
class PackingTerms(models.Model):
    _name ="packing.terms"
    _order = 'id desc'
    
    name = fields.Char(string="Name")
    vietnamese = fields.Char(string="Vietnamese")
    english = fields.Char(string="English")
    
class MarketPrice(models.Model):
    _name ="market.price"
    _order = 'mdate desc'
    
    
    mdate =  fields.Date(string="MDate")
    interbankrate = fields.Float(string="Interbank Rate")
    price = fields.Float(string="Price")
    bankceiling =fields.Float(string="Bank Ceiling")
    note = fields.Char(string="Note")
    bank_floor = fields.Float(string="Bank Floor")
    eximbank = fields.Float(string="Eximbank")
    techcombank = fields.Float(string="Techcombank")
    acb_or_vietinbank = fields.Float(string="ACB or Vietinbank")
    commercialrate = fields.Float(string="Commercial Rate")
    exporter_faq_price = fields.Float(string="Exporter FAQ Price")
    privateDealer_faq_price = fields.Float(string="privateDealer faq price")
    liffe_month = fields.Char(string="LIFFE Month")
    liffe = fields.Char(string="LIFFE")
    g2difflocal = fields.Float(string="G2DiffLocal")
    g2difffob = fields.Float(string="G2DiffFOB")
    
    

class product_category(models.Model):
    _inherit = "product.category"
    
    property_stock_account_tem_categ = fields.Many2one('account.account',string="Stock Tem Payable")
    property_stock_cogs_export = fields.Many2one('account.account',string="Cogs export")
    

class ShippingLine(models.Model):
    _name = 'shipping.line' 
    _order = 'create_date desc, id desc'
    
    name = fields.Char(string='Shipping Line', required=True, copy=False, index=True)
    active = fields.Boolean(string="Active")
    
class NedCrop(models.Model):
    _name = 'ned.crop' 
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'create_date desc, id desc'
    
    name = fields.Char(string='Crop', required=True, copy=False, index=True, default='New')
    start_date = fields.Date('Start Date', required=True , select=True, copy=False)
    to_date = fields.Date('End Date', required=True , select=True, copy=False)
    description = fields.Text('Description', select=True, copy=False)
    state = fields.Selection([('current', 'Current'), ('previous', 'Previous')], string='Status', copy=False , required=True, default='current')
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    
    invietnamese = fields.Char(string='InVietnamese')
    moisture = fields.Float(string='Moisture')
    foreign_matter = fields.Float(string='Foreign Matter')
    
    mc =fields.Float(string='MC %')
    fm =fields.Float(string='FM %')
    bb =fields.Float(string='BB %')
    
    black = fields.Float(string='Black')
    broken = fields.Float(string='Broken')
    brown = fields.Float(string='Brown')
    eaten = fields.Float(string='Eaten')
    immature = fields.Float(string='Immature')
    cherry= fields.Float(string='Cherry')
    burned =fields.Float(string='Burned')
    mold =fields.Float(string='Mold')
    scr18 = fields.Float(string='Scr18')
    scr16 = fields.Float(string='Scr16')
    scr13 = fields.Float(string='Scr13')
    scr12 = fields.Float(string='Scr12')
    uscr12 = fields.Float(string='UScr12')
    defects = fields.Float(string='Defects')
    triage = fields.Float(string='Triage')
    cup_taste = fields.Char(string='Cup Taste')
    
    premium = fields.Integer(string='Premium')
    flag_standard_cost = fields.Boolean(string="Flag Standard Cost")
    default_code = fields.Char(related='product_variant_ids.default_code', string='Internal Reference', readonly=False, required=True)


class NedPacking(models.Model):
    _name = 'ned.packing'
    _order = 'id desc'

    name = fields.Char(string="Packing",size=256,required=True)
    capacity = fields.Float(string="Capacity",digits=(16,0))
    tare_weight = fields.Float(string="Tare weight",digits=(16,2))
    price = fields.Float(string="Price",digits=(16,0))
    Premium = fields.Float(string="Premium", digits=(16,2))
    active = fields.Boolean(string="Active",default=True)
    
class NedFumigation(models.Model):
    _name = 'ned.fumigation'
    _order = 'id desc'
    
    name = fields.Char(string="Fumigation",size=256,required=True)
        
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    default_code = fields.Char(string='Internal Reference', readonly=False, required=True)
    
    
    @api.multi
    def name_get(self):
        result = []
        for product in self:
            result.append((product.id, "%s" % ( product.default_code or '')))
        return result
    
class NedCertificate(models.Model):
    _name = 'ned.certificate'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'active desc, id desc'
    
    @api.model
    def _default_currency_id(self):
        currency_ids = self.env['res.currency'].search([], limit=1)
        return currency_ids
    
    name = fields.Char(string='Certificate', required=True, copy=False, index=True, default='New')
    code = fields.Char(string='Code', required=True, copy=False, index=True)
    premium = fields.Float(string='Premium', required=True, copy=False, index=True, default=0)
    currency_id = fields.Many2one("res.currency", string="Currency", required=True, default=_default_currency_id)
    description = fields.Text('Description', select=True, copy=False)
    active = fields.Boolean(string='Active', default=True, copy=False)


class SupplierMgt(models.Model):
    _name = 'supplier.mgt'
    
    date = fields.Date(string="Date")
    type_ned = fields.Selection([('normal', 'Normal'), ('partner', 'Partner')], string='Type', default='normal')
    repperson1 = fields.Char(string='Primary')
    repperson2 = fields.Char(string='Secondary')
    goods = fields.Selection([('FAQ', 'FAQ'), ('Graded', 'Graded'),('Partner','Partner'),('Stop trading','Stop trading')], string='Goods')
    ppkg = fields.Float(string='PPKg')
    
    estimated_annual_volume = fields.Float(string='Estimated Annual Volume')
    purchase_undelivered_limit = fields.Float(string='Purchase Undelivered Limit')
    property_evaluation = fields.Float(string='Property Evaluation')
    m2mlimit = fields.Float(string='M2MLimit')
    partnert_id = fields.Many2one('res.partner',string= 'Supplier',domain="[('supplier', '=', True)]")
    negative_m2m_loss_limit = fields.Float(string='Negative M2M loss Limit')
    delivery_at = fields.Selection([('Factory', 'Factory'), ('HCM', 'HCM'),('Station','Station'),
                                    ('Stop trading','Stop trading')], string='Delivery at')
    deposited = fields.Float(string='Deposited')

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    supplier_mgt_line = fields.One2many('supplier.mgt','partnert_id','Supplier Mgt')
    type_ned = fields.Selection([('normal', 'Normal'), ('partner', 'Partner')], string='Type', default='normal')
    repperson1 = fields.Char(string='RepPerson1')
    repperson2 = fields.Char(string='RepPerson2')
    goods = fields.Selection([('faq', 'FAQ'), ('grade', 'GRADE')], string='Goods')
    ppkg = fields.Float(string='PPKg')
    
    estimated_annual_volume = fields.Float(string='Estimated Annual Volume')
    purchase_undelivered_limit = fields.Float(string='Purchase Undelivered Limit')
    property_evaluation = fields.Float(string='Property Evaluation')
    m2mlimit = fields.Float(string='M2MLimit')
    district_id = fields.Many2one('res.district', string="District")
    

    
    
    tem_payable_account_id = fields.Many2one('account.account', 
        string="Tem payable account", 
        domain="[('internal_type', '=', 'payable')]",
        required=False)
    
    @api.multi
    @api.onchange('district_id')
    def onchange_district_id(self):
        if not self.district_id:
            self.update({'state_id': False})
            domain = {'domain': {'state_id': []}}
            return {'domain':domain}
        
        values = {'state_id': self.district_id.state_id.id or False}
        self.update(values)
        
        domain = {'domain': {'state_id': [('id', '=', self.district_id.state_id.id)]}}
        return {'domain':domain}