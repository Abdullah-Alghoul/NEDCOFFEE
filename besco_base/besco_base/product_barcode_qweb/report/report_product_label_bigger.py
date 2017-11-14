# -*- coding: utf-8 -*-
##############################################################################
#
#    HLVSolution, Open Source Management Solution
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
        self.product_list = []
        self.localcontext.update({
            'get_rows_line' : self.get_rows_line,
            'get_product_list':self.get_product_list,
            'get_product_by_index' : self.get_product_by_index,
        })
    
    def get_product_list(self):
        wizard_data = self.localcontext['data']['form']
        self.product_list = []
        qty = wizard_data['qty']
        product_ids  = wizard_data['product_ids']
        product_obj = self.pool.get('product.product')
        index = 0
        for product in product_obj.browse(self.cr,self.uid,product_ids):
            i = 0
            while i< qty:
                product_vals = {
                    'index' : index,
                    'name': product.name or '',
                    'list_price': product.list_price or 0,
                }
                index += 1
                i+= 1
                self.product_list.append(product_vals)
        return True
    
    def get_rows_line(self):
        wizard_data = self.localcontext['data']['form']
        qty = wizard_data['qty']
        product_ids  = wizard_data['product_ids']
        total_qty = qty * len(product_ids)
        if total_qty%3 == 0:
            row = int(total_qty/3)
        else:
            row = int(total_qty/3) +1
        row_list = []
        print row
#         if row == 0:
#             row_list.append(0)
        i = 0
        while i < row:
            row_list.append(i)
            i += 1
        return row_list
    
    def get_product_by_index(self,rows,columns):
        index = (rows -1)*3 + (columns-1)
        product_list = self.product_list
        for prod in product_list:
            if prod['index'] == index:
                return {
                        'name' : prod['name'],
                        'list_price' : prod['list_price'],
                        }
        return {
                    'name' : '',
                    'list_price' : '',
                }
    
#     def get_product_by_index(self,rows,columns):
#         index = (rows -1)*3 + (columns-1)
#         product_list = self.product_list
#         for prod in product_list:
#             if prod['index'] == index:
#                 return prod['name']
#         return ''
    
#     def get_columns_line(self,index):
#         wizard_data = self.localcontext['data']['form']
#         qty = wizard_data['qty']
#         return qty
    
#     def get_product_list(self,columns,row):
#         wizard_data = self.localcontext['data']['form']
#         qty = wizard_data['qty']
#         product_ids  = wizard_data['product_ids']
#            
#         product_obj = self.pool.get('product.product')
        
        
        
#         product_length = len(product_ids)
#         total_qty = qty*product_length
#         index = 0
#         data = []
#         for product in product_obj.browse(self.cr,self.uid,product_ids):
#             product = {
#                 'name': product.name,
#                 'list_price': product.list_price or 0,
#             }
#             data.append(product)
#             index += 1
#         return data 
#         data = []
#         row = qty/3 + 1
#         diff = qty - row*3
#         for product in product_obj.browse(self.cr,self.uid,product_ids):
#             i = 0
#             index = 0
#             while i < row:
#                 product = {
#                     'index' : i,
#                     'name': product.name,
#                     'list_price': product.list_price or 0,
#                 }
#                 data.append(product)
#                 i+=1
              
        
#         for product in products_data:
#             if product['name']:
#                 i = 0
#                 label_row = []
#                 for product_row in range(form['qty']):
#                     i += 1
#                     label_data = {
#                         'name': product['name'],
#                         'price': product['list_price'],
#                     }
#                     label_row.append(label_data)
#                     if i == 3:
#                         i = 0
#                         data.append(label_row)
#                         label_row = []
#                          
#                 data.append(label_row)
#         if data:
#             return data
#         else:
#             return {}
#         return products_data


