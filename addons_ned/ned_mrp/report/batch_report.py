# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp import SUPERUSER_ID

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_total_inputs':self.get_total_inputs,
            'get_total_outputs':self.get_total_outputs,
            'get_analysis_input_total_outputs':self.get_analysis_input_total_outputs,
            'get_analysis_output_total_outputs':self.get_analysis_output_total_outputs,
            'get_analysis_loss_total_outputs':self.get_analysis_loss_total_outputs,
            'get_ned_crop':self.get_ned_crop
        })
        
    def get_ned_crop(self):
        sql ='''
            SELECT name FROM ned_crop where state ='current' limit 1
        '''
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return i['name'] or ''
        return ''
    
    def get_analysis_loss_total_outputs(self,o):
        basis = actual = var_usd = var =bom = 0
        val =[]
        for input in o.summary_ids:
            basis += input.basis or 0.0
            bom += input.bom
            var += input.var
            actual += input.actual
        
        val.append({
              'basis':basis,
              'bom':bom,
              'var':var,
              'var_usd':var_usd,
              'actual':actual
            })
        return val
    
    def get_analysis_output_total_outputs(self,o):
        val =[]
        belowsc12= screen13 = screen16 = screen18 = brown = broken = black = fm = mc = 0
        actual = var_usd = var =bom = basis = count = 0
        for input in o.output_ids:
            mc += input.mc * input.net_qty
            fm += input.fm * input.net_qty or 0.0
            black += input.black * input.net_qty  or 0.0
            broken += input.broken * input.net_qty or 0.0
            brown +=  input.brown * input.net_qty or 0.0
            screen18 += input.screen18 * input.net_qty or 0.0
            screen16 += input.screen16 * input.net_qty or 0.0
            screen13 += input.screen13 * input.net_qty or 0.0
            belowsc12 += input.screen12 * input.net_qty or 0.0
            count += input.net_qty or 0.0
            basis += input.basis_qty or 0.0
            bom += input.bom
            var += input.var
            var_usd += input.var_usd
            actual += input.actual
        
        val.append({
              'net_qty': count,
              'basis':basis,
              'deduction': (1- basis/count)*100,
              'mc':count and mc/count or 0.0,
              'fm':count and fm/count or 0.0, 
              'black':count and black/count or 0.0, 
              'broken':count and broken/count or 0.0, 
              'brown':count and brown/count or 0.0, 
              'screen18':count and screen18/count or 0.0, 
              'screen16':count and screen16/count or 0.0, 
              'screen13':count and screen13/count or 0.0, 
              'screen12':count and belowsc12/count or 0.0, 
              'bom':bom,
              'var':var,
              'var_usd':var_usd,
              'actual':actual
            })
        return val
    
    def get_analysis_input_total_outputs(self,o):
        val =[]
        belowsc12= screen13 = screen16 = screen18 = brown = broken = black = fm = mc = 0
        bom = basis = count = 0
        
        for input in o.input_ids:
            mc += input.mc * input.net_qty
            fm += input.fm * input.net_qty or 0.0
            black += input.black * input.net_qty  or 0.0
            broken += input.broken * input.net_qty or 0.0
            brown +=  input.brown * input.net_qty or 0.0
            screen18 += input.screen18 * input.net_qty or 0.0
            screen16 += input.screen16 * input.net_qty or 0.0
            screen13 += input.screen13 * input.net_qty or 0.0
            belowsc12 += input.screen12 * input.net_qty or 0.0
            count += input.net_qty or 0.0
            basis += input.basis_qty or 0.0
            bom += input.bom
        
        val.append({
              'net_qty': count,
              'basis':basis,
              'deduction': (1- basis/count)*100,
              'mc':count and mc/count or 0.0,
              'fm':count and fm/count or 0.0, 
              'black':count and black/count or 0.0, 
              'broken':count and broken/count or 0.0, 
              'brown':count and brown/count or 0.0, 
              'screen18':count and screen18/count or 0.0, 
              'screen16':count and screen16/count or 0.0, 
              'screen13':count and screen13/count or 0.0, 
              'screen12':count and belowsc12/count or 0.0, 
              'bom':bom
            })
        return val

    def get_total_outputs(self,obj):
        cherry = mold = belowsc12= screen13 = screen16 = screen18 = brown = broken = black = fm = mc = 0
        basis = count = 0
        val=[]
        for input in obj.outputs_ids:
            mc += input.mc * input.net_qty
            fm += input.fm * input.net_qty or 0.0
            black += input.black * input.net_qty  or 0.0
            broken += input.broken * input.net_qty or 0.0
            brown +=  input.brown * input.net_qty or 0.0
            screen18 += input.screen18 * input.net_qty or 0.0
            screen16 += input.screen16 * input.net_qty or 0.0
            screen13 += input.screen13 * input.net_qty or 0.0
            belowsc12 += input.screen12 * input.net_qty or 0.0
            cherry += input.cherry * input.net_qty or 0.0
            mold += input.mold * input.net_qty or 0.0
            count += input.net_qty or 0.0
            basis += input.basis_qty or 0.0
            
        val.append({  
              'net_qty': count,
              'basis':basis,
              'deduction': (1- basis/count)*100,
              'mc':count and mc/count or 0.0,
              'fm':count and fm/count or 0.0, 
              'black':count and black/count or 0.0, 
              'broken':count and broken/count or 0.0, 
              'brown':count and brown/count or 0.0, 
              'screen18':count and screen18/count or 0.0, 
              'screen16':count and screen16/count or 0.0, 
              'screen13':count and screen13/count or 0.0, 
              'screen12':count and belowsc12/count or 0.0, 
              'mold':count and mold/count or 0.0, 
              'cherry':count and cherry/count or 0.0, 
              })
        return val
    
    
    def get_total_inputs(self,obj):
        cherry = mold = belowsc12= screen13 = screen16 = screen18 = brown = broken = black = fm = mc = 0
        basis = count = 0
        val=[]
        for input in obj.input_ids:
            mc += input.mc * input.net_qty
            fm += input.fm * input.net_qty or 0.0
            black += input.black * input.net_qty  or 0.0
            broken += input.broken * input.net_qty or 0.0
            brown +=  input.brown * input.net_qty or 0.0
            screen18 += input.screen18 * input.net_qty or 0.0
            screen16 += input.screen16 * input.net_qty or 0.0
            screen13 += input.screen13 * input.net_qty or 0.0
            belowsc12 += input.screen12 * input.net_qty or 0.0
            cherry += input.cherry * input.net_qty or 0.0
            mold += input.mold * input.net_qty or 0.0
            count += input.net_qty or 0.0
            basis += input.basis_qty or 0.0
        val.append({
              'net_qty': count,
              'basis':basis,
              'deduction': (1- basis/count) * 100,
              'mc':count and mc/count or 0.0,
              'fm':count and fm/count or 0.0, 
              'black':count and black/count or 0.0, 
              'broken':count and broken/count or 0.0, 
              'brown':count and brown/count or 0.0, 
              'screen18':count and screen18/count or 0.0, 
              'screen16':count and screen16/count or 0.0, 
              'screen13':count and screen13/count or 0.0, 
              'screen12':count and belowsc12/count or 0.0, 
              'mold':count and mold/count or 0.0, 
              'cherry':count and cherry/count or 0.0, 
              })
        return val