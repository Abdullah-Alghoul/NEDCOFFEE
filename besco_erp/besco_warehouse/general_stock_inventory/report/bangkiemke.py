# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import logging
logger = logging.getLogger('report_aeroo')

from openerp.report import report_sxw
from openerp.report.report_sxw import rml_parse

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(rml_parse):
    def __init__(self, cr, uid, name, context):
        super(self.__class__, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.lead_planned_revenue = 0.0
        self.opp_planned_revenue = 0.0
        self.total_order = 0.0
        self.company_name = False
        self.company_address = False
        
        self.localcontext.update({
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address, 
            'get_line':self.get_line,
            'get_vietname_date':self.get_vietname_date,
            'get_vietname_datetime':self.get_vietname_datetime,
            'get_current_date':self.get_current_date,
            'get_freeze_date': self.get_freeze_date,
            'get_uom_convert': self.get_uom_convert,
        })
    
    def get_uom_convert(self, product_id):
        product = self.pool.get('product.product').browse(self.cr, self.uid, product_id).product_tmpl_id
        if product.uom_ids:
            uom = product.uom_ids[0]
            if uom.uom_type == 'bigger':
                return '1 ' + uom.uom_id.name + ' = ' + str(uom.factor) + ' ' + product.uom_id.name
            else:
                return '1 ' + product.uom_id.name + ' = ' + str(uom.factor) + ' ' + uom.uom_id.name
        else:
            return ''
        
    def get_current_date(self):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)        
        return date.strftime('%d/%m/%Y %H:%M:%S')
    
    def get_company(self,cr,uid):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
    
    def get_freeze_date(self, o):
        user_pool = self.pool.get('res.users')
        date_user_tz = user_pool._convert_user_datetime(self.cr, 1, o.freeze_date)
        date = date_user_tz.strftime('%d/%m/%Y %H:%M:%S')
        return date
    
    def get_company_name(self):
        return self.company_name
    
    def get_company_address(self):
        return self.company_address    
                    
    def get_line(self, object):
        inventory_id = object.id
        
        sql ='''
            SELECT sl.name location_name,pp.name_template product_name,pp.default_code, pp.barcode, uom.name uom_name, 
                ca.name category_name, sil.product_qty, sil.id, sil.product_id
                
            FROM stock_inventory_line sil 
            LEFT JOIN (product_template pt inner join product_product pp on pt.id = pp.product_tmpl_id inner join product_category ca on pt.categ_id = ca.id)
            ON  sil.product_id =  pp.id
            LEFT JOIN product_uom uom 
            ON sil.product_uom_id = uom.id
            INNER JOIN  stock_location sl ON sl.id = sil.location_id
            WHERE sil.inventory_id = %s
            Order By category_name
        ''' %(inventory_id)
        self.cr.execute(sql)
        res =[]
        for i in self.cr.dictfetchall():
#            sum_sys_value += i['sys_quantity'] * i['freeze_cost'],
#            sum_count_value += i['product_qty'] * i['freeze_cost']
            res.append(
                       {'product_name':i['product_name'],
                        'uom_name':i['uom_name'],
                        'barcode':i['barcode'],
                        'default_code':i['default_code'],
                        'category_name':i['category_name'],
                        'location_name':i['location_name'],
                        'product_qty': i['product_qty'],
                        'product_id': i['product_id'],
                        'id': i['id'],
                       })
        return res    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
