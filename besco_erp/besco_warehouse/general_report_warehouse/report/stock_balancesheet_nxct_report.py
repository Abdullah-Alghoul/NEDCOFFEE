# -*- coding: utf-8 -*-
##############################################################################
#
#    HLVSolution, Open Source Management Solution
#
##############################################################################

import time
import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import random
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.shop_ids =False
        self.shop_name =False
        self.category_ids = False
        self.product_ids = False
        self.parent_categ_ids = {}
        self.category_name = False
        
        self.product_id = False
        self.start_date = False
        self.date_end = False
        self.short_by = False
        self.company_name = False
        self.company_address = False
        self.location_id = False
        self.total_start_val = 0.0
        self.total_nhap_val = 0.0
        self.total_xuat_val = 0.0
        self.total_end_val = 0.0
        
        self.localcontext.update({
            'get_line':self.get_line,
            'get_vietname_date':self.get_vietname_date,
            'get_date':self.get_date,
            'get_location':self.get_location
        })
    
    def get_location(self,object):
        location_name = False
        for lo in  object.location_ids:
            location_name = lo.name
        return location_name
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_line(self, product_id, object):
        res =[]
        location_id = False

        lines = self.pool.get('report.stock.balance.sheet.line').search(self.cr,self.uid,[(['report_id','=',object.id]),('product_id','=',product_id)])
        lines = self.pool.get('report.stock.balance.sheet.line').browse(self.cr,self.uid,lines[0])
        bg_qty =  lines.bg_qty or 0.0
        bg_value =  lines.bg_value or 0.0
        for lo in  object.location_ids:
            location_id = lo.id
        sql ='''
            SELECT * FROM (
            SELECT 'xuat' type_s,sm.product_id,sm.date,sp.name,sm.origin, 0 nhap_qty ,0 nhap_gia, product_uom_qty xuat_qty, price_unit xuat_gia
            FROM stock_move sm left join stock_picking sp on sm.picking_id = sp.id 
            where sm.location_id = %s and sm.location_dest_id != %s
            and sm.state ='done'
            union all
            SELECT 'nhap' type_s, sm.product_id,sm.date,sp.name, sm.origin,product_uom_qty nhap_qty,price_unit nhap_gia ,0 xuat_qty ,0 xuat_gia
                FROM stock_move sm left join stock_picking sp on sm.picking_id = sp.id 
                where sm.location_id != %s and sm.location_dest_id = %s
            and sm.state ='done'
            )x
            where x.product_id = %s and date(timezone('UTC',date::timestamp)) between '%s' and '%s' 
            order by date
        '''%(location_id,location_id,location_id,location_id,product_id,object.date_start,object.date_end)
        print sql
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            contract = ''
            reference = ''
            if i['type_s']== 'xuat':
                bg_qty -= i['xuat_qty']
                bg_value -= i['xuat_qty'] * i['xuat_gia']
            else:
                bg_qty += i['nhap_qty']
                bg_value += i['nhap_qty'] * i['nhap_gia']
                if product_id == 1176:
                    if 'IM' in i['name']:
                        
                        picking = self.pool.get('stock.picking').search(self.cr,1,([('name','=',i['name'])]))
                        picking = self.pool.get('stock.picking').browse(self.cr,1,picking)
                        if ';' in picking.origin:
                            a = picking.origin.split(';')
                            contract = a and a[1] or ''
                            reference= a and a[0] or ''
                        else:
                            contract = picking.origin or ''
                
            res.append({
                        'date':self.get_vietname_date(i['date']),
                        'name':i['name'],
                        'contract':contract or '',
                        'reference':reference or '',
                        'origin':i['origin'],
                        'nhap_qty':i['nhap_qty'],
                        'nhap_gia':i['nhap_gia'],
                        'xuat_qty':i['xuat_qty'],
                        'xuat_gia':i['xuat_gia'],
                        'ton_qty':bg_qty,
                        'ton_value':bg_value,
                        'don_gia_ton':bg_qty and bg_value/bg_qty or 0.0
                        })
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
