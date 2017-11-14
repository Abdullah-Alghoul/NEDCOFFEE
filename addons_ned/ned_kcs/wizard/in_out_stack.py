

# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning


class wizradInOutStack(models.TransientModel):
    _name = "wizard.in.out.stack"
    
    stack_id = fields.Many2one('stock.stack',string="Stack")
    date  = fields.Date(string="Date")
    zone_id = fields.Many2one('stock.zone',string="Zone")
    qty_stack = fields.Float(string="Stack")
    

    stack_ids = fields.Many2many('stock.stack', string='Stack',)
#     detail_stack = fields.M
    
    @api.model
    def default_get(self, fields):
        res = {}
             
        active_ids = self._context.get('active_ids')
#         stack_ids = self.env['stock.stack'].search(active_ids)
        res.update({'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
                   'stack_ids':active_ids})
        return res
    
    @api.multi
    def merg_stack(self):
        stack_id = False
        this = self
        company = self.env.user.company_id.id or False
        warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'DF')], limit=1)
        init_qty = product_qty = 0
        stick_count = stone_count = mc = immature = eaten = burn = screen12 = screen13 = screen16 = screen18 = excelsa = 0
        cherry = mold = fm = black = brown = broken = 0.0
        count =0
        for line in self.stack_ids:
            stack_id = line
            init_qty += line.init_qty
            product_qty += line.remaining_qty
            mc += line.mc * line.init_qty or 0.0
            fm += line.fm * line.init_qty or 0.0
            black += line.black * line.init_qty or 0.0
            broken += line.broken * line.init_qty or 0.0
            brown +=  line.brown * line.init_qty or 0.0
            mold += line.mold * line.init_qty or 0.0
            cherry += line.cherry * line.init_qty or 0.0
            excelsa += line.excelsa * line.init_qty or 0.0
            screen18 += line.screen18 * line.init_qty or 0.0
            screen16 += line.screen16 * line.init_qty or 0.0
            screen13 += line.screen13 * line.init_qty or 0.0
            screen12 += line.screen12 * line.init_qty or 0.0
            burn += line.burn * line.init_qty or 0.0
            eaten += line.eaten * line.init_qty or 0.0
            immature += line.immature * line.init_qty or 0.0
            stick_count = line.stick_count 
            stone_count = line.stone_count 
            maize_yn = line.maize
            count += line.init_qty
            
            
            
            
            var = {
               'name': '/', 
               'picking_type_id': picking_type_id.id, 
               'min_date': this.date, 
               'date_done':this.date, 
               'partner_id': False, 
               'picking_type_code': picking_type_id.code or False,
               'location_id': picking_type_id.default_location_src_id.id or False, 
               'location_dest_id': picking_type_id.default_location_dest_id.id or False,
               'state':'draft',
               }  
            
            new_id = self.env['stock.picking'].create(var)
            name = line.name
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': line.product_id.uom_id.id or False,
                'product_uom_qty': line.remaining_qty or 0.0, 
                'init_qty': line.init_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': picking_type_id.id or False,
                'location_id': picking_type_id.default_location_src_id.id or False,
                'date_expected': this.date or False, 'partner_id': False,
                'location_dest_id': picking_type_id.default_location_dest_id.id or False,
                'type': picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': line.zone_id.id or False, 
                'product_id': line.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'state':'done', 
                'warehouse_id': warehouse_id.id or False,
                'stack_id':line.id,
                'state_kcs': 'approved'
                })
            
            new_id.action_done()
            
        var = {
           'name': '/', 
           'picking_type_id': picking_type_id.id, 
           'min_date': this.date, 
           'date_done':this.date, 
           'partner_id': False, 
           'picking_type_code': picking_type_id.code or False,
           'location_dest_id': picking_type_id.default_location_src_id.id or False, 
           'location_id': picking_type_id.default_location_dest_id.id or False,
           'state':'draft',
           'state_kcs': 'approved',
       }  
            
        new_id = self.env['stock.picking'].create(var)
        
        var = {
                'zone_id':this.zone_id.id,
                'hopper': False,
                'date':this.date,
                'name':False,
              }
        new_stack = self.env['stock.stack'].create(var)
        
        move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
            'name': name, 
            'product_uom': stack_id.product_id.uom_id.id or False,
            'product_uom_qty': product_qty or 0.0, 
            'init_qty': init_qty or 0.0, 
            'price_unit': 0.0,
            'picking_type_id': picking_type_id.id or False,
            'location_dest_id': picking_type_id.default_location_src_id.id or False,
            'date_expected': this.date or False, 'partner_id': False,
            'location_id': picking_type_id.default_location_dest_id.id or False,
            'type': picking_type_id.code or False, 'scrapped': False, 
            'company_id': company, 
            'zone_id': this.zone_id.id or False, 
            'product_id': stack_id.product_id.id or False,
            'date': self.date or False, 'currency_id': False,
            'warehouse_id': warehouse_id.id or False,
            'stack_id':new_stack.id,
            })
        
        var = {'picking_id': new_id.id, 
                'name': name or False,
                'product_id': stack_id.product_id.id or False, 
                'categ_id': stack_id.product_id.product_tmpl_id.categ_id.id,  
                'product_qty': init_qty or 0.0,
                'qty_reached': init_qty or 0.0,
                'criterions_id': False,  
                'product_uom': stack_id.product_id.uom_id.id or False,
                'move_id': move_id.id or False,
                'state': 'draft',
        }
        
        request = self.env['request.kcs.line'].create(var)
        new_id.action_done()
        request.write({
            'mc':mc/count,
            'fm':fm/count,
            'black':black/count,
            'broken':broken/count,
            'brown':brown/count,
            'mold':mold/count,
            'cherry':cherry/count,
            'excelsa':excelsa/count,
            'screen18':screen18/count,
            'screen16':screen16/count,
            'screen13':screen13/count,
            'belowsc12':screen12/count,
            'burned':burn/count,
            'eaten':eaten/count,
            'immature':immature/count,
            'stick_count':stick_count,
            'stone_count':stone_count,
            'maize_yn':maize_yn,
        })
        new_stack._compute_qc()    
            
            
            
    
    @api.multi
    def stack(self):
        stack_id = False
        for line in self.stack_ids:
            stack_id = line
        for this in self:
#             if this.product_qty > this.qty_stack -this.basis_qty:
#                 raise UserError(u'Request Qty is over')
            
            company = self.env.user.company_id.id or False
            
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            picking_type_id = self.env['stock.picking.type'].search([('name', '=', 'DF')], limit=1)
            
            var = {
                   'name': '/', 
                   'picking_type_id': picking_type_id.id, 
                   'min_date': this.date, 
                   'date_done':this.date, 
                   'partner_id': False, 
                   'picking_type_code': picking_type_id.code or False,
                   'location_id': picking_type_id.default_location_src_id.id or False, 
                   'location_dest_id': picking_type_id.default_location_dest_id.id or False,
                   'state':'draft',
               }  
            
            new_id = self.env['stock.picking'].create(var)
            product_uom_qty = this.qty_stack
                
            name = stack_id.name
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': stack_id.product_id.uom_id.id or False,
                'product_uom_qty': product_uom_qty or 0.0, 
                'init_qty': product_uom_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': picking_type_id.id or False,
                'location_id': picking_type_id.default_location_src_id.id or False,
                'date_expected': this.date or False, 'partner_id': False,
                'location_dest_id': picking_type_id.default_location_dest_id.id or False,
                'type': picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': stack_id.zone_id.id or False, 
                'product_id': stack_id.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'state':'done', 
                'warehouse_id': warehouse_id.id or False,
                'stack_id':stack_id.id,
                'state_kcs': 'approved'
                })
            
            
            var = {'picking_id': new_id.id, 
                    'name': name or False,
                    'product_id': stack_id.product_id.id or False, 
                    'categ_id': stack_id.product_id.product_tmpl_id.categ_id.id,  
                    'product_qty': product_uom_qty or 0.0,
                    'qty_reached': product_uom_qty or 0.0,
                    'criterions_id': False,  
                    'product_uom': stack_id.product_id.uom_id.id or False,
                    'move_id': move_id.id or False,
                    'state': 'draft',
                    
                    }
            request = self.env['request.kcs.line'].create(var)
            new_id.action_done()
            request.write({
                   'mc':stack_id.mc,
                    'fm':stack_id.fm,
                    'black':stack_id.black,
                    'broken':stack_id.broken,
                    'brown':stack_id.brown,
                    'mold':stack_id.mold,
                    'cherry':stack_id.cherry,
                    'excelsa':stack_id.excelsa,
                    'screen18':stack_id.screen18,
                    'screen16':stack_id.screen16,
                    'screen13':stack_id.screen13,
                    'belowsc12':stack_id.screen12,
                    'burned':stack_id.burn,
                    'eaten':stack_id.eaten,
                    'immature':stack_id.immature,
                    'stick_count':stack_id.stick_count,
                    'stone_count':stack_id.stone_count,
                    'maize_yn':stack_id.maize,
                    'stick_count':stack_id.stick_count
            })
            
            #Kiet tap stack nhap
            
            
            var = {
                   'name': '/', 
                   'picking_type_id': picking_type_id.id, 
                   'min_date': this.date, 
                   'date_done':this.date, 
                   'partner_id': False, 
                   'picking_type_code': picking_type_id.code or False,
                   'location_dest_id': picking_type_id.default_location_src_id.id or False, 
                   'location_id': picking_type_id.default_location_dest_id.id or False,
                   'state':'draft',
                   'state_kcs': 'approved',
               }  
            
            new_id = self.env['stock.picking'].create(var)
            
            var = {
                    'zone_id':this.zone_id.id,
                    'hopper': False,
                    'date':this.date,
                    'name':False,
                  }
            new_stack = self.env['stock.stack'].create(var)
            
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': stack_id.product_id.uom_id.id or False,
                'product_uom_qty': product_uom_qty or 0.0, 
                'init_qty': product_uom_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': picking_type_id.id or False,
                'location_dest_id': picking_type_id.default_location_src_id.id or False,
                'date_expected': this.date or False, 'partner_id': False,
                'location_id': picking_type_id.default_location_dest_id.id or False,
                'type': picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': this.zone_id.id or False, 
                'product_id': stack_id.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'warehouse_id': warehouse_id.id or False,
                'stack_id':new_stack.id,
                })
            
            var = {'picking_id': new_id.id, 
                    'name': name or False,
                    'product_id': stack_id.product_id.id or False, 
                    'categ_id': stack_id.product_id.product_tmpl_id.categ_id.id,  
                    'product_qty': product_uom_qty or 0.0,
                    'qty_reached': product_uom_qty or 0.0,
                    'criterions_id': False,  
                    'product_uom': stack_id.product_id.uom_id.id or False,
                    'move_id': move_id.id or False,
                    'state': 'draft',
            }
            
            request = self.env['request.kcs.line'].create(var)
            new_id.action_done()
            request.write({
                'mc':stack_id.mc,
                'fm':stack_id.fm,
                'black':stack_id.black,
                'broken':stack_id.broken,
                'brown':stack_id.brown,
                'mold':stack_id.mold,
                'cherry':stack_id.cherry,
                'excelsa':stack_id.excelsa,
                'screen18':stack_id.screen18,
                'screen16':stack_id.screen16,
                'screen13':stack_id.screen13,
                'belowsc12':stack_id.screen12,
                'burned':stack_id.burn,
                'eaten':stack_id.eaten,
                'immature':stack_id.immature,
                'stick_count':stack_id.stick_count,
                'stone_count':stack_id.stone_count,
                'maize_yn':stack_id.maize,
                'stick_count':stack_id.stick_count
            })
            new_stack._compute_qc()
    
    
    
    
    