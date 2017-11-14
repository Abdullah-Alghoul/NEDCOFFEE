# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from dateutil.relativedelta import relativedelta

DATE_FORMAT = "%Y-%m-%d"

class LongShortReport(models.Model):
    _name = "long.short.report"
    
    
    from_date = fields.Date(string="Date start")
    to_date = fields.Date(string="Date End")
    
    crop_id = fields.Many2one('ned.crop',string='Crop')
    long_ids = fields.One2many('long.short.line.report','line_id',string="Line")
    
    
    def get_date(self, date):
        date = datetime.strptime(date, DATE_FORMAT)
        from_date = date.strftime('%Y-%m') +'-01'
        to_date= datetime.strptime(from_date, DATE_FORMAT) + relativedelta(months=1)
        to_date = to_date.strftime('%Y-%m-%d')
        to_date =  datetime.strptime(to_date, DATE_FORMAT) + relativedelta(days=-1)
        to_date = to_date.strftime('%Y-%m-%d')
        return from_date,to_date
    
    @api.multi
    def load_data(self):
        for this in self:
            date = time.strftime(DATE_FORMAT)
            from_date,to_date  = self.get_date(date)
            
            from_date1 =  datetime.strptime(to_date, DATE_FORMAT) + relativedelta(days=+1)
            from_date1 = from_date1.strftime('%Y-%m-%d') #datetime.strptime(from_date1, DATE_FORMAT)
            from_date1,to_date1  = self.get_date(from_date1)
            
            
            from_date2 =  datetime.strptime(to_date1, DATE_FORMAT) + relativedelta(days=+1)
            from_date2 = from_date2.strftime('%Y-%m-%d')
            from_date2,to_date2  = self.get_date(from_date2)
            
            
            from_date3 =  datetime.strptime(to_date2, DATE_FORMAT) + relativedelta(days=+1)
            from_date3 = from_date3.strftime('%Y-%m-%d')
            from_date3,to_date3  = self.get_date(from_date3)
            
            from_date4 =  datetime.strptime(to_date3, DATE_FORMAT) + relativedelta(days=+1)
            from_date4 = from_date4.strftime('%Y-%m-%d')
            from_date4,to_date4  = self.get_date(from_date4)
            
            from_date5 =  datetime.strptime(to_date4, DATE_FORMAT) + relativedelta(days=+1)
            from_date5 = from_date5.strftime('%Y-%m-%d')
            from_date5,to_date5  = self.get_date(from_date5)
            
            from_date6 =  datetime.strptime(to_date5, DATE_FORMAT) + relativedelta(days=+1)
            from_date6 = from_date6.strftime('%Y-%m-%d')
            from_date6,to_date6  = self.get_date(from_date6)
            
            
            sql ='''
                DELETE FROM long_short_line_report;
                    
                SELECT x.*
                        
                    FROM
                    (
                        SELECT pp.id product_id, sum(remaining_qty) sitting_stock 
                        FROM stock_stack ss join product_product pp on ss.product_id = pp.id 
                        WHERE remaining_qty !=0
                        GROUP BY pp.default_code,pp.id
                        ORDER BY pp.default_code) x
                      
                '''%({
                      'from_date': from_date,
                      'to_date': to_date,
                      'from_date1': from_date1,
                      'to_date1': to_date1,
                      'from_date2': from_date2,
                      'to_date2': to_date2,
                      'from_date3': from_date3,
                      'to_date3': to_date3,
                      'from_date4': from_date4,
                      'to_date4': to_date4,
                      'from_date5': from_date5,
                      'to_date5': to_date5,
                      'from_date6': from_date6,
                      'to_date6': to_date6,
                      })
            print sql
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                sitting_stock = i['sitting_stock'] or 0.0
                sales_unshipped = sales_unshipped1= sales_unshipped2 =sales_unshipped3= sales_unshipped4= sales_unshipped5= sales_unshipped6= to_receive = qty_unfixed =0
                npe_ids =[]
                sql ='''
                    SELECT id from purchase_contract where type !='purchase'
                    and date_order >='2016-09-01'
                    and product_id = %s
                '''%(i['product_id'])
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    npe_ids.append(j['id'])
                for npe in self.env['purchase.contract'].browse(npe_ids):
                    qty_unfixed += npe.qty_unfixed
                
                npe_ids =[]
                sql ='''
                    SELECT id from purchase_contract where type ='purchase'
                    and product_id = %s
                '''%(i['product_id'])
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    npe_ids.append(j['id'])
                for npe in self.env['purchase.contract'].browse(npe_ids):
                    to_receive += npe.qty_unreceived
                
                sql ='''
                    SELECT  sum(sale_unshipped) sales_unshipped, sum(sale_unshipped1) sales_unshipped1 ,
                    sum(sale_unshipped2) sales_unshipped2,sum(sale_unshipped3) sales_unshipped3,
                    sum(sale_unshipped4) sales_unshipped4,sum(sale_unshipped5) sales_unshipped5,
                    sum(sale_unshipped6) sales_unshipped6
                    FROM 
                    (
                        SELECT sum(sales_unshipped) sale_unshipped, 0 sale_unshipped1,0 sale_unshipped2,0 sale_unshipped3,0 sale_unshipped4,
                                0 sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date <= '%(to_date)s'
                                and ship_by = 'Factory'
                        union all     
                        SELECT 0 sale_unshipped, sum(sales_unshipped) sale_unshipped1,0 sale_unshipped2,0 sale_unshipped3,0 sale_unshipped4,
                                0 sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date between '%(from_date1)s' and '%(to_date1)s'
                                and ship_by = 'Factory'
                        union all    
                         
                        SELECT 0 sale_unshipped, 0 sale_unshipped1,sum(sales_unshipped) sale_unshipped2,0 sale_unshipped3,0 sale_unshipped4,
                                0 sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date between '%(from_date2)s' and '%(to_date2)s'
                                and ship_by = 'Factory'
                        union all    
                        SELECT 0 sale_unshipped, 0 sale_unshipped1,0 sale_unshipped2,sum(sales_unshipped) sale_unshipped3,0 sale_unshipped4,
                                0 sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date between '%(from_date3)s' and '%(to_date3)s'
                                and ship_by = 'Factory'
                        union all
                        SELECT 0 sale_unshipped, 0 sale_unshipped1,0 sale_unshipped2,0 sale_unshipped3,sum(sales_unshipped) sale_unshipped4,
                                0 sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date between '%(from_date4)s' and '%(to_date4)s'
                                and ship_by = 'Factory'
                        union all
                        SELECT 0 sale_unshipped, 0 sale_unshipped1,0 sale_unshipped2,0 sale_unshipped3,0 sale_unshipped4,
                                sum(sales_unshipped) sale_unshipped5, 0 sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date  between '%(from_date5)s' and '%(to_date5)s'
                                and ship_by = 'Factory'
                        union all    
                        SELECT 0 sale_unshipped, 0 sale_unshipped1,0 sale_unshipped2,0 sale_unshipped3,0 sale_unshipped4,
                                0 sale_unshipped5, sum(sales_unshipped) sale_unshipped6
                            FROM 
                                v_sales_contract_v2
                            WHERE 
                                product_id = %(product_id)s
                                and date between '%(from_date6)s' and '%(to_date6)s'
                                and ship_by = 'Factory'
                    )X
                                
                '''%({
                      'product_id':i['product_id'],
                      'from_date': from_date,
                      'to_date': to_date,
                      'from_date1': from_date1,
                      'to_date1': to_date1,
                      'from_date2': from_date2,
                      'to_date2': to_date2,
                      'from_date3': from_date3,
                      'to_date3': to_date3,
                      'from_date4': from_date4,
                      'to_date4': to_date4,
                      'from_date5': from_date5,
                      'to_date5': to_date5,
                      'from_date6': from_date6,
                      'to_date6': to_date6,
                      })
                print sql
                self.env.cr.execute(sql)
                for k in self.env.cr.dictfetchall():
                    sales_unshipped = k['sales_unshipped']
                    sales_unshipped1 = k['sales_unshipped1']
                    sales_unshipped2 = k['sales_unshipped2']
                    sales_unshipped3 = k['sales_unshipped3']
                    sales_unshipped4 = k['sales_unshipped4']
                    sales_unshipped5 = k['sales_unshipped5']
                    sales_unshipped6 = k['sales_unshipped6']
                consignment = qty_unfixed or 0.0
                
                val ={
                    'line_id':this.id,
                    'product_id':i['product_id'],
                    'sitting_stock':i['sitting_stock'] or 0.0,
                    'consignment':qty_unfixed,
                    'to_receive':to_receive,
                    'sales_unshipped':sales_unshipped,
                    'gross_long_position':sitting_stock  + to_receive - consignment,
                    'net_position':sitting_stock - qty_unfixed + (to_receive) - sales_unshipped,
#                      
                    'sales_unshipped1':sales_unshipped1,
                    'sales_unshipped2':sales_unshipped2,
                    'sales_unshipped3':sales_unshipped3,
                    'sales_unshipped4':sales_unshipped4,
                    'sales_unshipped5':sales_unshipped5,
                    'sales_unshipped6':sales_unshipped6,
                }
                self.env['long.short.line.report'].create(val)
    
    @api.multi
    def export_data(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'production_analysis_report',
        }

class LongShortLineReport(models.Model):
    _name = "long.short.line.report"
    
    line_id = fields.Many2one('long.short.report',string='Report')
    product_id = fields.Many2one('product.product',string='Product')
    
    sitting_stock = fields.Float(string="Sitting stocks",digits=(12, 0))
    consignment = fields.Float(string="Consg. RCVD.",digits=(12, 0))
    gross_long_position = fields.Float(string="Gross long pos.",digits=(12, 0))
    
    to_receive = fields.Float(string="P. REC.",digits=(12, 0))
    sales_unshipped = fields.Float(string="S Unshipped",digits=(12, 0))
    net_position = fields.Float(string="Net position",digits=(12, 0))
    
    to_receive1 = fields.Float(string="P. REC next 1 month",digits=(12, 0))
    sales_unshipped1 = fields.Float(string="Sales Unshipped 1",digits=(12, 0))
    net_position1 = fields.Float(string="Net position 1",digits=(12, 0))
    
    to_receive2 = fields.Float(string="Purchases to-receive 1",digits=(12, 0))
    sales_unshipped2 = fields.Float(string="Sales Unshipped 2",digits=(12, 0))
    net_position2 = fields.Float(string="Net position 2",digits=(12, 0))
    
    to_receive3 = fields.Float(string="Purchases to-receive 1",digits=(12, 0))
    sales_unshipped3 = fields.Float(string="Sales Unshipped 3",digits=(12, 0))
    net_position3 = fields.Float(string="Net position 3",digits=(12, 0))
    
    to_receive4 = fields.Float(string="Purchases to-receive 1",digits=(12, 0))
    sales_unshipped4 = fields.Float(string="Sales Unshipped 4",digits=(12, 0))
    net_position4 = fields.Float(string="Net position 4",digits=(12, 0))
    
    to_receive5 = fields.Float(string="Purchases to-receive 1",digits=(12, 0))
    sales_unshipped5 = fields.Float(string="Sales Unshipped 5",digits=(12, 0))
    net_position5 = fields.Float(string="Net position 5",digits=(12, 0))
    
    to_receive6 = fields.Float(string="Purchases to-receive 1",digits=(12, 0))
    sales_unshipped6 = fields.Float(string="Sales Unshipped 6",digits=(12, 0))
    net_position6 = fields.Float(string="Net position 6",digits=(12, 0))
    
    
    