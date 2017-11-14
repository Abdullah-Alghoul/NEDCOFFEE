# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################

from openerp import api, fields, models, _
from openerp.tools import float_is_zero, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang

from openerp.exceptions import UserError, RedirectWarning
import openerp.addons.decimal_precision as dp
import time

class sale_promo_header(models.Model):
    _description = "Promotion Header"
    _inherit = ['mail.thread']
    _name ="sale.promo.header"
     
    @api.model
    def _default_requested_by(self):
        return self.env.uid
    
    company_id = fields.Many2one('res.company', string='Company', required=False,
                                 default=lambda self: self.env['res.company']._company_default_get('sale.promo.header'))
    name = fields.Char(string='Name', size=64, required=True)
    description = fields.Char(string='Description', size=128, required=False)              
    list_type = fields.Selection([('PRO', 'Promotion'),
                                   ('DIS', 'Discount')], string='Type', required=True)                                                                
    active = fields.Boolean(string='Active', default=True, required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False)
    
    start_date_active = fields.Date(string='From Date', required=True)
    end_date_active = fields.Date(string='To Date', required=True)
    
    start_hour = fields.Float(string='Start Hour', required=True)
    end_hour = fields.Float(string='End Hour', required=True)
    
#     repeating_flag = fields.Boolean(string='Repeat Flag', required=False)
    order_type = fields.Selection([
                                    ('All', 'All'),
                                    ('POS Order', 'POS Order'),
                                    ('Sale Order', 'Sale Order'),
                                    ], string='Order Type', required=True, default='POS Order')
    requested_by = fields.Many2one('res.users', string='Requested', default=_default_requested_by)
    compile_flag = fields.Boolean(string='Compile Flag', default=True)        
    discount_line = fields.One2many('sale.promo.lines', 'promotion_id')
    discount_promo_line = fields.One2many('sale.promo.lines', 'promotion_id')
    promo_line = fields.One2many('sale.promo.lines', 'promotion_id')
    promo_line_info = fields.One2many('sale.promo.lines', 'promotion_id')
    
    warehouse_ids = fields.Many2many('stock.warehouse', 'sale_promo_shop_rel', 'promo_id', 'shop_id', string='Shops')
    member_category = fields.Many2many('res.partner.category','sale_promo_custcat_rel','promo_id','res_partner_category_id', string='Partner Categories')
    first_get_flag = fields.Boolean(string='First Get Flag', required=False, default=True)
    search_product_ean = fields.Char(string='Search Product/EAN', size=300)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approval'),
        ('cancel', 'Cancelled')
        ], string='State', default='draft', select=True, readonly=True)
    
    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True
    
    @api.multi
    def action_reset(self):
        self.write({'state': 'draft'})
        return True
    
    @api.multi
    def action_approve(self):
        self.write({'approved_by': self.env.uid, 'state': 'approved'})
        return True
    
    @api.onchange('search_product_ean')
    def onchange_product(self):
        promo_line_pool = self.env['sale.promo.lines']
        domain = []
        domain.append(('promotion_id','=', self.id))
        if self.search_product_ean:
            domain.append('|')
            domain.append('|')
            domain.append(('product_ean', 'ilike', self.search_product_ean))
            domain.append(('product_id.name', 'ilike', self.search_product_ean))
            domain.append(('product_id.default_code', 'ilike', self.search_product_ean))
        if domain:
            line_ids = promo_line_pool.search(domain)
            if self.list_type == 'PRO':
                self.promo_line = line_ids
            else:
                self.discount_line = line_ids
    
#     @api.model
#     def create(self, vals):
#         if vals and 'start_hour' in vals and vals['start_hour']:
#             vals['end_hour_effective'] = self._get_hour(cr, uid,vals['end_hour']) and self._get_hour(cr, uid,vals['end_hour'])  or False
#         
#         if vals and 'end_hour' in vals and vals['end_hour']:
#             vals['end_hour_effective'] = self._get_hour(cr, uid,vals['end_hour']) and self._get_hour(cr, uid,vals['end_hour'])  or False
#         return super(sale_promo_header, self).create(vals)
    
#     @api.model
#     def write(self, vals):
#         if vals and 'start_hour' in vals and  vals['start_hour']:
#             vals['start_hour_effective'] = self._get_hour(cr, uid,vals['start_hour']) and self._get_hour(cr, uid,vals['start_hour'])  or False 
#                 
#         if vals and 'end_hour' in vals and vals['end_hour']:
#             vals['end_hour_effective'] = self._get_hour(cr, uid,vals['end_hour']) and self._get_hour(cr, uid,vals['end_hour'])  or False
#         return super(sale_promo_header, self).write(vals)
    
    @api.onchange('start_date_active', 'end_date_active')
    def onchange_dateheader(self):
        if self.end_date_active and self.start_date_active > self.end_date_active:
            self.end_date_active = False
            warning = {
               'title': _('Promotion Warning!'),
               'message' : _('Start Date must be smaller than End date !!!')
            }
            return {'warning': warning}
    
        if self.id and self.start_date_active:
            sql = '''
                select min(start_date_active) start_date
                from sale_promo_lines where promotion_id = %s
                '''%(self.id)
            self.env.cr.execute(sql)
            for data in self.env.cr.dictfetchall():
                if data['start_date'] and self.start_date_active > data['start_date']:
                    self.start_date = False
                    warning = {
                    'title': _('Promotion Warning!'),
                    'message' : _('Start Date header must be smaller than Start date line !!!')
                    }
                    return {'warning': warning}
                
        if self.id and self.end_date_active:
            sql = '''
                select max(end_date_active) end_date
                from sale_promo_lines where promotion_id = %s
                '''%(self.id)
            self.env.cr.execute(sql)
            for data in self.env.cr.dictfetchall():
                if data['end_date'] and self.end_date_active < data['end_date']:
                    self.end_date_active = False
                    warning = {
                     'title': _('Promotion Warning!'),
                     'message' : _('End Date header must be bigger than End date line !!!')
                    }
                    return {'warning': warning}
    
    @api.onchange('start_hour')  
    def onchange_start_hour(self):
        if (self.start_hour >= 0 and self.end_hour < 24):
            a = 1
        else:
            self.start_hour = False
            warning = {
             'title': _('Promotion Warning!'),
             'message' : _('Hour effective must be between 0 H and 24 H !!!')
            }
            return {'warning': warning} 
        
    @api.onchange('end_hour')  
    def onchange_end_hour(self):
        if (self.end_hour >= 0 or self.end_hour <= 24) and (self.end_hour >= self.start_hour):
            a = 1
        else:
            self.end_hour = False
            warning = {
             'title': _('Promotion Warning!'),
             'message' : _('Hour effective must be between 0 H and 24 H !!!')
            }
            return {'warning': warning} 
    
    #Thanh: Used to get promotion for POS Front-end
#     @api.multi
    def get_active_promotion_by_productcode(self,cr,uid, operation_date, warehouse_id):
        if not operation_date:
            operation_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
#         company_id = self.env.user.company_id.id
        company_id = 1
#         res_users_obj = self.pool.get('res.users')
#         company_id = res_users_obj.browse(cr, uid, uid).company_id.id
        sql = '''
        SELECT spl.id, sph.start_date_active, sph.end_date_active,
            case when sph.start_hour > 0
                then
                ('%(operation_date)s'::date + sph.start_hour * interval '1 hour')::character varying
                else
                '' end special_start_datetime,
            case when sph.end_hour > 0
                then
                ('%(operation_date)s'::date + sph.end_hour * interval '1 hour')::character varying
                else
                '' end special_end_datetime,
            sph.order_type, spl.modify_type, 
            spl.product_attribute, spl.product_attribute_value, spl.product_ean, spl.product_uom,    
                spl.level_type, spl.break_type, spl.volume_type, spl.operator, spl.value_from, spl.value_to, 
                spl.benefit_product_id, spl.benefit_uom, spl.benefit_qty
                    
        FROM sale_promo_header sph join sale_promo_lines spl on sph.id = spl.promotion_id
                and sph.company_id = %(company_id)s and sph.active = true and spl.active = true
                and '%(operation_date)s' between sph.start_date_active and sph.end_date_active
            /* =====    set dieu kien theo shop    ===== */
            join sale_promo_shop_rel psr on sph.id = psr.promo_id and psr.shop_id = %(warehouse_id)s
        WHERE sph.list_type = 'PRO' and spl.modify_type = 'pro_goods' and spl.product_attribute = 'product'
        '''%({'operation_date':operation_date,
              'warehouse_id': warehouse_id,
              'company_id': company_id})
#         self.env.cr.execute(sql)
        cr.execute(sql)
        return cr.dictfetchall()
    
#     #Thanh: Used to get promotion for POS Front-end
#     @api.multi
#     def get_active_promotion_by_productcode(self, operation_date, warehouse_id):
#         if not operation_date:
#             operation_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
#         company_id = self.env.user.company_id.id
#         sql = '''
#         SELECT spl.id, sph.start_date_active, sph.end_date_active,
#             case when sph.start_hour > 0
#                 then
#                 ('%(operation_date)s'::date + sph.start_hour * interval '1 hour')::character varying
#                 else
#                 '' end special_start_datetime,
#             case when sph.end_hour > 0
#                 then
#                 ('%(operation_date)s'::date + sph.end_hour * interval '1 hour')::character varying
#                 else
#                 '' end special_end_datetime,
#             sph.order_type, spl.modify_type, 
#             spl.product_attribute, spl.product_attribute_value, spl.product_ean, spl.product_uom,    
#                 spl.level_type, spl.break_type, spl.volume_type, spl.operator, spl.value_from, spl.value_to, 
#                 spl.benefit_product_id, spl.benefit_uom, spl.benefit_qty
#                     
#         FROM sale_promo_header sph join sale_promo_lines spl on sph.id = spl.promotion_id
#                 and sph.company_id = %(company_id)s and sph.active = true and spl.active = true
#                 and '%(operation_date)s' between sph.start_date_active and sph.end_date_active
#             /* =====    set dieu kien theo shop    ===== */
#             join sale_promo_shop_rel psr on sph.id = psr.promo_id and psr.shop_id = %(warehouse_id)s
#         WHERE sph.list_type = 'PRO' and spl.modify_type = 'pro_goods' and spl.product_attribute = 'product'
#         '''%({'operation_date':operation_date,
#               'warehouse_id': warehouse_id,
#               'company_id': company_id})
#         self.env.cr.execute(sql)
#         return self.env.dictfetchall()
    
    @api.multi
    def get_active_promotion_by_category(self, operation_date, warehouse_id):
        if not operation_date:
            operation_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        company_id = self.env.user.company_id.id
        sql = '''
        SELECT spl.id, sph.start_date_active, sph.end_date_active,
            case when sph.start_hour > 0
                then
                ('%(operation_date)s'::date + sph.start_hour * interval '1 hour')::character varying
                else
                '' end special_start_datetime,
            case when sph.end_hour > 0
                then
                ('%(operation_date)s'::date + sph.end_hour * interval '1 hour')::character varying
                else
                '' end special_end_datetime,
            sph.order_type, spl.modify_type, 
            spl.product_attribute, spl.categ_id,    
                spl.level_type, spl.break_type, spl.volume_type, spl.operator, spl.value_from, spl.value_to, 
                spl.benefit_product_id, spl.benefit_uom, spl.benefit_qty
                    
        FROM sale_promo_header sph join sale_promo_lines spl on sph.id = spl.promotion_id
                and sph.company_id = %(company_id)s and sph.active = true and spl.active = true
                and '%(operation_date)s' between sph.start_date_active and sph.end_date_active
            /* =====    set dieu kien theo shop    ===== */
            join sale_promo_shop_rel psr on sph.id = psr.promo_id and psr.shop_id = %(warehouse_id)s
        WHERE sph.list_type = 'PRO' and spl.modify_type = 'pro_goods' and spl.product_attribute = 'cat'
        '''%({'operation_date':operation_date,
              'warehouse_id': warehouse_id,
              'company_id': company_id})
        self.env.cr.execute(sql)
        return self.env.dictfetchall()
    
    @api.multi
    def get_active_promotion_by_cus_categ(self, operation_date, warehouse_id):
        if not operation_date:
            operation_date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        sql = '''
        SELECT sph.id rule_id, pcr.res_partner_category_id categ_id
        FROM sale_promo_header sph 
            join sale_promo_custcat_rel pcr on sph.id = pcr.promo_id
            join sale_promo_shop_rel psr on sph.id = psr.promo_id and psr.shop_id = %(warehouse_id)s
        WHERE sph.company_id = %(company_id)s
            and sph.list_type = 'PRO' and sph.active = true
            and '%(operation_date)s' between sph.start_date_active and sph.end_date_active
        '''%({'operation_date':operation_date,
              'company_id': self.env.user.company_id.id,
              'warehouse_id': warehouse_id})
        self.env.cr.execute(sql)
        res = {}
        for line in self.env.dictfetchall():
            if not res.has_key(line['rule_id']):
                res[line['rule_id']] = [line['categ_id']]
            else:
                res[line['rule_id']].append(line['categ_id'])
        return res
    #Thanh: Used to get promotion for POS Front-end
    
class sale_promo_lines(models.Model):
    _description = "Promotion Lines"    
    _name ="sale.promo.lines"
    _order = 'line_no desc'

    @api.model
    def add_modify_type(self):        
        context = self._context or {}
        result = []
        list_type = context.get('default_list_type',False)
        if not list_type:
            return [('pro_goods', _('Promotional Goods')),('disc_percent', _('% Discount')),('disc_value', _('Price Break Discount'))]
        if list_type ==  'PRO':
            result.append(('pro_goods', _('Promotional Goods')))
        else:
            result.append(('disc_percent', _('% Discount')))
            result.append(('disc_value', _('Price Break Discount')))
        return result
    
    @api.one
    @api.depends('product_attribute','product_id','categ_id')
    def _get_product_attribute_value(self):
        self.product_attribute_value = False
        if self.product_attribute == 'product':
            self.product_attribute_value = self.product_id and self.product_id.id or False
        if self.product_attribute == 'cat':
            self.product_attribute_value = self.categ_id and self.categ_id.id or False
    
    line_no = fields.Integer(string='Line no', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env['res.company']._company_default_get('sale.promo.lines'))               
    level_type = fields.Selection([
                                    ('Order', 'Order'),
                                    ('Line', 'Line'),                                                  
                                    ], string='Level', default='Line', required=True)
    modify_type = fields.Selection('add_modify_type', string='Modify Type', required=True)
    start_date_active = fields.Date(string='Start Date')    #ĐK: 2 ngày này phải nằm trong range date_effective của header
    end_date_active = fields.Date(string='End Date')    #ĐK: 2 ngày này phải nằm trong range date_effective của header
    product_attribute = fields.Selection([('product','Product Code'),
                                          ('cat','Category'),
                                          ('order', 'Order Amount')], 
                                         string='Product Attribute', default='product', required= True)
    product_id = fields.Many2one('product.product', string='Product')
    categ_id = fields.Many2one('product.category', string='Category')
    product_attribute_value = fields.Integer(compute='_get_product_attribute_value', store=True, string='Attribute Value')
    product_ean = fields.Char(string='Default EAN',size =20)
    product_uom = fields.Many2one('product.uom', string='UoM', context="{'product_id':product_id}")
    name = fields.Char(string='Description', size=128)
    volume_type = fields.Selection([
                                    ('qty', 'Quantity'),
                                    ('amt','Amount'),
                                    ('amtx','Untax Amount')                                                
                                    ], string='Volume Type',required= True)
    break_type = fields.Selection([
                                    ('Point', 'Point'),
                                    ('Recurring','Recurring')
                                    ], string='Break Type', default='Point', required= True)
    operator = fields.Selection([
                                    ('=', '='),
                                    ('!=','!='),
                                    ('>','>'), 
                                    ('>=', '>='),
                                    ('<','<'),
                                    ('>','<'),
                                    ('between','between')                                                      
                                    ], string='Operator', default='>=', required= True)
    value_from = fields.Float(string='Value From', digits=(16,2))
    value_to = fields.Float(string='Value To', digits=(16,2))
    promotion_id = fields.Many2one('sale.promo.header', string='Promotion')
    active = fields.Boolean(string='Active', default=True)
    benefit_uom = fields.Many2one('product.uom', string='Promotion UoM', context="{'product_id':benefit_product_id}")
    benefit_product_id = fields.Many2one('product.product', string='Promotion Item')
    benefit_qty = fields.Float(string='Promotion Qty', digits=(16,2))
    discount_value = fields.Float(string='Discount Value')
    override_flag = fields.Boolean(string='Override', default=True)
    parent_line_id = fields.Many2one('sale.promo.lines', string='Parent ID')
    promo_line_ids = fields.One2many('sale.promo.lines', 'parent_line_id', string='Condition Attributes')
    logical = fields.Selection([('and', 'And Clause'),
                                ('or','Or Clause')], 
                               string='Logical', default='and')
                                    
    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(sale_promo_lines, self).default_get(fields)
        if context.get('active_id',False) and context.get('active_model',False) and context['active_model'] == 'sale.promo.header':
            res.update({
                        "promotion_id": context['active_id'],
                        })
        if context.get('load_grand_child',False) and context.get('active_id',False) and context.get('active_model',False) and context['active_model'] == 'sale.promo.lines':
            this = self.env[context['active_model']].browse(context['active_id'])
            res.update({"id": this.id,
                        "line_no": this.line_no,
                        "start_date_active" : this.start_date_active,
                        "end_date_active" : this.end_date_active,
                        "level_type" : this.level_type,
                        "modify_type": this.modify_type,                       
                        "product_attribute" : this.product_attribute,      
                        "product_id" : this.product_id.id or False,      
                        "categ_id" : this.categ_id.id or False,      
                        "product_ean" : this.product_ean,      
                        "product_uom" : this.product_uom.id or False,      
                        "volume_type": this.volume_type,      
                        "break_type" : this.break_type,               
                        "operator": this.operator,
                        "value_from": this.value_from,
                        "value_to": this.value_to,
                        "active": this.active,
                        "company_id" : this.company_id.id or False,
                        "promotion_id" : this.promotion_id.id or False,
                        "promo_line_ids" : [x.id for x in this.promo_line_ids],
                        
                        "benefit_product_id" : this.benefit_product_id.id or False,
                        "benefit_uom" : this.benefit_uom.id or False,
                        "benefit_qty" : this.benefit_qty,
                        
                        "discount_value" : this.discount_value,
                        'override_flag': this.override_flag,
                        })
        return res
    
    @api.multi
    def create_line(self):
        return {'type': 'ir.actions.act_window_close'}
    
    @api.onchange('level_type', 'product_attribute', 'volume_type', 'break_type', 'operator')
    def onchange_leave(self):
        #Thanh: Active for parent line not childs
        if self.parent_line_id:
            warning ={}
            if self.product_attribute == 'order' and self.volume_type == 'qty':
                self.volume_type = False
                warning = {
                     'title': _('Promotion Warning!'),
                     'message' : _('Volume Type must be Amount or Untax Amount !!!')
                     }
            return {'warning': warning} 
        
        if self.level_type =='Line' and self.product_attribute == 'order':
            self.product_attribute = False
            warning = {
                 'title': _('Promotion Warning!'),
                 'message' : _("Product Attribute must be 'Product Code' or 'Category' !!!")
                 }
            return {'warning': warning} 
        
        if self.level_type == 'Order' and self.product_attribute == 'order' and self.volume_type == 'qty':
            self.volume_type = False
            warning = {
                 'title': _('Promotion Warning!'),
                 'message' : _("Volume Type must be 'Amount' or 'Untax Amount' !!!")
                 }
            return {'warning': warning}
        
        if self.product_attribute =='order' and self.volume_type == 'qty':
            self.volume_type = False
            warning = {
                 'title': _('Promotion Warning!'),
                 'message' : _("Volume Type must be 'Amount' or 'Untax Amount' !!!")
                 }
            return {'warning': warning} 
        
        if self.break_type == 'Recurring' and self.operator != '>=':
            self.operator = '>='
        
        return self.onchange_product_id()
    
    @api.onchange('start_date_active', 'end_date_active')
    def onchange_dateline(self):
        return self.onchange_product_id()
    
    @api.onchange('benefit_product_id')
    def onchange_benefit_product_id(self):
        if self.benefit_product_id:
            if not self.benefit_uom:
                self.benefit_uom = self.benefit_product_id.uom_id.id
            if not self.benefit_qty:
                self.benefit_qty = 1
            
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_uom:
            self.product_uom = self.product_id.uom_id.id
        if not self.product_ean:
            self.product_ean = self.product_id.barcode
            
        #Thanh: Active for parent line not childs
        if self.parent_line_id:
#             if self.product_id:
#             product_obj = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
#             #Thanh: Get Default UoM if it is not belong to Product UoM Conversion
#             conversion_uom_ids = [x.id for x in product_obj.conversion_uom_ids]
#             if not product_uom or (product_uom and product_uom not in conversion_uom_ids):
#                 product_uom = product_obj.uom_id.id
             
                #Thanh: Get ean13 from product_product instead of product_barcode
#                 self.env.cr.execute("SELECT barcode FROM product_product WHERE id = %s and active=true "%(self.product_id.id))
#                 res = self.env.cr.dictfetchall()
#                 if res:
#                     self.product_ean = res[0]['barcode']
#                 else:
#                     self.product_ean = False
                
#                 if product_barcode_pool.search(cr, uid, [('product_id','=',product_id),
#                                                          ('uom_id','=',product_uom),
#                                                          ('barcode','=',product_ean)]) == []:
#                     barcode_ids = product_barcode_pool.search(cr, uid, [('product_id','=',product_id),('uom_id','=',product_uom)])        
#                     if barcode_ids:
#                         product_ean = product_barcode_pool.browse(cr, uid, barcode_ids[0]).barcode
#                         value.update({'product_ean': product_ean})
#                     else:
#                         value.update({'product_ean': False})
#                 value.update({'product_uom': product_uom})
            return
        
        #Check Date Active
        warning = {}
        header_id = self.promotion_id.id #context.get('header_id',False)
        if not header_id:
            raise UserError(_('You have to save the Promotion first before creating a Promotion Line !!!'))
        header_obj = self.promotion_id #self.env['sale.promo.header'].browse(header_id)
        start_date_active_header = header_obj.start_date_active
        end_date_active_header = header_obj.end_date_active
        if not start_date_active_header:
            raise UserError(_('You have to input the Date Effective From first before creating a Promotion Line !!!'))
        
        #Check Start Date Active
        if  self.start_date_active and self.end_date_active and self.start_date_active > self.end_date_active:
            self.end_date_active = False
            warning = {
            'title': _('Promotion Warning!'),
             'message' : _('Start date active must be between Start date header and End line header !!!')
            }
            return {'warning': warning}
         
        if self.start_date_active and end_date_active_header and \
            (self.start_date_active < start_date_active_header or self.start_date_active > end_date_active_header):          
            self.start_date_active = False
            warning = {
            'title': _('Promotion Warning!'),
            'message' : _('Start date active must be between Start date header and End date header !!!')
            }
            return {'warning': warning}
        
        if self.start_date_active and self.start_date_active < start_date_active_header:
            self.start_date_active = False
            warning = {
            'title': _('Promotion Warning!'),
            'message' : _('Start date active must be between Start date Header and End line header !!!')
            }
            return {'warning': warning}
        
        if self.end_date_active and end_date_active_header and \
            (self.end_date_active < start_date_active_header or self.end_date_active > end_date_active_header):
            self.end_date_active = False
            warning = {
            'title': _('Promotion Warning!'),
            'message' : _('End Date active must be between Start date Header and End line header !!!')
            }
            return {'warning': warning}
        
        if self.end_date_active and self.end_date_active < start_date_active_header :
            self.end_date_active = False
            warning = {
            'title': _('Promotion Warning!'),
            'message' : _('End Date active must be between Start date Header and End line header !!!')
            }
            return {'warning': warning}
         
        #Check Full Price Line
        where = ''
        execute = False
        start_date_active = self.start_date_active or start_date_active_header
        end_date_active = self.end_date_active or end_date_active_header
        if self.level_type:
            where += " AND pl.level_type = '%s'"%(self.level_type)
        if self.product_attribute == 'product' and self.product_id and self.product_uom:
            where += " AND pl.product_attribute = 'product' AND pl.product_id = %s AND pl.product_uom=%s"%(self.product_id.id,self.product_uom.id)
            if self.product_ean:
                where += " AND coalesce(pl.product_ean,'%s') = '%s'"%(self.product_ean,self.product_ean)
            execute = True
#            if product_attribute == 'cat' and categ_id:
#                where += "AND product_attribute = 'cat' AND categ_id = %s"%(categ_id)
#                execute = True
        sql = '''
        SELECT pl.id
        FROM sale_promo_lines pl
        WHERE 
            pl.promotion_id = %s
        '''%(header_id)
        if self.id:
            where += " AND pl.id != %s"%(self.id)
        if start_date_active:
            where += " AND ((pl.end_date_active>='%s') or (pl.end_date_active is null))"%(start_date_active)
        if end_date_active:
            where += " AND ((pl.start_date_active<='%s') or (pl.start_date_active is null))"%(end_date_active)
        if execute:
            self.env.cr.execute(sql+where)
            result = self.env.cr.dictfetchall()
            if result:
                return {}
                self.start_date_active = False
                self.end_date_active = False
                self.level_type = False
                self.product_id = False
                self.product_uom = False
                self.product_ean = False
                warning = {
                       'title': _('Promotion Warning!'),
                       'message' : _('There is the same Promotion line. It may be similar in Product, UoM or Date Start and Date End !!!')
                       }
                return {'warning': warning}
    
    @api.onchange('product_uom')
    def onchange_product_uom_id(self):
        #Thanh: Active for parent line not childs
        if self.parent_line_id:
            if not self.product_uom:
                return
            return self.onchange_product_id()
        
        if not self.product_uom:
            return
        return self.onchange_product_id()
    
#     @api.onchange('product_ean')
#     def product_ean_change(self):
#         Thanh: Active for parent line not childs
#         if self.parent_line_id:
#             if not self.product_ean:
#                 return
#         
#             self.env.cr.execute('''SELECT pp.id, pt.uom_id 
#                             FROM product_product pp join product_template pt on pp.product_tmpl_id=pt.id
#                             WHERE pp.barcode = '%s
#                         '''%(self.product_ean))
#             res = self.env.cr.dictfetchall()
#             if res:
#                 self.product_id = res[0]['product_id']
#                 self.product_uom = res[0]['uom_id']
#             else:
#                 self.product_id = False
#                 self.product_uom = False
#             return self.onchange_product_id()
#         Thanh: Need to review, firstly get product_id and uom from product_template instead of product.barcode
#         product_barcode_pool = self.pool.get('product.barcode')
#         cr.execute("SELECT product_id,uom_id FROM product_barcode WHERE  barcode='%s' and active=true "%(product_ean,))
#         res = cr.dictfetchall()
#         if res:
#             product_id = res[0]['product_id']
#             product_uom = res[0]['uom_id']
#         else:
#             product_id = False
#         self.env.cr.execute('''SELECT pp.id, pt.uom_id 
#                             FROM product_product pp join product_template pt on pp.product_tmpl_id=pt.id
#                             WHERE pp.barcode = '%s
#                         '''%(self.product_ean))
#         res = self.env.cr.dictfetchall()
#         if res:
#             self.product_id = res[0]['product_id']
#             self.product_uom = res[0]['uom_id']
#         else:
#             self.product_id = False
#             self.product_uom = False
#         return self.onchange_product_id()
    
    @api.multi
    def unlink(self):
        for line in self:
            update_ids = self.search([('promotion_id','=', line.promotion_id.id),
                                      ('line_no','>',line.line_no)])
            if update_ids:
                self.env.cr.execute("UPDATE sale_promo_lines SET line_no=line_no-1 WHERE id in %s",(tuple(update_ids),))
        return super(sale_promo_lines, self).unlink()  
    
    @api.model
    def create(self, vals):
        context = self._context or {}
        if vals.get('parent_line_id',False):
            vals['promotion_id'] = False
            context['load_grand_child'] = False
        if vals.get('promotion_id',False):
            vals['line_no'] = len(self.search([('promotion_id', '=', vals['promotion_id'])])) + 1
        return super(sale_promo_lines, self).create(vals)  
    
    def date_promo_line_uniq(self):
        list_type =False
        for line in self:
            if line.promotion_id:
                list_type = line.promotion_id.list_type
            else:
                return True
            if line.product_attribute == 'product':
                sql = '''
                    SELECT spl.id 
                    FROM sale_promo_lines spl inner join sale_promo_header sp on sp.id = spl.promotion_id and  sp.list_type = '%s'
                    WHERE
                        modify_type = '%s' and product_attribute ='%s' and product_id = %s and product_ean = '%s' 
                        and product_uom = %s and volume_type = '%s' and spl.id !=%s 
                        and ((spl.end_date_active > '%s') or spl.end_date_active is null)
                        and ((spl.start_date_active < '%s') or spl.start_date_active is null)
                '''%(list_type,line.modify_type,line.product_attribute,line.product_id.id,line.product_ean,line.product_uom.id,line.volume_type,line.id,line.start_date_active,line.start_date_active)
                self.env.cr.execute(sql)
                promo_line_search = self.env.cr.dictfetchall()
                if promo_line_search:
                    return False
            if line.product_attribute == 'order':
                sql = '''
                    SELECT spl.id
                    FROM sale_promo_lines spl inner join sale_promo_header sp on sp.id = spl.promotion_id and  sp.list_type = '%s'
                    WHERE
                        modify_type = '%s' and product_attribute ='%s' 
                        and volume_type = '%s' and spl.id !=%s 
                        and ((spl.end_date_active > '%s') or spl.end_date_active is null)
                        and ((spl.start_date_active < '%s') or spl.start_date_active is null)
                '''%(list_type,line.modify_type,line.product_attribute,line.volume_type,line.id,line.start_date_active,line.start_date_active)
                self.env.cr.execute(sql)
                promo_line_search = self.env.cr.dictfetchall()
                 
                if promo_line_search:
                    return False
        return True
 
    _constraints = [(date_promo_line_uniq, 'Error: Duplicate line!!! Please recheck!!!', ['Start date'])]
    