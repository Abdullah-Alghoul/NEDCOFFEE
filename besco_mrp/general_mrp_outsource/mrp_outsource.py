# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

class MRPOutsourceRequest(models.Model):
    _name = "mrp.outsource.request"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'priority DESC,id ASC'
    
    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids
    
    @api.model
    def _src_id_default(self):
        company = self.env.user.company_id.id
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_id.wh_raw_material_loc_id.id
    
    name = fields.Char(string="Requirement", required=True, default="New", copy=False, readonly=True, states={'draft': [('readonly', False)]})
    date = fields.Date(string="Date Of Transfer",default=fields.Datetime.now, readonly=True, states={'draft': [('readonly', False)]})
    deadline = fields.Date(string='Deadline', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Datetime.now)
    type = fields.Selection([('out','Out'),('in','In')], string="Type", default="out")
    picking_no = fields.Char(string="Picking No.", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True, readonly=True, states={'draft': [('readonly', False)]}, change_default=True, track_visibility='always')
    production_id = fields.Many2one("mrp.production", string="Production", required=True, readonly=True, states={'draft': [('readonly', False)]})
    
    request_ids = fields.One2many("mrp.outsource.request.line", "request_id", string="MRP Outsource Request Line", readonly=True, states={'draft': [('readonly', False)]})
    produced_ids = fields.One2many("produced.product", "request_id", string="Produced Product", readonly=True, states={'draft': [('readonly', False)]})
    
    state = fields.Selection([("draft", "New"),("approved", "Approved"),('done','Done'),("cancel", "Cancelled")], string="Status", readonly=True, copy=False, index=True, default='draft')
    note = fields.Text(string="Notes")
    origin = fields.Char(string='Source Document')
    
    request_out_id = fields.Many2one("mrp.outsource.request", string="Outsource Request - Out", domain=[('type','=','out'),('state','=','approved')],readonly=True, states={'draft': [('readonly', False)]})
    
    priority = fields.Selection([('0', 'Not urgent'), ('1', 'Normal'), ('2', 'Urgent'), ('3', 'Very Urgent')], 'Priority', default='1')

    company_id = fields.Many2one('res.company', string='Company', required=True, change_default=True, readonly=True, states={'draft': [('readonly', False)]}, default=lambda self: self.env['res.company']._company_default_get('mrp.outsource.request'))
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_warehouse_id)
    location_src_id = fields.Many2one('stock.location', string='Raw Materials Location', required=True,  readonly=True, states={'draft': [('readonly', False)]}, default=_src_id_default)
    
    create_date = fields.Date(string='Creation Date', readonly=True, index=True, default=fields.Datetime.now, copy=False)
    create_uid = fields.Many2one('res.users', 'Responsible', readonly=True , default=lambda self: self._uid, copy=False)
    date_approve = fields.Date('Approval Date', readonly=True, select=True, copy=False)
    user_approve = fields.Many2one('res.users', string='User Approve', readonly=True, copy=False)
    
    @api.model
    def create(self, vals): 
        if vals.get('name', 'New'):
            if vals.get('type',False) == 'out':
                vals['name'] = self.env['ir.sequence'].next_by_code('outsource.issue')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('outsource.receipt')
        result = super(MRPOutsourceRequest, self).create(vals)
        return result
    
    @api.multi
    def unlink(self):
        for request in self:
            if request.state not in ('draft', 'cancel'):
                raise UserError(_('You can only delete draft or cancel.'))
        return super(MRPOutsourceRequest, self).unlink()
    
    @api.multi
    @api.onchange('warehouse_id')
    def onchange_warehouse_id(self):
        if not self.warehouse_id:
            domain = {"domain": {"location_src_id": []}}
            return domain
        values = {'location_src_id': self.warehouse_id.wh_raw_material_loc_id.id or False}
        self.update(values)
        domain = {"domain": {"location_src_id": [("id","=",self.warehouse_id.wh_raw_material_loc_id.id)]}}
        return domain
        
    @api.multi
    @api.onchange('request_out_id')
    def onchange_request_out_id(self):
        if not self.request_out_id:
            values = {'production_id': False, 'partner_id': False}
            self.update(values)
            domain = {"domain": {"production_id": [], "partner_id": []}}
            return domain
            
        values = {'production_id': self.request_out_id.production_id.id or False, 'partner_id': self.request_out_id.partner_id.id or False}
        self.update(values)
        domain = {"domain": {"production_id": [("id","=",self.request_out_id.production_id.id)],
                     "partner_id": [("id","=",self.request_out_id.partner_id.id)]}}
        return domain
    
    @api.multi
    def button_approve(self):
        if not self.request_ids:
            raise UserError(_('You cannot approve a Request without any Materials.'))
        
        if self.type == 'out' and not self.produced_ids:
            raise UserError(_('You cannot approve a Request without any Products to Produce.'))
        
        picking_type_pool = self.env['stock.picking.type']
        if self.type == "out":
            picking_type_id = self.warehouse_id.outsource_issue_type_id.id or False
            picking_type = picking_type_pool.browse(picking_type_id)
            default_location_src_id = picking_type.default_location_src_id.id or self.warehouse_id.wh_raw_material_loc_id.id or False
            default_location_dest_id = picking_type.default_location_dest_id.id or self.warehouse_id.wh_outsource_loc_id.id or False
        else:
            picking_type_id = self.warehouse_id.outsource_receipt_type_id.id or False
            picking_type = picking_type_pool.browse(picking_type_id)
            default_location_src_id = picking_type.default_location_src_id.id or self.warehouse_id.wh_outsource_loc_id.id or False
            default_location_dest_id = picking_type.default_location_dest_id.id or self.warehouse_id.wh_finished_good_loc_id.id or False
        
        if not picking_type_id:
            raise UserError(_('Not Picking Type,you cannot approve Request.'))
        if not default_location_src_id:
            raise UserError(_('Not Source Location Zone, you cannot approve Request.'))
        if not default_location_dest_id:
            raise UserError(_('Not Destination Location Zone ,You cannot approve Request.'))
        
        var = {'name': '/', 'picking_type_id': picking_type_id, 'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False, 
            'production_id': self.production_id.id or False, 'partner_id': self.partner_id.id,
            'picking_type_code': picking_type.code or False,
            'location_id': default_location_src_id or False,'location_dest_id': default_location_dest_id or False, 'outsouce_id': self.id}  
        picking_id = self.env['stock.picking'].create(var)  
        if picking_id:
            for request_line in self.request_ids:
                self.env['stock.move'].create({'picking_id': picking_id.id or False, 'name': request_line.product_id.name or '', 
                    'product_id': request_line.product_id.id or False,'product_uom': request_line.product_uom.id or False,
                    'product_uom_qty': request_line.product_qty or 0.0, 'price_unit': 0.0, 'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
                    'picking_type_id': picking_type_id or False, 'location_id': default_location_src_id,  'location_dest_id': default_location_dest_id, 
                    'type': picking_type.code or False,  'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'partner_id': self.partner_id.id, 'company_id': self.company_id.id, 'state':'draft', 'scrapped': False, 'warehouse_id': self.warehouse_id.id or False})
        
        self.write({'state': 'approved', 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 'picking_no': picking_id.name or ''})
    
    @api.multi
    def button_cancel(self):
        picking_id = self.env['stock.picking'].search([('outsouce_id','=', self.id)])
        if  self.state == 'done':
            raise UserError(_('You cannot cancel Request.'))
        elif picking_id.state != 'done':
            picking_id.action_cancel()
            self.write({'state': 'cancel'})
            
    @api.multi
    def button_done(self):
        self.write({'state': 'done'})
        
    @api.multi
    def button_load_produced(self):
        if self.production_id:
            self.env.cr.execute('''DELETE FROM MRP_Outsource_Request_Line WHERE request_id = %s''' % (self.id))
            for product_line in self.production_id.product_lines:
                var = {"request_id": self.id ,"product_id": product_line.product_id.id or False, 
                        "product_uom":product_line.product_uom.id or False, "product_qty": product_line.product_qty or 0.0}
                self.env['mrp.outsource.request.line'].create(var)
        return True
    
    @api.multi
    def button_load(self):
        if self.request_out_id:
            self.env.cr.execute('''DELETE FROM MRP_Outsource_Request_Line WHERE request_id = %s''' % (self.id))
            for line in self.request_out_id.produced_ids:
                var = {"request_id": self.id ,"product_id": line.product_id.id or False, 
                        "product_uom":line.product_uom.id or False, "product_qty": line.product_qty or 0.0}
                self.env['mrp.outsource.request.line'].create(var)
        return True
    
class MRPOutsourceRequestLine(models.Model):
    _name = "mrp.outsource.request.line"
    
    sequence = fields.Integer(string='Sequence', default=10)
    request_id = fields.Many2one("mrp.outsource.request", string="MRP Outsource Request", ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    product_qty = fields.Float(string="Qty", required=True)
    product_uom = fields.Many2one("product.uom", string="UoM", required=True)
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'),('cancel', 'Cancelled')],
          related='request_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            values = {'product_uom': False}
            self.update(values)
            domain={"domain":{"product_uom": []}}
            return domain
        values = {'product_uom': self.product_id.uom_id.id or False}
        self.update(values)
        domain={"domain":{"product_uom": [("category_id","=",self.product_id.uom_id.category_id.id)]}}
        return domain
    
class ProducedProduct(models.Model):
    _name = "produced.product"
    
    sequence = fields.Integer(string='Sequence', default=10)
    request_id = fields.Many2one("mrp.outsource.request", string="MRP Outsource Request", ondelete='cascade', index=True, copy=False)
    production_id = fields.Many2one("mrp.production", string="Production")

    operation_id = fields.Many2one("mrp.production.workcenter.line", string="Operation", required=True)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    product_qty = fields.Float(string="Qty", required=True)
    product_uom = fields.Many2one("product.uom", string="UoM", required=True)
    state = fields.Selection(selection=[('draft', 'New'), ('approved', 'Approved'),('cancel', 'Cancelled')],
          related='request_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    
    @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        if not self.product_id:
            values = {'product_uom': False}
            self.update(values)
            domain={"domain":{"product_uom": []}}
            return domain
        values = {'product_uom': self.product_id.uom_id.id or False}
        self.update(values)
        domain={"domain":{"product_uom": [("category_id","=",self.product_id.uom_id.category_id.id)]}}
        return domain
    
    @api.multi
    @api.onchange('operation_id')
    def onchange_operation_id(self):
        if not self.operation_id:
            values = {'product_id': False,'product_uom': False}
            self.update(values)
            domain = {"domain": {"product_id": [], "product_uom": []}}
            
        values = {'product_id': self.operation_id.product_id.id or False,'product_uom': self.operation_id.product_uom.id}
        self.update(values)
        domain = {"domain": {"product_id": [("id","=",self.operation_id.product_id.id)]}}            
        return domain
    
class MRPProduction(models.Model):
    _inherit="mrp.production"
    
    @api.depends('picking_ids')
    def _compute_picking(self):
        for mrp in self:
            pickings = self.env['stock.picking'] 
            outsource_issues = self.env['stock.picking']
            outsource_receipt = self.env['stock.picking']
            for line in mrp.picking_ids:
                moves = line.move_lines.filtered(lambda r: r.state != 'cancel')
                if line.picking_type_code == 'outsource_issue':
                    outsource_issues |= moves.mapped('picking_id')
                elif line.picking_type_code == 'outsource_receipt':
                    outsource_receipt |= moves.mapped('picking_id')
                pickings |= moves.mapped('picking_id')
                
            mrp.outsource_issue_count = len(outsource_issues)
            mrp.outsource_receipt_count = len(outsource_receipt) 
            mrp.picking_ids = pickings

    outsource_issue_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    outsource_receipt_count = fields.Integer(compute='_compute_picking', string='Receptions', default=0)
    picking_ids = fields.One2many('stock.picking','production_id',string='Picking', copy=False)
    
    @api.multi
    def action_view_outsource_issue(self):
        pick_ids = []
        for picking in self.picking_ids:
            if picking.picking_type_code == 'outsource_issue' and picking.state != 'cancel':
                pick_ids.append(picking.id)
                
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['context'] = {}
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False
        return result
    
    @api.multi
    def action_view_outsource_receipt(self):
        request_ids = []
        for picking in self.picking_ids:
            if picking.picking_type_code == 'outsource_issue' and picking.state != 'cancel':
                request_ids.append(picking.id)
                
        action = self.env.ref('stock.action_picking_tree')
        result = action.read()[0]
        pick_ids = sum([order.picking_ids.ids for order in self], [])
        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        elif len(pick_ids) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            result['context'] = {}
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = pick_ids and pick_ids[0] or False