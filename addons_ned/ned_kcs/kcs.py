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
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
# 

class PostShipMentLine(models.Model):
    _inherit = "post.shipment.line"
    
    lot_id = fields.Many2one('lot.kcs', string='Lot manager')
    lot_manager = fields.Char(string='Lot manager')
    
class StockStack(models.Model):
    _inherit = "stock.stack"
    _order = 'create_date desc, id desc'
     
    @api.depends('move_ids','move_ids.picking_id','move_ids.state','move_ids.picking_id.state_kcs','move_ids.picking_id.state','move_ids.picking_id.kcs_line')
    def _compute_qc(self):
        for this in self:
            stick_count = stone_count = mc = immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = excelsa = cherry = mold = fm = black = brown = broken = 0.0
            gip_net = gip_basis = gdn_basis = gdn_net = net_qty = basis_qty = 0.0
            districts_id = production_id = False
            contract_no = remarks =''
            count =0
            net_qty =0.0
            for line in this.move_ids:
                if line.picking_id.picking_type_id.code in ('production_in','transfer_in','incoming','phys_adj'):
                    if  line.state != 'done':
                        continue
                    
                    for kcs in line.picking_id.kcs_line:
                        mc += kcs.mc * line.init_qty or 0.0
                        fm += kcs.fm * line.init_qty or 0.0
                        black += kcs.black * line.init_qty or 0.0
                        broken += kcs.broken * line.init_qty or 0.0
                        brown +=  kcs.brown * line.init_qty or 0.0
                        mold += kcs.mold * line.init_qty or 0.0
                        cherry += kcs.cherry * line.init_qty or 0.0
                        excelsa += kcs.excelsa * line.init_qty or 0.0
                        screen18 += kcs.screen18 * line.init_qty or 0.0
                        screen16 += kcs.screen16 * line.init_qty or 0.0
                        screen13 += kcs.screen13 * line.init_qty or 0.0
                        belowsc12 += kcs.belowsc12 * line.init_qty or 0.0
                        burned += kcs.burned * line.init_qty or 0.0
                        eaten += kcs.eaten * line.init_qty or 0.0
                        immature += kcs.immature * line.init_qty or 0.0
                        stick_count = kcs.stick_count 
                        stone_count = kcs.stone_count 
                        maize_yn = kcs.maize_yn
                        count += line.init_qty
                        
                    packing_id = line.picking_id.packing_id and line.picking_id.packing_id.id
                    net_qty += line.init_qty
                    basis_qty += line.product_uom_qty
                    
                    if line.picking_id.note:
                        remarks += line.picking_id.note +', '
                    
                    if line.picking_id.contract_no:
                        contract_no += line.picking_id.contract_no +', '
                    
#                     if line.picking_id.districts_id:
#                         districts_id = line.picking_id.districts_id.id
                    
                    if line.picking_id.production_id:
                        production_id = line.picking_id.production_id.id
                        
                if line.picking_id.picking_type_id.code in('outgoing','transfer_out') and line.state == 'done':
                    gdn_basis += line.product_qty
                    gdn_net += line.init_qty
                
                if line.picking_id.picking_type_id.code == 'production_out' and line.state == 'done':
                    gip_net += line.init_qty
                    gip_basis += line.product_qty        
         
            if count !=0:
                this.update({'mc':mc/count,'cherry':cherry/count,'fm':fm/count,'black':black/count,'broken':broken/count,
                            'brown':brown/count,'mold':mold/count,'cherry':cherry/count,'excelsa':excelsa/count,'screen18':screen18/count,
                            'screen16':screen16/count,'screen13':screen13/count,'screen12':belowsc12/count,'burn':burned/count,'eaten':eaten/count,
                            'immature':immature/count,'stick_count':stick_count,'stone_count':stone_count,'maize':maize_yn,
                            'packing_id':packing_id,'net_qty':net_qty,'basis_qty':basis_qty,'remarks':remarks,
                            'gdn_basis':gdn_basis,'gdn_net':gdn_net,'gip_net':gip_net,'gip_basis':gip_basis,
                            'production_id':production_id})
    
    production_id = fields.Many2one('mrp.production',string="Production",compute='_compute_qc',store=True)
                     
    mc = fields.Float(string="MC",compute='_compute_qc',group_operator="avg", digits=(12, 2),store=True)
    fm = fields.Float(compute='_compute_qc',string="Fm",group_operator="avg",  digits=(12, 2),store=True)
    black = fields.Float(compute='_compute_qc',string="Black",group_operator="avg",  digits=(12, 2),store=True)
    broken = fields.Float(compute='_compute_qc',string="Broken", group_operator="avg", digits=(12, 2),store=True)
    brown = fields.Float(compute='_compute_qc',string="Brown", group_operator="avg", digits=(12, 2),store=True) 
    mold = fields.Float(compute='_compute_qc',string="Mold", group_operator="avg", digits=(12, 2),store=True) 
    immature = fields.Float(compute='_compute_qc',string="immature",group_operator="avg",  digits=(12, 2),store=True)
     
    burn = fields.Float(compute='_compute_qc',string="Burn", group_operator="avg",  digits=(12, 2),store=True) 
    eaten = fields.Float(compute='_compute_qc',string="Eaten", group_operator="avg", digits=(12, 2),store=True) 
    cherry = fields.Float(compute='_compute_qc',string="Cherry",group_operator="avg",  digits=(12, 2),store=True) 
    maize = fields.Char(string="Maize") 
    stone_count = fields.Char(string="Stone",compute='_compute_qc',group_operator="avg",  store=True) 
    stick_count = fields.Char(string="Stick",compute='_compute_qc',group_operator="avg",  store=True) 
    screen18 = fields.Float(compute='_compute_qc',string="Screen18",group_operator="avg",   digits=(12, 2),store=True) 
    screen16 = fields.Float(compute='_compute_qc',string="Screen16",group_operator="avg",   digits=(12, 2),store=True) 
    screen13 = fields.Float(compute='_compute_qc',string="Screen13",group_operator="avg",   digits=(12, 2),store=True) 
    screen12 = fields.Float(compute='_compute_qc',string="Below Screen12",group_operator="avg",   digits=(12, 2),store=True) 
    excelsa = fields.Float(compute='_compute_qc',string="Excelsa",group_operator="avg",  digits=(12, 2),store=True) 
    
    packing_id = fields.Many2one('ned.packing',string="Packing",compute='_compute_qc',store=True)
    
    net_qty = fields.Float(compute='_compute_qc',string="NET Qty",  digits=(12, 0),store=True) 
    basis_qty = fields.Float(compute='_compute_qc',string="Basis Qty",  digits=(12, 0),store=True) 
    remarks = fields.Char(string="Remarks",compute='_compute_qc',store=True)
    remarks_note = fields.Char(string="Remark Note")
    gdn_basis = fields.Float(compute='_compute_qc',string="Gdn Basis Qty",  digits=(12, 0),store=True) 
    gdn_net = fields.Float(compute='_compute_qc',string="Gdn Net Qty",  digits=(12, 0),store=True) 
    
    gip_net = fields.Float(compute='_compute_qc',string="Gip Net Qty",  digits=(12, 0),store=True) 
    gip_basis = fields.Float(compute='_compute_qc',string="Gip Basis Qty",  digits=(12, 0),store=True) 
    contract_no = fields.Char(string="Contract No",compute='_compute_qc',store=True)
#     districts_id = fields.Many2one('res.district',compute='_compute_qc', string='Source')
    
    
    
    def get_datetime(self, date):
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%Y')
    
    @api.depends('date')
    def _compute_date(self):
        for line in self:
            if line.date:
                line.year_tz = self.get_datetime(line.date)
            else:
                line.year_tz = False
    
    year_tz = fields.Char(compute='_compute_date',string = "Year", store=True)
    

class LotKcs(models.Model):
    _name ="lot.kcs"
    _order = "id desc"
    
    name = fields.Char(string="Lot no")
    lot_date = fields.Date(string="Date")
    contract_id = fields.Many2one('s.contract',string="S Contract")
    #lot_quantity = fields.Float(string="Lot Quantity")
    mc = fields.Float(string="MC")
    cup_test = fields.Char(string="Cup Test")
    los_ids = fields.One2many('lot.stack.allocation', 'lot_id', string="Lot Allocation", readonly=True)
    product_id = fields.Many2one(related='contract_id.product_id',  string='Product',store=True)
    
    @api.depends('mc','quantity','mc_on_despatch','defects','los_ids','los_ids.quantity','los_ids.stack_id','los_ids.grp_id','state','los_ids.grp_id.state_kcs')
    def _compute_qc(self):
        for line in self:
            stick_count = stone_count = mc = immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = excelsa = cherry = mold = fm = black = brown = broken = 0.0
            count =0
            for lot in line.los_ids:
                mc += lot.stack_id.mc * lot.quantity or 0.0
                fm += lot.stack_id.fm * lot.quantity or 0.0
                black += lot.stack_id.black * lot.quantity or 0.0
                broken += lot.stack_id.broken * lot.quantity or 0.0
                brown +=  lot.stack_id.brown * lot.quantity or 0.0
                mold += lot.stack_id.mold * lot.quantity or 0.0
                cherry += lot.stack_id.cherry * lot.quantity or 0.0
                excelsa += lot.stack_id.excelsa * lot.quantity or 0.0
                screen18 += lot.stack_id.screen18 * lot.quantity or 0.0
                screen16 += lot.stack_id.screen16 * lot.quantity or 0.0
                screen13 += lot.stack_id.screen13 * lot.quantity or 0.0
                belowsc12 += lot.stack_id.screen12 * lot.quantity or 0.0
                burned += lot.stack_id.burn * lot.quantity or 0.0
                eaten += lot.stack_id.eaten * lot.quantity or 0.0
                immature += lot.stack_id.immature *  lot.quantity or 0.0
                stick_count = lot.stack_id.stick_count 
                stone_count = lot.stack_id.stone_count 
                count += lot.quantity
                
                
            line.mc = count and mc/count or 0.0
            line.fm = count and fm/count or 0.0
            line.black = count and black/count or 0.0
            line.broken = count and broken/count or 0.0
            line.brown = count and brown/count or 0.0
            line.mold = count and mold/count or 0.0
            line.cherry = count and cherry/count or 0.0
            line.excelsa = count and excelsa/count or 0.0
            line.screen18 = count and screen18/count or 0.0
            line.screen16 = count and screen16/count or 0.0
            line.screen13 = count and screen13/count or 0.0
            line.screen12 = count and belowsc12/count or 0.0
              
            line.burn = count and burned/count or 0.0
            line.eaten = count and eaten/count or 0.0
            line.immature = count and immature/count or 0.0
            line.stick_count = stick_count
            line.stone_count = stone_count
                
    mc = fields.Float(string="MC",compute='_compute_qc', digits=(12, 2),store=True)
    fm = fields.Float(compute='_compute_qc',string="Fm",  digits=(12, 2),store=True)
    black = fields.Float(compute='_compute_qc',string="Black",  digits=(12, 2),store=True)
    broken = fields.Float(compute='_compute_qc',string="Broken",  digits=(12, 2),store=True)
    brown = fields.Float(compute='_compute_qc',string="Brown",  digits=(12, 2),store=True) 
    mold = fields.Float(compute='_compute_qc',string="Mold",  digits=(12, 2),store=True) 
    immature = fields.Float(compute='_compute_qc',string="immature",  digits=(12, 2),store=True)
    
    burn = fields.Float(compute='_compute_qc',string="Burn",  digits=(12, 2),store=True) 
    eaten = fields.Float(compute='_compute_qc',string="Eaten",  digits=(12, 2),store=True) 
    cherry = fields.Float(compute='_compute_qc',string="Cherry",  digits=(12, 2),store=True) 
    maize = fields.Char(string="Maize") 
    stone = fields.Char(string="Stone") 
    stick = fields.Char(string="Stick") 
    screen18 = fields.Float(compute='_compute_qc',string="Screen18",  digits=(12, 2),store=True) 
    screen16 = fields.Float(compute='_compute_qc',string="Screen16",  digits=(12, 2),store=True) 
    screen13 = fields.Float(compute='_compute_qc',string="Screen13",  digits=(12, 2),store=True) 
    screen12 = fields.Float(compute='_compute_qc',string="Screen12",  digits=(12, 2),store=True) 
    excelsa = fields.Float(compute='_compute_qc',string="Excelsa",  digits=(12, 2),store=True) 
    
    cuptaste = fields.Char(string="Cuptaste",readonly=True,store=False,related='los_ids.cuptaste', )
    supervisor = fields.Char(string="Supervisor")
    
    quantity = fields.Float(string="Quantity")
    delivery_id = fields.Many2one('delivery.order',string="Do no.")
    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approve')], string="State", required=True, default="draft")
    grp_id = fields.Many2one('stock.picking',string="GRP", domain="[('production_id', '!=', False),('state', '=', 'done'),('picking_type_id.code', '=', 'production_in')]")
    stack_id = fields.Many2one('stock.stack', string="Stack", readonly=False,store=True)
    nvs_id = fields.Many2one('sale.contract', string="NVS - Nls",domain="[('scontract_id', '=', contract_id)]")
    partner_id = fields.Many2one('res.partner',related='nvs_id.partner_id', string="Customer")
    lot_ned = fields.Char(string="Lot Ned")
    
    @api.depends('los_ids','los_ids.mc_on_despatch')
    def _compute_mc_on_despatch(self):
        for order in self:
            defects = mc_on_despatch = 0
            count =0
            for line in order.los_ids:
                mc_on_despatch += line.mc_on_despatch
                defects += line.defects
                count +=1
            if count:
                order.mc_on_despatch = mc_on_despatch/count
                order.defects = defects/count
            else:
                order.mc_on_despatch =0.0
            
    mc_on_despatch = fields.Float(compute='_compute_mc_on_despatch',string="Mc On Despatch",  digits=(12, 2),store=True) 
    defects = fields.Float(compute='_compute_mc_on_despatch', digits=(12, 2),store=True, string="Defects") 
    
    @api.depends('los_ids','los_ids.quantity')
    def _total_qty(self):
        for order in self:
            total_qty = 0
            for line in order.los_ids:
                total_qty += line.quantity
            order.lot_quantity = total_qty
            
    lot_quantity = fields.Float(compute='_total_qty', digits=(16, 0) , string='Lot Quantity',store=True)
    qty_scontract = fields.Float(related='contract_id.total_qty',  string='Qty SContract',store=True)
        
#     @api.model
#     def create(self, vals):
#         vals['name'] = self.env['ir.sequence'].next_by_code('lot.kcs') 
#        r esult = super(LotKcs, self).create(vals)
#         return result
     
class LotStackAllocation(models.Model):
    _name ="lot.stack.allocation"
    _order = "id desc"
    
    lot_id = fields.Many2one('lot.kcs',string="Lot no.")
    #stack_id = fields.Many2one('stock.stack',string="Stack")
    quantity = fields.Float(string="Quantity")
    delivery_id = fields.Many2one('delivery.order',string="Do no.")
    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approve')], string="State", required=True, default="draft")
    grp_id = fields.Many2one('stock.picking',string="GRP", domain="[('state', '=', 'done'),('picking_type_id.code', 'in', ('production_in','incoming'))]")
    stack_id = fields.Many2one('stock.stack', string="Stack", readonly=False)
    contract_id = fields.Many2one(related='lot_id.contract_id',  string='S Contract',store = True)
    zone_id = fields.Many2one('stock.zone',related='stack_id.zone_id', string="Zone", readonly=True,store=True)
    mc_on_despatch = fields.Float(string="Mc On Despatch")
    cuptaste = fields.Char(string="Cuptaste",)
    defects = fields.Float(string="Defects-ISO",  digits=(12, 2)) 
    defects_tcvn = fields.Float(string="Defects-TCVN",  digits=(12, 2)) 
    gdn_id = fields.Many2one('stock.picking',string="GDN",readonly=True) 
    product_id = fields.Many2one(related='lot_id.product_id',string="Product",readonly=True,store=True) 
    nvs_id = fields.Many2one(related='lot_id.nvs_id', string="NVS - NLS",readonly=True,store=True)
    
    @api.multi
    def btt_confirm(self):
        #self.update_gdn()
        for this in self:
            
            if this.delivery_id:
                packing_id = False
                if this.stack_id.move_ids:
                    for q in this.stack_id.move_ids:
                        if q.location_id.usage =='production' and q.location_dest_id.usage== 'internal':
                            if q.packing_id:
                                packing_id = q.packing_id.id
                if this.delivery_id.type =='Sale':
                    
                    if this.quantity == 0:
                        raise UserError(_('Quantity > 0'))
                    warehouse = this.delivery_id.warehouse_id
                    if not warehouse:
                        company = self.env.user.company_id.id 
                        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
                    
                    if this.nvs_id.type !='local':
                        picking_type_id = warehouse.out_type_id
                    else:
                        picking_type_id = warehouse.out_type_local_id
                    
                    if not picking_type_id:
                        raise UserError(_('Chưa định nghĩa Picking '))
                        
                    if this.delivery_id and not this.delivery_id.picking_id:
                        var = {'name': '/', 
                               'picking_type_id': picking_type_id.id or False, 
                               'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
                               'origin':this.delivery_id.name,
                               'partner_id': this.delivery_id.partner_id.id or False,
                               'picking_type_code': picking_type_id.code or False,
                               'location_id': picking_type_id.default_location_src_id.id or False, 
                               'vehicle_no':this.delivery_id.trucking_no or '',
                               'location_dest_id': picking_type_id.default_location_dest_id.id or False, 
                               'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)}
                        picking_id = self.env['stock.picking'].create(var)  
                        this.delivery_id.picking_id = picking_id.id
                    else:
                        picking_id = this.delivery_id.picking_id
                         
                    if not this.gdn_id:
                        this.gdn_id = picking_id.id
                         
                    self.env['stock.move'].create({'picking_id': picking_id.id or False, 
                           'name': this.product_id.name or '', 
                           'product_id': this.product_id.id or False,
                           'product_uom': this.product_id.uom_id.id or False, 
                           'product_uom_qty': this.quantity or 0.0,
                           'init_qty':this.quantity or 0.0,
                           'price_unit': 0.0,
                           'picking_type_id': picking_type_id.id or False, 
                           'location_id': picking_type_id.default_location_src_id.id or False, 
                           'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                           'location_dest_id': picking_type_id.default_location_dest_id.id or False, 
                           'type': picking_type_id.code or False,
                           'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
                           'partner_id': this.lot_id.contract_id.partner_id.id or False,
                           'company_id': 1,
                           'state':'draft', 
                           'scrapped': False, 
                           #'grp_id':this.grp_id.id,
                           'zone_id':this.zone_id.id,
                           'stack_id':this.stack_id.id,
                           'packing_id':packing_id,
                           'warehouse_id': warehouse.id or False})
                    this.state = 'approve'
                else:
                    if self.delivery_id.type == 'Transfer':
                        warehouse = this.delivery_id.from_warehouse_id
                        move = self.env['stock.move']
                        if self.delivery_id.warehouse_id.transfer_out_id:
                            picking_type = self.delivery_id.from_warehouse_id.transfer_out_id
                            if this.delivery_id and not this.delivery_id.picking_id:
                                picking_type = self.delivery_id.from_warehouse_id.transfer_out_id
                                names = self.delivery_id.name
                                val={
                                        'name':'/',
                                        'picking_type_id':picking_type.id,
                                        'delivery_order_id':self.delivery_id.id,
                                        'location_id':picking_type.default_location_src_id.id,
                                        'location_dest_id':picking_type.default_location_dest_id.id,
                                        'origin':names,
                                        'transfer':False,
                                        'state':'draft',
                                        'picking_type_code':picking_type.code or False,
                                    }
                                picking_id = self.env['stock.picking'].create(val)
                                this.delivery_id.picking_id = picking_id.id
                            else:
                                picking_id = this.delivery_id.picking_id
                            
                            if not this.gdn_id:
                                this.gdn_id = picking_id.id
                            
                            product_id = this.product_id and this.product_id or this.delivery_id.product_id  
                            
                            move_vals ={
                                        'name': product_id.name or '', 
                                        'product_id': product_id.id or False,
                                        'product_uom': product_id.uom_id.id or False, 
                                        'product_uom_qty': this.quantity or 0.0,
                                        'init_qty':this.quantity or 0.0,
                                        'price_unit': 0.0,
                                        'picking_id': picking_id.id, 
                                        'init_qty':this.quantity or 0.0,
                                        'product_uom_qty': this.quantity or 0.0,
                                        'price_unit': 0.0,
                                        'picking_type_id': picking_type.id,
                                        'location_id': picking_type.default_location_src_id.id or False,
                                        'location_dest_id': picking_type.default_location_dest_id.id or False, 
                                        'date_expected': time.strftime('%Y-%m-%d %H:%M:%S') or False,
                                        'company_id': 1, 
                                        'state':'draft', 'scrapped': False, 
                                        'warehouse_id': warehouse.id or False,
                                        'zone_id':this.zone_id.id,
                                        'stack_id':this.stack_id.id,
                                        'packing_id':packing_id
                                }
                            
                            move.create(move_vals)
                            self.picking_id = picking_id.id
                        this.state = 'approve'
            
    @api.multi
    def btt_settodraft(self):
        for this in self:
            move_id = self.env['stock.move'].search([('product_id','=',this.product_id.id),
                                            ('init_qty','=',this.quantity),('stack_id','=',this.stack_id.id)])
            if move_id.picking_id.state =='done':
                a = move_id.picking_id.name + u' Đã Done'
                raise UserError(_(a))
            if move_id: 
                move_id.unlink()
            this.state = 'draft'
            
                
class DeliveryOrder(models.Model):
    _inherit = "delivery.order"
    
    #do_kcs = fields.One2many('do.kcs', 'do_id', string="DO KCS")
    
    @api.depends('fm','product_id','picking_id','picking_id.state')
    def _compute_qc(self):
        for line in self:
            if line.picking_id and line.product_id:
                immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = excelsa = cherry = mold = fm = black = brown = broken = 0.0
                count =0
                for move_line in line.picking_id.move_lines:
                    if move_line.product_id.id == line.product_id.id:
                          
                        for move in move_line.stack_id.move_ids:
                            if move.trans_type !='In':
                                continue
                            for kcs in move.picking_id.kcs_line:
                                fm += kcs.fm or 0.0
                                black += kcs.black or 0.0
                                broken += kcs.broken or 0.0
                                brown +=  kcs.brown or 0.0
                                mold += kcs.mold or 0.0
                                cherry += kcs.cherry or 0.0
                                excelsa += kcs.excelsa or 0.0
                                screen18 += kcs.screen18 or 0.0
                                screen16 += kcs.screen16 or 0.0
                                screen13 += kcs.screen13 or 0.0
                                belowsc12 += kcs.belowsc12 or 0.0
                                burned += kcs.burned or 0.0
                                eaten += kcs.eaten or 0.0
                                immature += kcs.immature or 0.0
                                count +=1
                                  
                line.fm = count and fm/count or 0.0
                line.black = count and black/count or 0.0
                line.broken = count and black/count or 0.0
                line.brown = count and brown/count or 0.0
                line.mold = count and mold/count or 0.0
                line.cherry = count and cherry/count or 0.0
                line.excelsa = count and excelsa/count or 0.0
                line.screen18 = count and screen18/count or 0.0
                line.screen16 = count and screen16/count or 0.0
                line.screen13 = count and screen13/count or 0.0
                line.screen12 = count and belowsc12/count or 0.0
                  
                line.burn = count and burned/count or 0.0
                line.eaten = count and eaten/count or 0.0
                line.immature = count and immature/count or 0.0
     
    lot_no = fields.Char(string="Lot No")      
#     date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
#     day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
    
    mc = fields.Float(string="MC")
    fm = fields.Float(compute='_compute_qc',string="Fm",  digits=(12, 2),store=True)
    black = fields.Float(compute='_compute_qc',string="Black",  digits=(12, 2),store=True)
    broken = fields.Float(compute='_compute_qc',string="Broken",  digits=(12, 2),store=True)
    brown = fields.Float(compute='_compute_qc',string="Brown",  digits=(12, 2),store=True) 
    mold = fields.Float(compute='_compute_qc',string="Mold",  digits=(12, 2),store=True) 
    immature = fields.Float(compute='_compute_qc',string="immature",  digits=(12, 2),store=True)
    defects = fields.Float(string="Defects",  digits=(12, 2)) 
    burn = fields.Float(compute='_compute_qc',string="Burn",  digits=(12, 2),store=True) 
    eaten = fields.Float(compute='_compute_qc',string="Eaten",  digits=(12, 2),store=True) 
    cherry = fields.Float(compute='_compute_qc',string="Cherry",  digits=(12, 2),store=True) 
    maize = fields.Float(string="Maize",  digits=(12, 2),store=True) 
    stone = fields.Float(string="Stone",  digits=(12, 2),store=True) 
    stick = fields.Float(string="Stick",  digits=(12, 2),store=True) 
    screen18 = fields.Float(compute='_compute_qc',string="Screen18",  digits=(12, 2),store=True) 
    screen16 = fields.Float(compute='_compute_qc',string="Screen16",  digits=(12, 2),store=True) 
    screen13 = fields.Float(compute='_compute_qc',string="Screen13",  digits=(12, 2),store=True) 
    screen12 = fields.Float(compute='_compute_qc',string="Screen12",  digits=(12, 2),store=True) 
    excelsa =  fields.Float(compute='_compute_qc',string="Excelsa",  digits=(12, 2),store=True) 
    cuptaste = fields.Char(string="Cuptaste")
    supervisor = fields.Char(string="Supervisor")
    
    @api.multi
    def button_approve_kcs(self):
        for delivery in self:
            delivery.state_kcs = 'approve'
            
    @api.multi
    def button_load_kcs(self):
        product_list =[]
        for do in self:
            sql ='''
                DELETE FROM do_kcs where do_id = %s
            '''%(do.id)
            self.env.cr.execute(sql)
            
            for move in do.picking_id.move_lines:
                if move.product_id not in product_list:
                    product_list.append(move.product_id)
            for product_id in product_list:
                vals ={
                       'product_id':product_id.id,
                       'do_id':do.id,
                       }
                self.env['do.kcs'].create(vals)
            return
    
    
class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    @api.depends('move_lines.product_uom_qty','move_lines','move_lines.product_qty')
    def _total_qty(self):
        for order in self:
            total_qty = total_bag = total_weighbridge_qty = total_init_qty = 0
            for line in order.move_lines:
                total_qty +=line.product_uom_qty or 0.0
                total_init_qty +=line.init_qty or 0.0
                total_weighbridge_qty += line.weighbridge or 0.0
                total_bag += line.bag_no
                
            order.total_qty = total_qty
            order.total_init_qty = total_init_qty or 0.0
            order.total_bag = total_bag or 0.0
            order.total_weighbridge_qty = total_weighbridge_qty or 0.0
            
    total_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Total Qty',store=True)
    total_init_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Init Qty',store=True)
    total_weighbridge_qty = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Real Qty',store=True)
    total_bag = fields.Float(compute='_total_qty',digits=(16,0) , string = 'Bag',store=True)
    
    contract_no = fields.Char(string="Contract no")
    date_sent = fields.Datetime('Date Sent',default= time.strftime(DATETIME_FORMAT))
    
    
    change_product_id = fields.Many2one('product.product','Change Product')
    packing_id = fields.Many2one(related='move_lines.packing_id',  string='Packing',store = True)
    
    @api.multi
    def btt_change_product(self):
        
#         avs = self.env['account.invoice'].search([('state','!=','draft'),('stock_move_id','=',False),('type','=','out_invoice')])
#         for inv in avs:
#             if not inv.stock_move_id:
# #                 inv.action_cancel()
# #                 inv.action_cancel_draft()
# #                 inv.signal_workflow('invoice_open')
#                 inv.create_stock_move()
#         
        for pick in self:
            if pick.state =='done' and pick.state_kcs == 'approved':
                raise UserError(_('You much select Stack'))
            
            if pick.change_product_id:
                #Change cho KCs
                for kcs_line in pick.kcs_line:
                    kcs_line.product_id = pick.change_product_id.id
                #Change cho Stock Move
                for move in pick.move_lines:
                    move.prduct_id = pick.change_product_id.id
                    move.product_uom_qty = move.init_qty
                pick.product_id = pick.change_product_id.id
                if pick.state =='draft':
                    pick.action_confirm()   
                 
                #Change cho san xuat
                sql ='''
                    select id from mrp_operation_result_produced_product where picking_id =%s
                '''%(pick.id)
                self.env.cr.execute(sql)
                for line in self.env.cr.dictfetchall():
                    result = self.env['mrp.operation.result.produced.product'].browse(line['id'])
                    result.product_id = pick.change_product_id.id
                     
                pick.note = '''Change %s'''%(pick.change_product_id.default_code)
            
        return
        
    @api.multi
    def do_new_transfer(self):
        for this in self:
            this.ensure_one()
            if this.picking_type_id.stack == True:
                for move in this.move_lines:
                    if not move.stack_id:
                        raise UserError(_('You much select Stack'))
            if this.picking_type_id.kcs == True:
                if this.state_kcs == 'draft':
                    raise UserError(_('Name %s requiring KCS.')%(self.name))
            
        return super(StockPicking, self).do_new_transfer()
    
    #Kiet: Check cancel in case Warehouse Transfers
    @api.multi
    def action_cancel(self):
        for this in self:
            this.state_kcs = 'cancel'
        super(StockPicking, self).action_cancel()
        
        
    @api.multi
    def btt_reject(self):
        for pick in self:
            pick.action_cancel()
            pick.state_kcs = 'rejected'
            pick.date_done =time.strftime(DATETIME_FORMAT)
            if pick.picking_type_code == 'production_in':
                produced_product = self.env['mrp.operation.result.produced.product'].search([('picking_id','=',pick.id)])
                if produced_product:
                    produced_product.kcs_notes = pick.note or False
                    for line in produced_product.operation_result_id.consumed_products:
                        line.check_kcs = False
                    
                    for line in produced_product.operation_result_id.operation_id.produce_ids:
                        for move_line in pick.move_lines:
                            if move_line.product_id == line.product_id:
                                line.check_kcs = False
            
            for line in pick.kcs_line:
                line.state = 'reject'
                
                return
    @api.multi
    def btt_approved(self):
        if not self.kcs_line:
            raise UserError(_('You cannot approve a Request KCS without any Request KCS Line.'))
        for pick in self:
            pick.state_kcs = 'approved'
            for line in pick.kcs_line:
                if line.state != 'draft':
                    continue
                line.state = 'approved'
                if pick.picking_type_id.deduct:
                    line.move_id.write({'product_uom_qty': line.basis_weight or 0.0})
                else:
                    line.move_id.write({'product_uom_qty': line.product_qty or 0.0})
                
                produced_product = self.env['mrp.operation.result.produced.product'].search([('picking_id','=',pick.id)])
                if produced_product:
                    produced_product.kcs_notes = pick.note or False
        self.write({'state_kcs': 'approved', 'approve_id': self.env.uid,
            'date_kcs': time.strftime(DATE_FORMAT)})
        if self.picking_type_code == 'production_in':
            pick.name =  pick.picking_type_id.sequence_id.with_context(ir_sequence_date=self.date_kcs).next_by_id()
            
        if self.picking_type_id.kcs_approved:
            operation = self.env['stock.pack.operation'].search([('picking_id','=',self.id)])
            for i in self.kcs_line:
                if i.product_id == operation.product_id:
                    operation.write({'product_qty':i.basis_weight,'qty_done':i.basis_weight})
            self.action_done()
            
    
    @api.multi
    def report_qa_production(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'qa_production_report',
                }
    
    @api.multi
    def report_qa_gdn(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'qa_gdn_report',
                }
    
    @api.multi
    def report_qa_grn(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'qa_grn_report',
                }
    

# class DoKCS(models.Model):
#     _name ="do.kcs"
#     
#     def get_vietname_date(self, date):
#         if not date:
#             date = time.strftime(DATE_FORMAT)
#         date = datetime.strptime(date, DATE_FORMAT)
#         return date.strftime('%d-%m-%Y')
    
#     @api.depends('do_id','fm','product_id','picking_id')
#     def _compute_qc(self):
#         for line in self:
#             if line.do_id.picking_id and line.product_id:
#                 immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = excelsa = cherry = mold = fm = black = brown = broken = 0.0
#                 count =0
#                 for move_line in line.do_id.picking_id.move_lines:
#                     if move_line.product_id.id == line.product_id.id:
#                         
#                         for move in move_line.stack_id.move_ids:
#                             if move.trans_type !='In':
#                                 continue
#                             for kcs in move.picking_id.kcs_line:
#                                 fm += kcs.fm or 0.0
#                                 black += kcs.black or 0.0
#                                 broken += kcs.broken or 0.0
#                                 brown +=  kcs.brown or 0.0
#                                 mold += kcs.mold or 0.0
#                                 cherry += kcs.cherry or 0.0
#                                 excelsa += kcs.excelsa or 0.0
#                                 screen18 += kcs.screen18 or 0.0
#                                 screen16 += kcs.screen16 or 0.0
#                                 screen13 += kcs.screen13 or 0.0
#                                 belowsc12 += kcs.belowsc12 or 0.0
#                                 burned += kcs.burned or 0.0
#                                 eaten += kcs.eaten or 0.0
#                                 immature += kcs.immature or 0.0
#                                 count +=1
#                                 
#                 line.fm = count and fm/count or 0.0
#                 line.black = count and black/count or 0.0
#                 line.broken = count and black/count or 0.0
#                 line.brown = count and brown/count or 0.0
#                 line.mold = count and mold/count or 0.0
#                 line.cherry = count and cherry/count or 0.0
#                 line.excelsa = count and excelsa/count or 0.0
#                 line.screen18 = count and screen18/count or 0.0
#                 line.screen16 = count and screen16/count or 0.0
#                 line.screen13 = count and screen13/count or 0.0
#                 line.screen12 = count and belowsc12/count or 0.0
#                 
#                 line.burn = count and burned/count or 0.0
#                 line.eaten = count and eaten/count or 0.0
#                 line.immature = count and immature/count or 0.0
                
            
                
    
#     lot_no = fields.Integer(string="Lot No")      
#     date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
#     day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)
#     product_id = fields.Many2one('product.product',string="Product",)
#     do_id = fields.Many2one('delivery.order',string ="Do")
#     do_date = fields.Date(related='do_id.date', string="Do Date", readonly=True)
#     picking_id = fields.Many2one('stock.picking',related='do_id.picking_id', string="Picking", readonly=True)
#     do_qty = fields.Float(string="Do Qty",related='do_id.total_qty',digits=(12, 0))
#     mc = fields.Float(string="MC")
#     fm = fields.Float(compute='_compute_qc',string="Fm",  digits=(12, 2))
#     black = fields.Float(compute='_compute_qc',string="Black",  digits=(12, 2))
#     broken = fields.Float(compute='_compute_qc',string="Broken",  digits=(12, 2))
#     brown = fields.Float(compute='_compute_qc',string="Brown",  digits=(12, 2)) 
#     mold = fields.Float(compute='_compute_qc',string="Mold",  digits=(12, 2)) 
#     immature = fields.Float(compute='_compute_qc',string="immature",  digits=(12, 2))
#     defects = fields.Float(string="Defects",  digits=(12, 2)) 
#     burn = fields.Float(compute='_compute_qc',string="Burn",  digits=(12, 2)) 
#     eaten = fields.Float(compute='_compute_qc',string="Eaten",  digits=(12, 2)) 
#     cherry = fields.Float(compute='_compute_qc',string="Cherry",  digits=(12, 2)) 
#     maize = fields.Float(string="Maize",  digits=(12, 2)) 
#     stone = fields.Float(string="Stone",  digits=(12, 2)) 
#     stick = fields.Float(string="Stick",  digits=(12, 2)) 
#     screen18 = fields.Float(compute='_compute_qc',string="Screen18",  digits=(12, 2)) 
#     screen16 = fields.Float(compute='_compute_qc',string="Screen16",  digits=(12, 2)) 
#     screen13 = fields.Float(compute='_compute_qc',string="Screen13",  digits=(12, 2)) 
#     screen12 = fields.Float(compute='_compute_qc',string="Screen12",  digits=(12, 2)) 
#     cuptaste = fields.Char(string="Cuptaste")
#     supervisor = fields.Char(string="Supervisor")
    
    
class KCSCriterions(models.Model):
    _inherit = "kcs.criterions"
    
    broken_standard_ids = fields.One2many("broken.standard", "criterion_id", string="Broken",readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    brown_standard_ids = fields.One2many("brown.standard", "criterion_id", string="Brown",readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    mold_standard_ids = fields.One2many("mold.standard", "criterion_id", string="Mold",readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    
    standard_excelsa = fields.Float(string="Excelsa_%",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    percent_excelsa = fields.Float(string="Percent", digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    
    standard_screen18_16 = fields.Float(string="OverScreen16_%",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    percent_screen18_16 = fields.Float(string="Percent",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    standard_screen13 = fields.Float(string="OverScreen13_%",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    percent_screen13 = fields.Float(string="Percent",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    
    standard_burned = fields.Float(string="Burned_%",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    percent_burned = fields.Float(string="Percent",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    percent_fm = fields.Float(string="Fm",default="0.01",  digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    
class RequestKCS(models.Model):
    _inherit = "request.kcs"            
                       
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
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code  == 'outgoing':
                    if move.product_id.kcs_outgoing == True:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code  == 'internal':
                    if move.product_id.kcs_internal:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'internal':
                    if move.product_id.kcs_internal:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'production_out':
                    if move.product_id.kcs_production_out:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
                        self.env['request.kcs.line'].create(var)
                elif self.picking_type_id.code == 'production_in':
                    if move.product_id.kcs_production_in:
                        tmpl_obj = tmpl.browse(move.product_id.product_tmpl_id.id)
                        categ_id = tmpl_obj.categ_id.id or False
                        var = {'request_id': self.id, 'name': move.name or False, 'product_id': move.product_id.id or False, 'categ_id': categ_id,'move_id': move.id or False,
                           'product_qty': move.product_uom_qty or 0.0,'criterions_id': False,'product_uom': move.product_uom.id or False,'state': 'draft'}
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
                    product_qty = kcs_line.product_qty or 0.0000
                    qty_reached = product_qty - (product_qty * kcs_line.deduction) or 0.0000
                    if qty_reached > product_qty:
                        raise UserError(_('Quantity do not bigger than Init Quantity'))
                    else:
                        kcs_line.move_id.write({'product_uom_qty': qty_reached or 0.0})
                else:
                    kcs_line.move_id.write({'product_uom_qty': 0.0})
                    kcs_line.move_id.action_cancel()
        self.write({'state': 'approved', 'user_approve': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
    
class RequestKCSLine(models.Model):
    _inherit = "request.kcs.line"
    
    @api.model
    def create(self, vals):
        result = super(RequestKCSLine, self).create(vals)
        return result
    
    @api.depends('mc_degree')
    def _percent_mc(self):
        for this in self:
            if this.mc_degree > 0:
                this.mc = (this.mc_degree / (1 + this.mc_degree / 100)) 
            else:
                this.mc = 0.0
            
    @api.depends('mc_degree', 'sample_weight')
    def _mc_deduct(self):
        for this in self:
            if this.mc_degree != 0:
                degree = self.env['degree.mc'].search([('mconkett', '=', this.mc_degree)], limit=1)
#                 if not degree:
#                     raise UserError(_('You much Define Degree mc'))
                this.mc_deduct = degree.deduction * -1
                this.mc_deduct = this.mc_deduct 
            else:
                this.mc_deduct = 0.0
    
    @api.depends('sample_weight','fm_gram')
    def _percent_fm(self):
        for this in self:
            if this.sample_weight != 0:
                this.fm = (this.fm_gram / this.sample_weight or 0.0000)*100
            else:
                this.fm = 0.0
            
    @api.depends('sample_weight','fm_gram')
    def _fm_deduct(self):
        for this in self:
            if this.fm_gram > 0 and this.sample_weight > 0 and this.criterions_id:
                fm_deduct = this.criterions_id.percent_fm - (this.fm_gram / this.sample_weight) or 0.0000
                this.fm_deduct = fm_deduct * 100
            else:
                this.fm_deduct = 0.0
            
    @api.depends('bb_sample_weight','black_gram')
    def _percent_black(self):
        for this in self:
            if this.bb_sample_weight > 0 and this.black_gram > 0:
                black = this.black_gram / this.bb_sample_weight or 0.0000
                this.black = black * 100
            else:
                this.black = 0.0
            
    @api.depends('bb_sample_weight','broken_gram')
    def _percent_broken(self):
        for this in self:
            if this.bb_sample_weight > 0 and this.broken_gram > 0:
                broken = this.broken_gram / this.bb_sample_weight or 0.0000
                this.broken = broken * 100
            else:
                this.broken = 0.0
    
    @api.depends('black','broken','criterions_id')
    def _broken_deduct(self):
        for this in self:
            if this.black > 0 and this.broken > 0 and this.criterions_id:
                broken_deduct = deduct = percent_bb = 0.0000
                percent_bb = self.black + self.broken 
                
                self.env.cr.execute('''SELECT id FROM Broken_Standard WHERE criterion_id = %s ORDER BY range_end desc'''%(this.criterions_id.id))
                for broken_standard in self.env.cr.dictfetchall(): 
                    deduct =0.0
                    broken_obj = self.env['broken.standard'].browse(broken_standard['id'])
                    percent = broken_obj.percent or 0.0
                    if broken_obj.range_start <= percent_bb and  percent_bb <= broken_obj.range_end:
                        deduct = (percent_bb - broken_obj.range_start) * (percent/100)
                        percent_bb = broken_obj.range_start
                    broken_deduct += deduct
                this.broken_deduct = broken_deduct *(-1) 
            else:
                this.broken_deduct = 0.0
            
    @api.depends('bb_sample_weight','brown_gram')
    def _percent_brown(self):
        for this in self:
            if this.bb_sample_weight != 0:
                brown = this.brown_gram / this.bb_sample_weight  or  0.0000
                this.brown = brown * 100
            else:
                this.brown = 0.0
            
    @api.depends('brown','criterions_id')
    def _brown_deduct(self):
        for this in self:
            if this.brown > 0 and this.criterions_id:
                brown_deduct = deduct = percent_brown = 0.000
                percent_brown = this.brown
                
                self.env.cr.execute('''SELECT id FROM brown_standard WHERE criterion_id = %s ORDER BY range_end DESC'''%(self.criterions_id.id))
                for brown_standard in self.env.cr.dictfetchall(): 
                    deduct =0.0
                    brown_obj = self.env['brown.standard'].browse(brown_standard['id'])
                    percent = brown_obj.percent or 0.0
                        
                    if brown_obj.range_start <= percent_brown and percent_brown <= brown_obj.range_end:
                        deduct = (percent_brown - brown_obj.range_start) * (percent/100)
                        percent_brown = brown_obj.range_start
                    brown_deduct += deduct
                    
                this.brown_deduct = brown_deduct *(-1) 
            else:
                this.brown_deduct = 0.0
            
    @api.depends('sample_weight','mold_gram')
    def _percent_mold(self):
        for this in self:
            if this.sample_weight != 0:
                mold = this.mold_gram / this.sample_weight  or 0.0000
                this.mold = mold * 100
            else:
                this.mold = 0.0
            
    @api.depends('mold','criterions_id')
    def _mold_deduct(self):
        for this in self:
            if this.mold and this.criterions_id:
                mold_deduct = 0.0000
                percent_brown = this.mold
                
                self.env.cr.execute('''SELECT id FROM mold_standard WHERE criterion_id = %s ORDER BY range_end DESC'''%(this.criterions_id.id))
                for mold_standard in self.env.cr.dictfetchall():
                    mold_obj = self.env['mold.standard'].browse(mold_standard['id'])
                    deduct =0.0
                        
                    if mold_obj.range_start <= percent_brown and percent_brown <= mold_obj.range_end:
                        deduct = (percent_brown - mold_obj.range_start) * (mold_obj.percent/100 or 0.0)
                        percent_brown = mold_obj.range_start
                    mold_deduct += deduct
                this.mold_deduct = mold_deduct *(-1)
            else:
                this.mold_deduct = 0.0
    
    @api.depends('sample_weight','cherry_gram')
    def _percent_cherry(self):
        for this in self:
            if this.sample_weight > 0 and this.cherry_gram > 0:
                cherry = this.cherry_gram / this.sample_weight  or 0.0000
                this.cherry = cherry * 100
            else:
                this.cherry = 0.0
            
    @api.depends('sample_weight','excelsa_gram')
    def _percent_excelsa(self):
        for this in self:
            if this.sample_weight > 0 and this.excelsa_gram > 0:
                excelsa = this.excelsa_gram / this.sample_weight  or 0.0000
                this.excelsa = excelsa * 100
            else:
                this.excelsa = 0.0
            
    @api.depends('excelsa','criterions_id')
    def _excelsa_deduct(self):
        for this in self:
            if this.excelsa > 0 and this.criterions_id:
                excelsa_deduct = percent_excelsa = standard = percent = 0.0000
                
                percent_excelsa = this.excelsa
                standard = this.criterions_id.standard_excelsa
                percent = this.criterions_id.percent_excelsa
                if percent_excelsa > standard:
                    excelsa_deduct = (percent_excelsa - standard) * percent/100
                this.excelsa_deduct = excelsa_deduct *(-1) 
            else:
                this.excelsa_deduct = 0.0
            
    @api.depends('sample_weight','screen18_gram')
    def _percent_screen18(self):
        for this in self:
            if this.sample_weight != 0:
                screen18 = this.screen18_gram / this.sample_weight or 0.0000
                this.screen18 = screen18 * 100
            else:
                this.screen18 = 0.0
            
    @api.depends('sample_weight','screen16_gram')
    def _percent_screen16(self):
        for this in self:
            if this.sample_weight != 0:
                screen16 = this.screen16_gram / this.sample_weight  or 0.0000
                this.screen16 = screen16 * 100
            else:
                this.screen16 = 0.0
            
    @api.depends('screen18','screen16','criterions_id')
    def _screen16_deduct(self):
        for this in self:
            if this.screen18 > 0 and this.screen16 > 0 and this.criterions_id:
                oversc16 = percent_oversc = standard = percent = 0.0000
    
                percent_oversc = this.screen16 + this.screen18
                standard = this.criterions_id.standard_screen18_16
                percent = this.criterions_id.percent_screen18_16
                if 0 < percent_oversc and  percent_oversc < standard:
                    oversc16 = (standard - percent_oversc) * (percent/100 or 0.0)
                this.oversc16 = oversc16 * (-1) 
            else:
                this.oversc16 = 0
            
    @api.depends('sample_weight','screen13_gram')
    def _percent_screen13(self):
        for this in self:
            if this.sample_weight > 0 and this.screen13_gram > 0:
                screen13 = this.screen13_gram / this.sample_weight or 0.0000
                this.screen13 = screen13 * 100
            else:
                this.screen13 = 0.0
            
    @api.depends('screen18','screen16','screen13','criterions_id')
    def _screen13_deduct(self):
        for this in self:
            if this.screen18 > 0 and this.screen16 > 0 and this.screen13 > 0 and this.criterions_id:
                oversc13 = percent_oversc = standard = percent = 0.0000
                
                percent_oversc = this.screen13 + this.screen16 + this.screen18
                standard = this.criterions_id.standard_screen13
                percent = this.criterions_id.percent_screen13
                
                if 0 < percent_oversc and percent_oversc < standard:
                    oversc13 = (standard - percent_oversc) * (percent/100 or 0.0)
                this.oversc13 = oversc13 * (-1) 
            else:
                this.oversc13 =0.0
            
    @api.depends('sample_weight','belowsc12_gram')
    def _percent_belowsc12(self):
        for this in self:
            if this.sample_weight > 0 and this.belowsc12_gram > 0:
                belowsc12 = this.belowsc12_gram / this.sample_weight or 0.0000
                this.belowsc12 = belowsc12 * 100
            else:
                this.belowsc12 = 0.0
    
    @api.depends('sample_weight','burned_gram')
    def _percent_burned(self):
        for this in self:
            if this.sample_weight > 0 and this.burned_gram > 0:
                burned = this.burned_gram / this.sample_weight or 0.0000
                this.burned = burned * 100
            else:
                this.burned = 0.0
            
    @api.depends('burned','burned_gram','sample_weight')
    def _burned_deduct(self):
        for this in self:
            if this.burned > 0 and this.criterions_id:
                burned_deduct = percent_burned = standard = percent = 0.0000
                
                percent_burned = this.burned 
                standard = this.criterions_id.standard_burned
                percent = this.criterions_id.percent_burned
                
                if standard > 0 and percent_burned > standard:
                    burned_deduct = (percent_burned - standard) * percent/100
                this.burned_deduct = burned_deduct * (-1) 
            else:
                this.burned_deduct = 0.0
            
    @api.depends('sample_weight','eaten_gram')
    def _percent_eaten(self):
        for this in self:
            if this.bb_sample_weight > 0 and this.eaten_gram > 0:
                eaten = this.eaten_gram / this.bb_sample_weight or 0.0000
                this.eaten = eaten * 100
            else:
                this.eaten = 0.0
            
    @api.depends('sample_weight','immature_gram')
    def _percent_immature(self):
        for this in self:
            if this.bb_sample_weight != 0:
                immature = this.immature_gram / this.bb_sample_weight  or 0.0000
                this.immature = immature * 100
            
    @api.depends('sample_weight','bb12_gram')
    def _percent_bb12(self):
        for this in self:
            if this.sample_weight != 0:
                bb12 = this.bb12_gram / this.sample_weight or 0.0000
                this.bb12 = bb12 * 100
            else:
                this.bb12 = 0.0
            
    @api.depends('sample_weight','bb_sample_weight','mc_deduct','fm_deduct','broken_deduct','brown_deduct'
                 ,'mold_deduct','excelsa_deduct','oversc16','oversc13','burned_deduct','deduction_manual')
    def _compute_deduction(self):   
        for line in self:
            product_qty = line.product_qty or 0.0
            if line.picking_id.picking_type_id.deduct:
                if line.deduction_manual:
                    line.deduction = line.deduction_manual
                    
                    line.qty_reached = product_qty * line.deduction_manual/100
                    line.basis_weight = product_qty + product_qty * line.deduction_manual/100
                else:
                    deduction = (line.mc_deduct + line.fm_deduct + line.broken_deduct +
                          line.brown_deduct + line.mold_deduct + line.excelsa_deduct +
                           line.oversc13 + line.oversc16 + line.burned_deduct) or 0.0
                    line.deduction = deduction
                    line.qty_reached = product_qty * deduction/100
                    line.basis_weight = product_qty + product_qty * deduction/100
            else:
                line.qty_reached = product_qty
                line.basis_weight = product_qty
            
            
    sample_weight = fields.Float(string="Sample Weight", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    bb_sample_weight = fields.Float(string="BB Sample Weight", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    
    mc_degree = fields.Float(string="MCDegree", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    mc = fields.Float(compute='_percent_mc', string="MC_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    mc_deduct = fields.Float(compute='_mc_deduct', string="MC Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    fm_gram = fields.Float(string="FM Gram", default=0.0000, digits=(12, 2))
    fm = fields.Float(compute='_percent_fm',string="FM_%", readonly=True, store=True, default=0.0000, digits=(12, 2),group_operator="avg")
    fm_deduct = fields.Float(compute='_fm_deduct', string="FM Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    black_gram = fields.Float(string="Black Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    black = fields.Float(compute='_percent_black',group_operator="avg",string="Black_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    broken_gram = fields.Float(string="Broken Gram", default=0.0000, digits=(12, 2),)
    broken = fields.Float(compute='_percent_broken',group_operator="avg",string="Broken_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    broken_deduct = fields.Float(compute='_broken_deduct', string="BB Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    brown_gram = fields.Float(string="Brown Gram", default=0.0000, digits=(12, 2)) 
    brown = fields.Float(compute='_percent_brown',group_operator="avg",string="Brown_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    brown_deduct = fields.Float(compute='_brown_deduct',string="Brown Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    mold_gram = fields.Float(string="Mold Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    mold = fields.Float(compute='_percent_mold',group_operator="avg",string="Mold_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    mold_deduct = fields.Float(compute='_mold_deduct',string="Mold Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    cherry_gram = fields.Float(string="Cherry Gram", default=0.0000, states={'draft': [('readonly', False)]}, digits=(12, 2))
    cherry = fields.Float(compute='_percent_cherry', group_operator="avg",string="Cherry_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    excelsa_gram = fields.Float(string="Excelsa Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    excelsa = fields.Float(compute='_percent_excelsa', group_operator="avg", string="Excelsa_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    excelsa_deduct = fields.Float(compute='_excelsa_deduct' ,string="Excelsa Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    screen18_gram = fields.Float(string="Screen18 Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    screen18 = fields.Float(compute='_percent_screen18',group_operator="avg", string="Screen18_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    screen16_gram = fields.Float(string="Screen16 Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    screen16 = fields.Float(compute='_percent_screen16',group_operator="avg", string="Screen16 %", readonly=True, store=True, default=0.0000, digits=(12, 2))
    oversc16 = fields.Float(compute='_screen16_deduct',string="OverSc16 Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    screen13_gram = fields.Float(string="Screen13 Gram", default=0.0000, digits=(12, 2),readonly=True, states={'draft': [('readonly', False)]})
    screen13 = fields.Float(compute='_percent_screen13',group_operator="avg", string="Screen13_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    oversc13 = fields.Float(compute='_screen13_deduct',string="OverSc13 Deduct", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    belowsc12_gram = fields.Float(string="Belowsc12 Gram", default=0.000, digits=(12, 2), readonly=True, states={'draft': [('readonly', False)]})
    belowsc12 = fields.Float(compute='_percent_belowsc12',group_operator="avg", string="Belowsc12_%", readonly=True, store=True, default=0.000)
    
    burned_gram = fields.Float(string="Burned Gram", default=0.0000, digits=(12, 2), readonly=True, states={'draft': [('readonly', False)]})
    burned = fields.Float(compute='_percent_burned',group_operator="avg", string="Burned_%", default=0.0000, digits=(12, 2),store=True)
    burned_deduct = fields.Float(compute='_burned_deduct',string="Burned Deduct",  store=True,  digits=(12, 2))
    
    eaten_gram = fields.Float(string="Eaten Gram", default=0.0000, digits=(12, 2), readonly=True, states={'draft': [('readonly', False)]})
    eaten = fields.Float(compute='_percent_eaten',group_operator="avg", string="Eaten_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    immature_gram = fields.Float(string="Immature Gram", default=0.0000, digits=(12, 2), readonly=True, states={'draft': [('readonly', False)]})
    immature = fields.Float(compute='_percent_immature',group_operator="avg", string="Immature_%", readonly=True, store=True, default=0.0000, digits=(12, 2))
    
    maize_yn = fields.Char(string="Maize YN", readonly=True, states={'draft': [('readonly', False)]})
    stone_count = fields.Char(string="Stone Count", readonly=True, states={'draft': [('readonly', False)]})
    stick_count = fields.Char(string="Stick Count", readonly=True, states={'draft': [('readonly', False)]})
    
    bb12_gram = fields.Float(string="BB12 Gram", default=0.0000, digits=(12, 2), readonly=True, states={'draft': [('readonly', False)]})
    bb12 = fields.Float(compute='_percent_bb12', string="BB12_%", default=0.0000, digits=(12, 2), readonly=True, store=True)
    
    deduction = fields.Float(compute='_compute_deduction', string="Deduction %",  store=True,  digits=(12, 2))
    qty_reached = fields.Float(compute='_compute_deduction', string="Deduction Weight", store=True, digits=(12, 0))
    basis_weight = fields.Float(compute='_compute_deduction', string="Basis Weight", store=True, digits=(12, 0))
    deduction_manual = fields.Float(string="Deduction Manual %", digits=(12, 2))
    
    stack_id = fields.Many2one('stock.stack',related='picking_id.stack_id', string="Stack", readonly=True,store=True)
    zone_id = fields.Many2one('stock.zone',related='picking_id.zone_id', string="Zone", readonly=True,store=True)
    partner_id = fields.Many2one('res.partner',related='picking_id.partner_id', string="Partner", readonly=True,store=True)
    date = fields.Date(related='picking_id.date_kcs', string="KCs Date", readonly=True,store=False)
    production_id = fields.Many2one('mrp.production',related='picking_id.production_id', string="Production", readonly=True,store=True)
    picking_type_id = fields.Many2one('stock.picking.type',related='picking_id.picking_type_id', string="Picking Type", readonly=True,store=True)
    picking_type_code = fields.Selection(related='picking_id.picking_type_id.code', 
                    selection=[('incoming', 'Suppliers'), ('outgoing', 'Customers'), ('internal', 'Internal')],string="Picking Type Code", readonly=True,store=True)
    cuptest = fields.Char(String="Cuptest")
    districts_id = fields.Many2one(related='picking_id.districts_id', string="districts", readonly=True,store=False)
    
    contract_no = fields.Char(related='picking_id.contract_no', string="Contract no", readonly=True)
    
    reference = fields.Char(string="Reference")
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d-%m-%Y')
    @api.depends('date')
    def _compute_date(self):
        for line in self:
            line.date_tz = line.date
            line.day_tz = self.get_date(line.date)
            
    date_tz = fields.Date(compute='_compute_date',string = "date", store=True)
    day_tz = fields.Char(compute='_compute_date',string = "Month", store=True)

    