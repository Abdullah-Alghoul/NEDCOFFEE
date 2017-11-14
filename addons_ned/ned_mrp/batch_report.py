# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

DATE_FORMAT = "%Y-%m-%d"

class ProductionAnalysis(models.Model):
    _name = "production.analysis"
    
    #premium_id = fields.Many2one('mrp.bom.premium',string="Premium")
    
    production_id = fields.Many2one('mrp.production',string="Production")
    input_basis_qty = fields.Float(string="Input Basis Qty", related='production_id.product_basis_issued',)
    output_product_received = fields.Float(string="Output Basis Qty", related='production_id.product_received',)
    
    cost_of_purchases = fields.Float(string="Cost of Purchases (FIFO)")
    input_ids = fields.One2many('production.analysis.line.input','analysis_id', string="Inputs")
    output_ids = fields.One2many('production.analysis.line.output','analysis_id', string="Oututs")
    summary_ids = fields.One2many('production.analysis.line','analysis_id',string="Prod. Loss")
    prod_pl = fields.Float(string="Prod. P&L",)
    
    @api.multi
    def export_data(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'production_analysis_report',
                }
    
    @api.multi
    def load_data(self):
        for this in self:
            nvl_net__qty = nvl_basis_qty = 0
            sql ='''
                SELECT  sum(total_init_qty) net_qty,sum(total_qty) basis_qty 
                FROM stock_picking  sp
                    WHERE production_id = %s
                        and picking_type_code in ('production_out')
                        and state ='done'
                    GROUP By picking_type_code,product_id
            '''%(this.production_id.id)
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                nvl_net__qty = i['net_qty'] or 0.0
                nvl_basis_qty = i['basis_qty'] or 0.0
            
            sql ='''
                DELETE FROM production_analysis_line_input;
                DELETE FROM production_analysis_line_output;
                DELETE FROM production_analysis_line;
                
                SELECT  picking_type_code,product_id, sum(total_init_qty) net_qty,sum(total_qty) basis_qty 
                FROM stock_picking  sp
                    WHERE production_id = %s
                        and picking_type_code in ('production_in','production_out')
                        and state ='done'
                    GROUP By picking_type_code,product_id
            '''%(this.production_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                premium = 0
                sql ='''
                    SELECT line.*
                    FROM  mrp_bom_premium  pre join mrp_bom_premium_line line on pre.id = line.prem_id
                    WHERE pre.active = true
                    and line.product_id = %s
                    and id = %s
                    limit 1
                '''%(line['product_id'],this.premium_id.id)
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    premium = j['premium']
                
                bom = 0
                sql ='''
                    SELECT line.*
                    FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                        join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id
                    WHERE bom.id = %s and line.product_id = %s
                '''%(this.production_id.bom_id.id,line['product_id'])
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    bom = j['off_topic']
                
                
                count = 0
                if line['picking_type_code'] != 'production_out':
                    mc = belowsc12 = screen13 = screen16 = screen18 = fm = black = brown = broken = 0.0
                    sql ='''
                        SELECT sp.total_qty npe_qty, qc.*
                        FROM stock_picking  sp join request_kcs_line qc on sp.id = qc.picking_id
                            WHERE sp.production_id = %s
                                and sp.picking_type_code ='%s'
                                and sp.state ='done'
                                and sp.product_id = %s
                    '''%(this.production_id.id,line['picking_type_code'],line['product_id'])
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        mc += i['mc'] * i['npe_qty'] or 0.0
                        fm += i['fm'] * i['npe_qty'] or 0.0
                        black += i['black'] * i['npe_qty'] or 0.0
                        broken += i['broken'] * i['npe_qty'] or 0.0
                        brown +=  i['brown'] * i['npe_qty'] or 0.0
                        screen18 += i['screen18'] * i['npe_qty'] or 0.0
                        screen16 += i['screen16'] * i['npe_qty'] or 0.0
                        screen13 += i['screen13'] * i['npe_qty'] or 0.0
                        belowsc12 += i['belowsc12'] * i['npe_qty'] or 0.0
                        count += i['npe_qty']
                    
                    actual = nvl_basis_qty and line['basis_qty'] / nvl_basis_qty or 0.0
                    var_usd = (this.cost_of_purchases + premium) * (actual - bom) * line['basis_qty'] /1000
                    val ={
                          'analysis_id':this.id,
                          'product_id':line['product_id'],
                          'net_qty':line['net_qty'],
                          'basis_qty':line['basis_qty'],
                          'mc':count and mc/count or 0.0,
                          'fm':count and fm/count or 0.0, 
                          'black':count and black/count or 0.0, 
                          'broken':count and broken/count or 0.0, 
                          'brown':count and brown/count or 0.0, 
                          'screen18':count and screen18/count or 0.0, 
                          'screen16':count and screen16/count or 0.0, 
                          'screen13':count and screen13/count or 0.0, 
                          'screen12':count and belowsc12/count or 0.0, 
                          'actual':actual,
                          'premium':premium,
                          'bom':bom,
                          'var': actual - bom,
                          'var_usd':var_usd
                          }
                    self.env['production.analysis.line.output'].create(val)
                else:
                    mc = belowsc12 = screen13 = screen16 = screen18 = fm = black = brown = broken = 0.0
                    sql ='''
                        SELECT sp.total_qty basis_qty, stack.*
                        FROM stock_picking  sp join stock_stack stack on sp.stack_id = stack.id
                            WHERE sp.production_id = %s
                                and picking_type_code ='%s'
                                and sp.state ='done'
                                and sp.total_qty !=0
                                and sp.product_id = %s
                    '''%(this.production_id.id,line['picking_type_code'],line['product_id'])
                    self.env.cr.execute(sql)
                    for i in self.env.cr.dictfetchall():
                        mc += i['mc'] * i['basis_qty'] or 0.0
                        fm += i['fm'] * i['basis_qty'] or 0.0
                        black += i['black'] * i['basis_qty'] or 0.0
                        broken += i['broken'] * i['basis_qty'] or 0.0
                        brown +=  i['brown'] * i['basis_qty'] or 0.0
                        screen18 += i['screen18'] * i['basis_qty'] or 0.0
                        screen16 += i['screen16'] * i['basis_qty'] or 0.0
                        screen13 += i['screen13'] * i['basis_qty'] or 0.0
                        belowsc12 += i['screen12'] * i['basis_qty'] or 0.0
                        count += i['basis_qty']
                    
                    actual = nvl_basis_qty and line['basis_qty'] / nvl_basis_qty or 0.0
                    var_usd = (this.cost_of_purchases + premium) * (actual - bom) * line['basis_qty'] /1000
                        
                    val ={
                          'analysis_id':this.id,
                          'product_id':line['product_id'],
                          'net_qty':line['net_qty'],
                          'basis_qty':line['basis_qty'],
                          'mc':count and mc/count or 0.0,
                          'fm':count and fm/count or 0.0,
                          'black':count and black/count or 0.0, 
                          'broken':count and broken/count or 0.0, 
                          'brown':count and brown/count or 0.0, 
                          'screen18':count and screen18/count or 0.0, 
                          'screen16':count and screen16/count or 0.0, 
                          'screen13':count and screen13/count or 0.0, 
                          'screen12':count and belowsc12/count or 0.0, 
                          'actual':actual,
                          'premium':premium,
                          'bom':bom,
                          'var': actual - bom,
                          'var_usd':var_usd
                    }
                    analysis = self.env['production.analysis.line.input'].create(val)
            
            this.refresh()
            #Tao summary
            for loop in (1,2,3):
                total = 0.0
                bom = 0
                sql ='''
                    SELECT line.*
                    FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                        join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                    WHERE bom.id = %s and line.product_id = 1175
                '''%(this.production_id.bom_id.id,)
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    #kiet: Code lay Drying loss
                    bom = j['off_topic']
                
                if loop == 1:
                    in_avg_mc = net_qty  =0
                    for input in this.input_ids:
                        in_avg_mc += input.net_qty * input.mc
                        net_qty += input.net_qty
                    #Kiet Bình quân in
                    in_avg_mc = round(in_avg_mc/ net_qty,1)
                    
                    out_avg_mc = net_qty =0
                    for output in this.output_ids:
                        net_qty += output.net_qty
                        out_avg_mc += output.net_qty * output.mc
                    #Kiet: Bình quân Out
                    out_avg_mc = round(out_avg_mc/ net_qty,1)
                    
                    wloss = this.input_basis_qty * (1-((1- in_avg_mc/100)/(1- out_avg_mc/100)))
                    actual = this.input_basis_qty and wloss/ this.input_basis_qty or 0.0
                    vals ={
                    'basis':wloss,
                    'name':   'MC loss',
                    'bom':bom,
                    'analysis_id':this.id,
                    'actual':actual or 0.0,
                    'var':(actual - bom) or 0.0
                    }
                    self.env['production.analysis.line'].create(vals)
                    total += wloss
                
                if loop == 2:
                    sql ='''
                        SELECT  pp.id product_id, pp.default_code, sum(total_qty) basis_qty 
                            FROM stock_picking  sp join product_product pp on sp.product_id = pp.id
                                join product_template pt on pp.product_tmpl_id = pt.id
                                join product_category pc on pt.categ_id = pc.id
                                WHERE production_id = %s
                                    and picking_type_code in ('production_in')
                                    and sp.state ='done'
                                    and pc.code in ('Reject')
                                GROUP By pp.id,pp.default_code
                        '''%(this.production_id.id)
                    self.env.cr.execute(sql)
                    for k in self.env.cr.dictfetchall():
                        bom = 0
                        sql ='''
                            SELECT line.off_topic
                            FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                                join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                            WHERE bom.id = %s and line.product_id = %s
                            LIMIT 1
                        '''%(this.production_id.bom_id.id,k['product_id'])
                        self.env.cr.execute(sql)
                        for j in self.env.cr.dictfetchall():
                            #kiet: Code lay Drying loss
                            bom = j['off_topic']
                        
                        actual = this.input_basis_qty and k['basis_qty']/ this.input_basis_qty or 0.0
                            
                        premium = 0
                        vals ={
                        'name':   k['default_code'],
                        'bom':bom,
                        'basis':k['basis_qty'],
                        'actual':actual,
                        'var':(actual - bom) or 0.0,
                        'analysis_id':this.id
                        }
                        self.env['production.analysis.line'].create(vals)
                        total += k['basis_qty']
                
                if loop == 3:
                    bom = 0
                    sql ='''
                        SELECT line.*
                        FROM mrp_bom bom join mrp_bom_stage_line stage on bom.id = stage.bom_id
                            join mrp_bom_stage_output_line line on stage.id = line.bom_stage_line_id 
                        WHERE bom.id = %s and line.product_id = 1373
                    '''%(this.production_id.bom_id.id)
                    self.env.cr.execute(sql)
                    for j in self.env.cr.dictfetchall():
                        #kiet: Code lay Drying loss
                        bom = j['off_topic']
                    
                    basis = this.input_basis_qty - this.output_product_received - total
                    actual = this.input_basis_qty and basis/ this.input_basis_qty or 0.0
                    
                    vals ={
                    'name':   'Invisible loss',
                    'bom':bom,
                    'basis':basis,
                    'analysis_id':this.id,
                    'actual':actual or 0.0,
                    'var':(actual - bom) or 0.0
                    }
                    self.env['production.analysis.line'].create(vals)
                    
            return

class ProductionAnalysisLine(models.Model):
    _name = "production.analysis.line"
    
    name = fields.Char(' ')
    bom = fields.Float(' ')
    basis = fields.Float(' ')
    actual = fields.Float(' ')
    var = fields.Float(' ')
    analysis_id = fields.Many2one('production.analysis',string="Report")
    
    

class ProductionAnalysisLineInput(models.Model):
    _name = "production.analysis.line.input"
    _order = 'categ_code, id desc'
    
    analysis_id = fields.Many2one('production.analysis',string="Report")
    categ_code = fields.Char(related='product_id.categ_id.code',string="Category",store=True)
    product_id = fields.Many2one('product.product',string="Product")
    net_qty = fields.Float( string ="Net Qty",digits=(12, 0))
    basis_qty = fields.Float(string ="Basis Qty",digits=(12, 0))
    mc = fields.Float(group_operator="avg",store=True)
    fm = fields.Float(group_operator="avg",store=True)
    black = fields.Float(group_operator="avg",store=True)
    broken = fields.Float(group_operator="avg",store=True)
    brown = fields.Float(group_operator="avg",store=True)
    screen18 = fields.Float(string =">18%" ,group_operator="avg",store=True)
    screen16 = fields.Float(string =">16%" ,group_operator="avg",store=True)
    screen13 = fields.Float(string =">13%" ,group_operator="avg",store=True)
    screen12 = fields.Float(string ="<12%",group_operator="avg",store=True)
    
    premium = fields.Float(string ="Premium",digits=(12, 0) )
    bom = fields.Float(string ="BOM %",digits=(12, 0) )
    actual = fields.Float(string ="Actual - %",digits=(12, 4) )
    var = fields.Float(string ="Var. %",digits=(12, 2) )
    var_usd = fields.Float(string ="Var. US$",digits=(12, 2) )
    
    
class ProductionAnalysisLineOutput(models.Model):
    _name = "production.analysis.line.output"
    _order = 'categ_code, id desc'
    
    
    analysis_id = fields.Many2one('production.analysis',string="Report")
    
    categ_code = fields.Char(related='product_id.categ_id.code',string="Category",store=True)
    product_id = fields.Many2one('product.product',string="Product")
    net_qty = fields.Float( string ="Net Qty",digits=(12, 0))
    basis_qty = fields.Float(string ="Basis Qty",digits=(12, 0))
    mc = fields.Float(group_operator="avg",store=True)
    fm = fields.Float(group_operator="avg",store=True)
    black = fields.Float(group_operator="avg",store=True)
    broken = fields.Float(group_operator="avg",store=True)
    brown = fields.Float(group_operator="avg",store=True)
    screen18 = fields.Float(string =">18%" ,group_operator="avg",store=True)
    screen16 = fields.Float(string =">16%" ,group_operator="avg",store=True)
    screen13 = fields.Float(string =">13%" ,group_operator="avg",store=True)
    screen12 = fields.Float(string ="<12%",group_operator="avg",store=True)
    premium = fields.Float(string ="Premium",digits=(12, 2) )
    bom = fields.Float(string ="BOM %",digits=(12, 2) )
    actual = fields.Float(string ="Actual - %",digits=(12, 4) )
    var = fields.Float(string ="Var. %",digits=(12, 4) )
    var_usd = fields.Float(string ="Var. US$",digits=(12, 2) )
    

class BatchReport(models.Model):
    _name = "batch.report"
    
    production_id = fields.Many2one('mrp.production',string="Production")
    input_ids = fields.One2many('batch.report.input','batch_id',string="Inputs")
    outputs_ids = fields.One2many('batch.report.output','batch_id',string="OutPus")
    stack_id = fields.Many2one('stock.stack',string="Stack")
    product_id = fields.Many2one('product.product',string="Product")
    
    @api.multi
    def export_data(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'batch_reprot',
                }
    @api.multi
    def load_data(self):
        for this in self:
            if this.stack_id:
                sql ='''
                    DELETE FROM batch_report_input where batch_id = %s ;
                    DELETE FROM batch_report_output where batch_id = %s ;
                    SELECT  picking_type_code,id,stack_id from stock_picking 
                        WHERE production_id = %s and stack_id = %s
                            and picking_type_code in ('production_in','production_out')
                            and total_qty !=0
                            and state ='done'
                '''%(this.id,this.id, this.production_id.id,this.stack_id.id)
                self.env.cr.execute(sql)
            elif this.product_id:
                sql ='''
                    DELETE FROM batch_report_input where batch_id = %s ;
                    DELETE FROM batch_report_output where batch_id = %s ;
                    SELECT  picking_type_code,id,stack_id from stock_picking 
                        WHERE production_id = %s and product_id = %s
                            and picking_type_code in ('production_in','production_out')
                            and total_qty !=0
                            and state ='done'
                '''%(this.id,this.id, this.production_id.id,this.product_id.id)
                self.env.cr.execute(sql)
            else:
                sql ='''
                    DELETE FROM batch_report_input where batch_id = %s ;
                    DELETE FROM batch_report_output where batch_id = %s ;
                    SELECT  picking_type_code,id,stack_id from stock_picking 
                        WHERE production_id = %s
                            and picking_type_code in ('production_in','production_out')
                            and total_qty !=0
                            and state ='done'
                '''%(this.id,this.id, this.production_id.id)
                self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                
                val ={
                      'stack_id':line['stack_id'],
                      'picking_id':line['id'],
                      'batch_id':this.id
                      }
                if line['picking_type_code'] =='production_out':
                    self.env['batch.report.input'].create(val)
                else:
                    self.env['batch.report.output'].create(val)
            return

class BatchReportInput(models.Model):
    _name = "batch.report.input"
    
    stack_id = fields.Many2one('stock.stack',string="Stack No.")
    picking_id = fields.Many2one('stock.picking',string="Gip")
    net_qty = fields.Float(related='picking_id.total_init_qty', string ="Net Qty")
    basis_qty = fields.Float(related='picking_id.total_qty', string ="Basis Qty")
    product_id = fields.Many2one('product.product',string="Product.",related='stack_id.product_id')
    mc = fields.Float(related='stack_id.mc',group_operator="avg",store=True)
    fm = fields.Float(related='stack_id.fm',group_operator="avg",store=True)
    black = fields.Float(related='stack_id.black',group_operator="avg",store=True)
    broken = fields.Float(related='stack_id.broken',group_operator="avg",store=True)
    brown = fields.Float(related='stack_id.brown',group_operator="avg",store=True)
    mold = fields.Float(related='stack_id.mold' ,group_operator="avg",store=True)
    cherry = fields.Float(related='stack_id.cherry' ,group_operator="avg",store=True)
    screen18 = fields.Float(related='stack_id.screen18', string =">18%" ,group_operator="avg",store=True)
    screen16 = fields.Float(related='stack_id.screen16',string =">16%" ,group_operator="avg",store=True)
    screen13 = fields.Float(related='stack_id.screen13',string =">13%" ,group_operator="avg",store=True)
    screen12 = fields.Float(related='stack_id.screen12',string ="<12%",group_operator="avg",store=True)
    batch_id = fields.Many2one('batch.report',string="Inputs")

class BatchReportOutput(models.Model):
    _name = "batch.report.output"
    
    stack_id = fields.Many2one('stock.stack',string="Stack No.")
    picking_id = fields.Many2one('stock.picking',string="Gip")
    net_qty = fields.Float(related='picking_id.total_init_qty', string ="Net Qty")
    basis_qty = fields.Float(related='picking_id.total_qty', string ="Basis Qty")
    product_id = fields.Many2one('product.product',string="Product.",related='stack_id.product_id')
    mc = fields.Float(related='stack_id.mc',group_operator="avg",store=True)
    fm = fields.Float(related='stack_id.fm',group_operator="avg",store=True)
    black = fields.Float(related='stack_id.black',group_operator="avg",store=True)
    broken = fields.Float(related='stack_id.broken',group_operator="avg",store=True)
    brown = fields.Float(related='stack_id.brown',group_operator="avg",store=True)
    mold = fields.Float(related='stack_id.mold' ,group_operator="avg",store=True)
    cherry = fields.Float(related='stack_id.cherry' ,group_operator="avg",store=True)
    screen18 = fields.Float(related='stack_id.screen18', string =">18%" ,group_operator="avg",store=True)
    screen16 = fields.Float(related='stack_id.screen16',string =">16%" ,group_operator="avg",store=True)
    screen13 = fields.Float(related='stack_id.screen13',string =">13%" ,group_operator="avg",store=True)
    screen12 = fields.Float(related='stack_id.screen12',string ="<12%",group_operator="avg",store=True)
    batch_id = fields.Many2one('batch.report',string="Output")
    
    
    
    
    