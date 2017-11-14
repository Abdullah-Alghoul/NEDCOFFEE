# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError
from datetime import datetime
import time

DATE_FORMAT = "%Y-%m-%d"

class KCSCriterions(models.Model):
    _name = "kcs.criterions"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'id asc'
    
    name = fields.Char(string="Name", required=True, copy=False, default="New", readonly=True,  states={'draft': [('readonly', False)]})
    from_date = fields.Date(stirng="From Date", required=True, default=fields.Datetime.now, copy=False, readonly=True,  states={'draft': [('readonly', False)]})
    to_date = fields.Date(stirng="TO Date", default=fields.Datetime.now, copy=False, readonly=True,  states={'draft': [('readonly', False)]})
    state = fields.Selection([("draft", "New"),("approved", "Approved"),("cancel", "Cancelled")], string="Status", readonly=True, copy=False, index=True, default='draft')
    categ_id = fields.Many2one("product.category", string="Category", readonly=False ,domain=[('parent_id','!=',False)], states={'draft': [('readonly', False)]}, required=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=False , required=False)
    special = fields.Boolean(string='Special',default=False)
    origin = fields.Char(string='Source Document')
    note = fields.Text(string="Notes")
    ksc_line_ids = fields.One2many("kcs.criterions.line", "ksc_id", "KCS Line", readonly=True, states={'draft': [('readonly', False)]})
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now, copy=False)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid, copy=False)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True, copy=False)
    
    @api.multi
    def unlink(self):
        for kcs in self:
            if kcs.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(KCSCriterions, self).unlink()
    
    @api.one
    @api.constrains('name')
    def _check_name(self):
        if self.name:
            criterions_ids = self.search([('name', '=', self.name), ('id', '!=', self.id)])
            if criterions_ids:
                raise UserError(_("KCS Criterions (%s) was exist.") % (self.name))
    
        
    @api.multi
    def button_approve(self): 
        if self.special:
            self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            return True
        
        if self.product_id:
            for criterions in  self.search([('id','!=',self.id),('state', '=', 'approved'), ('product_id','=',self.product_id.id)]): 
                if criterions.from_date <= self.from_date and self.from_date <= criterions.to_date:
                    raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s)") % (criterions.name,criterions.from_date,criterions.to_date))
                if criterions.from_date <= self.to_date and  self.to_date <= criterions.to_date:
                    raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                    
                if self.from_date <= criterions.from_date and  criterions.from_date <= self.to_date:
                    raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                if self.from_date <= criterions.to_date and  criterions.to_date <= self.to_date:
                    raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                
            self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            return True
        
        if self.categ_id:
            kcs_criterions_ids =[]
            sql ='''
                SELECT id FROM
                    kcs_criterions
                    WHERE
                        state = 'approved'
                        and categ_id = %s
                        and product_id is null
                        and id != %s
            '''%(self.categ_id.id,self.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                kcs_criterions_ids.append(line['id'])
            if kcs_criterions_ids:
                for criterions in  self.browse(kcs_criterions_ids): 
                    if criterions.from_date <= self.from_date and  self.from_date <= criterions.to_date:
                        raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s)") % (criterions.name,criterions.from_date,criterions.to_date))
                    if criterions.from_date <= self.to_date and  self.to_date <= criterions.to_date:
                        raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                    
                    if self.from_date <= criterions.from_date and  criterions.from_date <= self.to_date:
                        raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                    if self.from_date <= criterions.to_date and  criterions.to_date <= self.to_date:
                        raise UserError(_("KCS Criterions (%s) was exist. Date (%s - %s) ") % (criterions.name,criterions.from_date,criterions.to_date))
                
            self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            return True
        
    @api.multi 
    def button_cancel(self):
        self.write({'state': 'cancel', 'date_cancel': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
    @api.multi 
    def button_draft(self):
        self.write({'state': 'draft'})
        
        
    
class KCSCriterionsLine(models.Model):
    _name = "kcs.criterions.line"
    _order = 'id asc'
    
    @api.model
    def _get_sequence(self):
        seq = 1
        for kcs_line in self:
            if not kcs_line.ids:
                return 
            kcs_line.sequence = seq
            seq += 1
    
    name = fields.Char(string="Description")
    sequence = fields.Integer(compute="_get_sequence", string="Sequence", store=False, track_visibility='always')
    check_indicators = fields.Char(string='Check Indicators', required=True)
    value = fields.Float(string='Value', required=True)
    type = fields.Selection([('bigger', 'Bigger than the reference value'), ('reference', 'By reference value'),
         ('smaller', 'Smaller than the reference value')], string="Type", default='reference', required=True)
    description = fields.Text(string="Description")
    ksc_id = fields.Many2one("kcs.criterions", string="KCS Criterions", ondelete='cascade', index=True, copy=False)
    
class RequestKCS(models.Model):
    _name = "request.kcs"
    _order = 'id desc'
    
    name = fields.Char(string="Reference ", required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default='New')
    auditor = fields.Char(string="Auditor", readonly=True, states={'draft': [('readonly', False)]}, index=True)
    date = fields.Date(string="Date", readonly=True, index=True, states={'draft': [('readonly', False)]}, copy=False, default=fields.Datetime.now)
    state = fields.Selection([("draft", "New"), ("approved", "Approved"), ("cancel", "Cancelled")], string="Status", readonly=True, copy=False, index=True, default='draft')
    picking_type_id = fields.Many2one("stock.picking.type", stirng="Picking Type", required=True, readonly=True, states={'draft': [('readonly', False)]})
    picking_id = fields.Many2one("stock.picking", string="Picking", required=True, readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    note = fields.Text(string="Note") 
    #request_line_ids = fields.One2many("request.kcs.line", "request_id", string="Request KCS Line", readonly=True, states={'draft': [('readonly', False)]})
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True)
    
    @api.model
    def create(self, vals): 
        if vals.get('name', 'New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('request.kcs')
        result = super(RequestKCS, self).create(vals)
        return result
    
    @api.multi
    def unlink(self):
        for request in self:
            if request.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(RequestKCS, self).unlink()
    
    @api.one
    @api.constrains('name')
    def _check_name(self):
        if self.name:
            request_ids = self.search([('name', '=', self.name), ('id', '!=', self.id)])
            if request_ids:
                raise UserError(_("Request KCS (%s) was exist.") % (self.name))
    
    @api.multi
    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if not self.picking_type_id:
            domain = {'domain': {'picking_id': []}}
            return domain
        domain = {'domain': {'picking_id': [('picking_type_id', '=', self.picking_type_id.id)]}}
        return domain
    
    @api.multi
    @api.onchange('picking_id')
    def onchange_picking_id(self):
        if not self.picking_id:
            domain = {'domain': {'picking_type_id': []}}
            values = {'picking_type_id': False}
            self.update(values)
            return domain
            
        domain = {'domain': {'picking_type_id': [('id', '=', self.picking_id.picking_type_id.id or False)]}}
        values = {'picking_type_id': self.picking_id.picking_type_id.id}
        self.update(values)
        return domain
    
    @api.multi
    def button_load(self):
        tmpl = self.env['product.template']
        if self.picking_id:
            self.env.cr.execute('''DELETE FROM indicator_kcs WHERE id in (SELECT ik.id FROM indicator_kcs ik 
                    join request_kcs_line rkl on ik.request_line_id = rkl.id WHERE rkl.request_id = %(request_id)s);
                DELETE FROM request_kcs_line WHERE request_id = %(request_id)s;''' % ({'request_id': self.id}))
            for move in self.picking_id.move_lines:
                if self.picking_type_id.code  == 'incoming':
                    if move.product_id.kcs_incoming == True:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code  == 'outgoing':
                    if move.product_id.kcs_outgoing == True:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code  == 'internal':
                    if move.product_id.kcs_internal:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'internal':
                    if move.product_id.kcs_internal:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'production_out':
                    if move.product_id.kcs_production_out:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'production_in':
                    if move.product_id.kcs_production_in:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,  
                               'product_qty': move.product_uom_qty or 0.0,'qty_reached': move.product_uom_qty or 0.0,'criterions_id': False,  
                               'product_uom': move.product_uom.id or False,'move_id': move.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
        return True
    
    @api.multi
    def button_approve(self):
        for request in self:
            if not request.request_line_ids:
                raise UserError(_('You cannot approve a Request KCS without any Request KCS Line.'))
            request.picking_id.write({'request_kcs_id': request.id})
            for kcs_line in request.request_line_ids:
                if kcs_line.state == 'draft':
                    raise UserError(_('You cannot approve a Request KCS.'))
                elif kcs_line.state == 'approved':
                    if kcs_line.qty_reached > kcs_line.product_qty:
                        raise UserError(_('Quantity do not bigger than Init Quantity'))
                    else:
                        kcs_line.move_id.write({'product_uom_qty': kcs_line.qty_reached or 0.0})
                else:
                    kcs_line.move_id.write({'product_uom_qty': 0.0})
                    kcs_line.move_id.action_cancel()
        self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        
    @api.multi
    def button_cancel(self):
        for request in self:
            if request.picking_id.state == 'done': 
                raise UserError(_('Unable to cancel Request KCS %s')%(self.name))
            for line in request.kcs_line:
                line.state ='reject'
        self.write({'state': 'cancel'})
    
class RequestKCSLine(models.Model):
    _name = "request.kcs.line"
    _order = 'id'
    
    @api.model
    def _default_uom_id(self):
        uom_id = self.env['product.uom'].search([('id','=', 3)])
        return uom_id
    
    name = fields.Text("Name",readonly=True, states={'draft': [('readonly', False)]})
    product_id = fields.Many2one("product.product", string="Product", required=True)
    categ_id = fields.Many2one("product.category", string="Category",domain=[('parent_id','!=',False)])
    product_qty = fields.Float("Net Weight",digits=(12, 0))
    qty_reached = fields.Float("Deduction Weight")
    product_uom = fields.Many2one("product.uom", string="UoM", required=True, default=_default_uom_id)
    #criterions_id = fields.Many2one("kcs.criterions", string="KCS Criterion",readonly=True, states={'draft': [('readonly', False)]})
    criterions_id = fields.Many2one(related='picking_id.kcs_criterions_id',  string="KCS Criterion",readonly=True, states={'draft': [('readonly', False)]})
    related='contract_line.price_unit', 
    indicator_kcs_ids = fields.One2many("indicator.kcs", "request_line_id", string="KCS Indicator" ,
                                        readonly=True, states={'draft': [('readonly', False)]})
    #request_id = fields.Many2one("request.kcs", string="Request KCS",   copy=False)
    picking_id = fields.Many2one("stock.picking", string="Request KCS", ondelete='cascade', index=True, copy=False)
    state = fields.Selection(selection=[('draft', 'New'),('approved', 'Approved'),('reject', 'Reject')],string='Status', readonly=True, copy=False, index=True, default='draft')
    move_id = fields.Many2one('stock.move', string="Move", readonly=True, copy=False)
    cuptest = fields.Char(string="Cuptest")
    
    @api.multi
    def unlink(self):
        for request_line in self:
            if request_line.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(RequestKCSLine, self).unlink()
    
    @api.multi
    def button_load(self):
        if self.criterions_id:
            self.env.cr.execute('''DELETE FROM indicator_kcs WHERE request_line_id = %s''' % (self.id))
            for criterions_line in self.criterions_id.ksc_line_ids:
                var = {'check_indicators': criterions_line.check_indicators or False, 'standard': criterions_line.value or 0.0,
                       'type': criterions_line.type or False, 'request_line_id': self.id, 'measured_value': 0.0}
                self.env['indicator.kcs'].create(var)
        return True
    
    @api.multi
    @api.onchange("product_id")
    def onchange_product_id(self):
        tmpl = self.env['product.template']
        if not self.product_id:
            values =  {'categ_id': False}
            self.update(values)
        tmpl_obj = tmpl.browse(self.product_id.product_tmpl_id.id)
        categ_id = tmpl_obj.categ_id.id or False
        values =  {'categ_id': categ_id}
        self.update(values)
            
    @api.multi
    def button_approved(self):
        if not self.move_id and not self.criterions_id:
            raise UserError(_('Unable to approved GRN Quality'))
        self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                
    @api.multi
    def button_reject(self):
        if self.criterions_id.state == 'done' or self.move_id.state == 'done': 
            raise UserError(_('Unable to cancel GRN Quality'))
        self.write({'state': 'cancel'})
    
class IndicatorKCS(models.Model):
    _name = "indicator.kcs"
    
    check_indicators = fields.Char(string="Check Indicators", required=True)
    standard = fields.Float(string="Standard", required=True)
    type = fields.Selection([('bigger', 'Bigger than the reference value'), ('reference', 'By reference value'),
         ('smaller', 'Smaller than the reference value')], string="Type", default='reference', required=True)
    measured_value = fields.Float(string="Measured Value", required=True)
    request_line_id = fields.Many2one("request.kcs.line", string="Request KCS Line", ondelete='cascade', index=True, copy=False)
    note = fields.Text(string="Note", copy=False)

class StockPicking_type(models.Model):
    _inherit = "stock.picking.type"
    
    kcs = fields.Boolean(string="KCS")
    deduct = fields.Boolean(string="Deduct")
    kcs_approved = fields.Boolean(string="Kcs Approved Picking")
    
    
class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    product_kcs = fields.Boolean(string="KCS")
    
class StockMove(models.Model):
    _inherit = "stock.move"
    
    @api.multi
    @api.onchange("init_qty")
    def onchange_init_qty(self):
        for move in self:
            values =  {'product_uom_qty': move.init_qty or 0.0}
            move.update(values)
        
    init_qty = fields.Float(string='Net Weight', digits=(12, 0),copy=True,)
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    def _total_qty(self):
        for order in self:
            total_qty = 0
            total_init_qty = 0
            for line in order.move_lines:
                total_init_qty +=line.init_qty or 0.0
                total_qty +=line.product_uom_qty or 0.0
            order.total_init_qty = total_init_qty or 0.0
            order.total_qty = total_qty or 0.0
            
    total_init_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Init Qty')
    total_qty = fields.Float(compute='_total_qty',digits=(16,2) , string = 'Total Qty')
    
#     request_kcs_id = fields.Many2one("request.kcs", "Request KCS", 
#          states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    state_kcs = fields.Selection(selection=[('draft', 'New'),('approved', 'Approved'),
        ('rejected', 'Rejected'),('cancel', 'Cancel')],string='KCS Status', readonly=True, copy=False, index=True, default='draft',track_visibility='onchange')
    date_kcs = fields.Date(string="KCS Date")
    
    kcs_line = fields.One2many('request.kcs.line','picking_id',string="KCS Line")
    approve_id = fields.Many2one("res.users",string= "Approved")
    kcs_criterions_id = fields.Many2one("kcs.criterions",string= "Rule KCS")
    special = fields.Boolean(string="Special")
    
    @api.multi
    def btt_loads(self):
        for pick in self:
            if not pick.date_kcs:
                pick.date_kcs = time.strftime(DATE_FORMAT)
            if pick.picking_type_id.kcs != True:
                raise UserError(_('Quy trinh khong KCS'))
                continue
            for move in pick.move_lines:
                if move.product_id.product_kcs == True:
                    raise UserError(_('Products %s khong can KCS.')%(move.product_id.name))
                
                kcs_criterions_id = False
                sql ='''
                    SELECT id
                    FROM kcs_criterions
                    WHERE '%s' between from_date and to_date
                        and product_id =%s
                        and (special is null or special =false)
                        and state not in ('draft','cancel')
                    ORDER BY id DESC
                    LIMIT 1
                '''%(pick.date_kcs,move.product_id.id)
                self.env.cr.execute(sql)
                for criterions in self.env.cr.dictfetchall():
                    kcs_criterions_id = criterions['id'] or False
                if not kcs_criterions_id:
                    sql ='''
                    SELECT id
                    FROM kcs_criterions
                    WHERE '%s' between from_date and to_date
                        and categ_id =%s and product_id is null
                        and (special is null or special = false)
                        and state not in ('draft','cancel')
                    ORDER BY id DESC
                    LIMIT 1
                '''%(pick.date_kcs,move.product_id.categ_id.id)
                self.env.cr.execute(sql)
                for criterions in self.env.cr.dictfetchall():
                    kcs_criterions_id = criterions['id'] or False
                
                if not kcs_criterions_id:
                    raise UserError(_('You must define rule KCS.'))
                
                pick.kcs_criterions_id = kcs_criterions_id
                
                self.env.cr.execute('''
                    DELETE FROM request_kcs_line WHERE picking_id = %(picking_id)s;''' % ({'picking_id': self.id}))
                
                var = {'picking_id': pick.id, 
                        'name': move.name or False,
                        'product_id': move.product_id.id or False, 
                        'categ_id': move.product_id.product_tmpl_id.categ_id.id,  
                        'product_qty': move.init_qty or 0.0,
                        'qty_reached': move.init_qty or 0.0,
                        'criterions_id': False,  
                        'product_uom': move.product_uom.id or False,
                        'move_id': move.id or False,
                        'state': 'draft'}
                self.env['request.kcs.line'].create(var)
    
    @api.multi
    def btt_approved(self):
        for pick in self:
            pick.state_kcs = 'approved'
            for line in pick.kcs_line:
                if line.state_kcs != 'draft':
                    continue
                line.state = 'approve'
    
    @api.multi
    def btt_draft(self):
        for pick in self:
#             if pick.state == 'done':
#                 raise UserError(_(u'Bộ phận kho đã nhập kho, muốn điều chỉnh thông báo với bộ phận kho'))
            pick.state_kcs = 'draft'
            pick.action_revert_done()
            for line in pick.kcs_line:
                line.write({'state': 'draft'})
            
                
    @api.multi
    def btt_reject(self):
        for pick in self:
            pick.state_kcs = 'rejected'
            for line in pick.kcs_line:
                if line.state_kcs != 'draft':
                    continue
                line.state = 'rejected'
        
    @api.multi
    def do_new_transfer(self):
        self.ensure_one()
        if self.picking_type_id.kcs == True:
            for move in self.move_lines:
                if move.product_id.product_kcs:
                    if self.state_kcs == 'draft':
                        raise UserError(_('Products %s requiring KCS.')%(move.product_id.name))
        return super(StockPicking, self).do_new_transfer()
