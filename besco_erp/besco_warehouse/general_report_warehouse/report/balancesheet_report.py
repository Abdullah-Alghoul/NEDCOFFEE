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
        self.get_company(cr, uid)
        
        self.localcontext.update({
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_date_start':self.get_date_start,
            'get_date_end':self.get_date_end,
            'get_total_start_val':self.get_total_start_val,
            'get_total_nhap_val':self.get_total_nhap_val,
            'get_total_xuat_val':self.get_total_xuat_val,
            'get_total_end_val':self.get_total_end_val,
            'get_line_by_product':self.get_line_by_product,
            'get_current_date':self.get_current_date,
            'get_warehouse_name':self.get_warehouse_name,
            'get_category_name':self.get_category_name,
            'get_line_1_category':self.get_line_1_category,
            'get_line_product_by_categ':self.get_line_product_by_categ,
#             'get_uom_name':self.get_uom_name,
            'get_line_2_categ':self.get_line_2_categ,
            'quydoi_kyty':self.quydoi_kyty,
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
    
    def get_total_start_val(self, o):
        total_start_val = 0
        for line in o.report_lines:
            total_start_val += line.bg_value
        return total_start_val
    def get_total_nhap_val(self, o):
        total_nhap_val = 0
        for line in o.report_lines:
            total_nhap_val += line.in_value
        return total_nhap_val
    
    def get_total_xuat_val(self, o):
        total_xuat_val = 0
        for line in o.report_lines:
            total_xuat_val += line.out_value
        return total_xuat_val
    
    def get_total_end_val(self, o):
        total_end_val = 0
        for line in o.report_lines:
            total_end_val += line.end_value
        return total_end_val
    
    def get_company(self,cr,uid):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
         
    def get_company_name(self):
        return self.company_name
    def get_company_address(self):
        return self.company_address 
    
    def quydoi_kyty(self,seq):
        if seq ==1:
            return 'I.'
        elif seq ==2:
            return 'II.'
        elif seq ==3:
            return 'III.'
        elif seq ==4:
            return 'VI.'
        elif seq ==5:
            return 'V.'
        elif seq ==6:
            return 'VI.'
        elif seq ==7:
            return 'VII.'
        elif seq ==8:
            return 'VIII.'
        elif seq ==9:
            return 'IX.'
        elif seq ==10:
            return 'X.'
        elif seq ==11:
            return 'XI.'
        elif seq ==12:
            return 'XII.'
        elif seq ==13:
            return 'XIII.'
        elif seq ==14:
            return 'XIV.'
        elif seq ==15:
            return 'XV.'
        elif seq ==16:
            return 'XVI.'
        elif seq ==17:
            return 'XVII.'
        elif seq ==18:
            return 'XVIII.'
        elif seq ==19:
            return 'XIX.'
        elif seq ==20:
            return 'XX.'
        else:
            return seq
        
        
    def get_date_start(self, o):
#         if not o.start_date:
#             self.get_header()
        return self.get_vietname_date(o.date_start)
    
    def get_date_end(self, o):
#         if not self.date_end:
#             self.get_header()
        return self.get_vietname_date(o.date_end)
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_vietname_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_warehouse_name(self):
        if not self.shop_name:
            self.get_header()
        return self.shop_name 
    
    def get_category_name(self):
        return self.category_name 
    
    
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
#         self.shop_ids = [1]
#         shop_obj = self.pool.get('sale.shop').browse(self.cr,self.uid,self.shop_ids)
#         self.shop_name = shop_obj and shop_obj[0].name or False
#         self.shop_ids = (','.join(map(str, self.shop_ids)))
        self.short_by = wizard_data['short_by'] and wizard_data['short_by'] or False
        self.start_date = wizard_data['date_start']
        self.date_end = wizard_data['date_end']
        self.location_id = wizard_data['location_id'] and wizard_data['location_id'][0] or False
        if self.location_id:
            self.location_id = self.pool.get('stock.location').search(self.cr, self.uid, [('id','child_of',self.location_id)])
            self.location_id = (','.join(map(str, self.location_id)))
            
        self.category_ids = wizard_data['categ_ids'] or []
        self.product_ids = wizard_data['product_ids'] or []
        if len(self.product_ids):
            self.cr.execute('''
            select pt.categ_id
            from product_product pp join product_template pt on pp.product_tmpl_id=pt.id
            where pp.id in (%s)
            '''%(','.join(map(str, self.product_ids))))
            self.category_ids = [x[0] for x in self.cr.fetchall()]
        return True
    
    def get_line_1_category(self):
        sql = False
        result = [{'id': None, 'name': u'Nhóm cha'}]
        parents = []
        if not len(self.category_ids):
            #THANH: Get Root and childs level 1 if note category from wizard
            parent_ids = self.pool.get('product.category').search(self.cr, self.uid, [('parent_id', '=', False)])
            self.category_ids = self.pool.get('product.category').search(self.cr, self.uid, [('parent_id', 'in', parent_ids)])
            
        if len(self.category_ids):
            sql ='''
                SELECT distinct pc.parent_id, pc.id
                FROM product_category pc  
                WHERE id in (%s)
            '''%(','.join(map(str, self.category_ids)))
            self.cr.execute(sql)
            for x in self.cr.fetchall():
                if x[0]:
                    parents.append(x[0])
                if not self.parent_categ_ids.has_key(x[0]):
                    self.parent_categ_ids[x[0]] = []
                if x[1] in self.category_ids:
                    self.parent_categ_ids[x[0]].append(x[1])
                    
            if len(parents):
                sql='''
                    SELECT id,'['||code||'] ' ||name as name 
                    FROM product_category 
                    WHERE id in (%s)
                    ORDER BY seq
                '''%(','.join(map(str, parents)))
            
                self.cr.execute(sql)
                for x in self.cr.dictfetchall():
                    result.append(x)
        return result
    
    def get_line_2_categ(self, categ_id):
        if self.parent_categ_ids.has_key(categ_id):
            sql='''
                SELECT id,'['||code||'] ' ||name as name 
                FROM product_category 
                WHERE id in (%s)
                ORDER BY seq
            '''%(','.join(map(str, self.parent_categ_ids[categ_id])))
            self.cr.execute(sql)
            return self.cr.dictfetchall()
        return []
            
    def get_line_product_by_categ(self, category_id):
        
        where = 'WHERE 1=1'
        
        if category_id:
            where += ' AND pt.categ_id in(%s)'%(category_id)
        if len(self.product_ids):
            where += ' AND pp.id in (%s)'%(','.join(map(str, self.product_ids)))
            
        if self.location_id:
            sql ='''  
                SELECT pp.id, pp.name_template, pu.name uom_name, coalesce(pp.barcode,pp.default_code) product_code, 
                    sum(start_onhand_qty) start_onhand_qty, sum(start_val) start_val, 
                    sum(nhaptk_qty) nhaptk_qty, sum(nhaptk_val) nhaptk_val,
                    sum(xuattk_qty) xuattk_qty, sum(xuattk_val) xuattk_val,    
                    sum(end_onhand_qty) end_onhand_qty,
                    sum(end_val) end_val
                    
                    --spl.name,spl.date,spl.life_date,
                    
                    From
                        (SELECT
                            stm.product_id,
                            
                            --stm.prodlot_id,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then -1*stm.product_qty 
                            else 0.0 end
                            end start_onhand_qty,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then -1*(stm.price_unit * stm.product_qty)
                            else 0.0 end
                            end start_val,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then stm.product_qty
                            else 0.0 end nhaptk_qty,
                            
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then 1*stm.product_qty 
                            else 0.0
                            end xuattk_qty,
                    
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else 0.0 end nhaptk_val,
                            
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then 1*(stm.price_unit * stm.product_qty)
                            else 0.0
                            end xuattk_val,        
                             
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then -1*stm.product_qty 
                            else 0.0 end
                            end end_onhand_qty,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then -1*(stm.price_unit * stm.product_qty)
                            else 0.0 end
                            end end_val            
                        FROM stock_move stm 
                            join stock_location loc1 on stm.location_id=loc1.id
                            join stock_location loc2 on stm.location_dest_id=loc2.id
                        WHERE stm.state= 'done'
                            --and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s' 
                            )foo
                    left join product_product pp on foo.product_id = pp.id
                        left join product_template pt on pp.product_tmpl_id = pt.id
                        left join product_uom pu on pt.uom_id = pu.id
                    
                    --left join stock_production_lot spl on foo.prodlot_id = spl.id
                    
                    %(where)s
                    
                    group by pp.id, pp.name_template, pu.name
                    
                    --spl.name,spl.date,spl.life_date
                    
                    order by pp.name_template
                
                 '''%({
                  'start_date': self.start_date,
                  'end_date': self.date_end,
                  'shop_ids':self.shop_ids,
                  'where': where,
                  }) 
        else:
            sql ='''  
                SELECT pp.id, pp.name_template, pu.name uom_name, coalesce(pp.barcode,pp.default_code) product_code, 
                    sum(start_onhand_qty) start_onhand_qty, sum(start_val) start_val, 
                    sum(nhaptk_qty) nhaptk_qty, sum(nhaptk_val) nhaptk_val,
                    sum(xuattk_qty) xuattk_qty, sum(xuattk_val) xuattk_val,    
                    sum(end_onhand_qty) end_onhand_qty,
                    sum(end_val) end_val
                    
                    --spl.name,spl.date,spl.life_date,
                    
                    From
                        (SELECT
                            stm.product_id,stm.product_uom,
                            
                            --stm.prodlot_id,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then -1*stm.product_qty 
                            else 0.0 end
                            end start_onhand_qty,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                            then -1*(stm.price_unit * stm.product_qty)
                            else 0.0 end
                            end start_val,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then stm.product_qty
                            else 0.0 end nhaptk_qty,
                            
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then 1*stm.product_qty 
                            else 0.0
                            end xuattk_qty,
                    
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else 0.0 end nhaptk_val,
                            
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                            then 1*(stm.price_unit * stm.product_qty)
                            else 0.0
                            end xuattk_val,        
                             
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then -1*stm.product_qty 
                            else 0.0 end
                            end end_onhand_qty,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then (stm.price_unit * stm.product_qty)
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                            then -1*(stm.price_unit * stm.product_qty)
                            else 0.0 end
                            end end_val            
                        FROM stock_move stm 
                            join stock_location loc1 on stm.location_id=loc1.id
                            join stock_location loc2 on stm.location_dest_id=loc2.id
                        WHERE stm.state= 'done'
                            --and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s' 
                            )foo
                    left join product_product pp on foo.product_id = pp.id
                        left join product_template pt on pp.product_tmpl_id = pt.id
                        left join product_uom pu on pt.uom_id = pu.id
                    
                    --left join stock_production_lot spl on foo.prodlot_id = spl.id
                    
                    %(where)s
                    
                    group by pp.id, pp.name_template, pu.name
                    
                    --spl.name,spl.date,spl.life_date,
                    
                    order by pp.name_template
                '''%({
                  'start_date': self.start_date,
                  'end_date': self.date_end,
                  'shop_ids':self.shop_ids,
                  'where': where,
                  }) 
        
        self.cr.execute(sql)
        res =[]
        for i in self.cr.dictfetchall():
            self.total_start_val = self.total_start_val + (i['start_val'] or 0)
            self.total_nhap_val = self.total_nhap_val +(i['nhaptk_val'] or 0.0)
            self.total_xuat_val = self.total_xuat_val +(i['xuattk_val'] or 0.0)
            self.total_end_val = self.total_end_val +(i['end_val'] or 0.0)
            res.append(
                   {
                   'product_id':i['id'],
                   'name_template':i['name_template'],
                   'product_code': i['product_code'],
                   'uom_name': i['uom_name'],
                   'start_onhand_qty':i['start_onhand_qty'],
                   'start_val':i['start_val'] or 0.0,
                   'nhaptk_qty':i['nhaptk_qty'] or 0.0,
                   'nhaptk_val':i['nhaptk_val'] or 0.0,
                   'xuattk_qty':i['xuattk_qty'] or 0.0,
                   'xuattk_val':i['xuattk_val'] or 0.0,
                   'end_onhand_qty':i['end_onhand_qty'] or 0.0,
                   'end_val':i['end_val'] or 0.0,
                   'name':i.has_key('name') or False,
                   'date':i.has_key('date') and self.get_vietname_datetime(i['date']) or False,
                   'life_date':i.has_key('life_date') and self.get_vietname_datetime(i['life_date']) or False
                   })
        return res
    
    def get_line_by_product(self):
        where = 'WHERE 1=1'
        
        if len(self.category_ids):
            where += ' AND pt.categ_id in(%s)'%(','.join(map(str, self.category_ids)))
        if len(self.product_ids):
            where += ' AND pp.id in (%s)'%(','.join(map(str, self.product_ids)))
            
        if not self.location_id:
            sql ='''  
            SELECT pp.id, pp.name_template, coalesce(pp.barcode,pp.default_code) product_code, 
                pu.name uom_name, 
                sum(start_onhand_qty) start_onhand_qty, sum(start_val) start_val, 
                sum(nhaptk_qty) nhaptk_qty, sum(nhaptk_val) nhaptk_val,
                sum(xuattk_qty) xuattk_qty, sum(xuattk_val) xuattk_val,    
                sum(end_onhand_qty) end_onhand_qty,
                sum(end_val) end_val
                
                --,spl.name
                
                From
                    (SELECT
                        stm.product_id,stm.product_uom, 
                        
                        --spol.lot_id,   
                        
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then stm.product_qty
                        else
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then -1*stm.product_qty 
                        else 0.0 end
                        end start_onhand_qty,
                        
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then -1*(stm.price_unit * stm.product_qty)
                        else 0.0 end
                        end start_val,
                        
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then stm.product_qty
                        else 0.0 end nhaptk_qty,
                        
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then 1*stm.product_qty 
                        else 0.0
                        end xuattk_qty,
                
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else 0.0 end nhaptk_val,
                        
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then 1*(stm.price_unit * stm.product_qty)
                        else 0.0
                        end xuattk_val,        
                         
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then stm.product_qty
                        else
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then -1*stm.product_qty 
                        else 0.0 end
                        end end_onhand_qty,
                        
                        case when loc1.usage != 'internal' and loc2.usage = 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else
                        case when loc1.usage = 'internal' and loc2.usage != 'internal' and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then -1*(stm.price_unit * stm.product_qty)
                        else 0.0 end
                        end end_val            
                    FROM stock_move stm 
                        join stock_location loc1 on stm.location_id=loc1.id
                        join stock_location loc2 on stm.location_dest_id=loc2.id
                        left join(stock_pack_operation spo join stock_pack_operation_lot spol on spo.id= spol.operation_id)
                            on stm.picking_id = spo.picking_id
                    WHERE 
                        stm.state= 'done'
                        --date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s' 
                        )foo
                
                left join product_product pp on foo.product_id = pp.id
                    left join product_template pt on pp.product_tmpl_id = pt.id
                    left join product_uom pu on pt.uom_id = pu.id
                    
                    --left join stock_production_lot spl on foo.lot_id = spl.id
                
                %(where)s
                
                group by pp.id, pp.name_template, pu.name
                
                --,spl.name
                
                order by pp.name_template
            
            '''%({
              'start_date': self.start_date,
              'end_date': self.date_end,
              'where': where,
              })
           
        else:
            sql ='''  
            SELECT pp.id, pp.name_template, pu.name uom_name, coalesce(pp.barcode,pp.default_code) product_code,
                sum(start_onhand_qty) start_onhand_qty, sum(start_val) start_val, 
                sum(nhaptk_qty) nhaptk_qty, sum(nhaptk_val) nhaptk_val,
                sum(xuattk_qty) xuattk_qty, sum(xuattk_val) xuattk_val,    
                sum(end_onhand_qty) end_onhand_qty,
                sum(end_val) end_val
                
                --,spl.name
                
                From
                    (SELECT  
                        stm.product_id,stm.product_uom,
                        
                        --spol.lot_id,
                        
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then stm.product_qty
                        else
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then -1*stm.product_qty 
                        else 0.0 end
                        end start_onhand_qty,
                        
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) < '%(start_date)s'
                        then -1*(stm.price_unit * stm.product_qty)
                        else 0.0 end
                        end start_val,
                        
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then stm.product_qty
                        else 0.0 end nhaptk_qty,
                        
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then 1*stm.product_qty 
                        else 0.0
                        end xuattk_qty,
                
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else 0.0 end nhaptk_val,
                        
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s'
                        then 1*(stm.price_unit * stm.product_qty)
                        else 0.0
                        end xuattk_val,        
                         
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then stm.product_qty
                        else
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then -1*stm.product_qty 
                        else 0.0 end
                        end end_onhand_qty,
                        
                        case when loc1.id not in ('%(location_id)s') and loc2.id in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then (stm.price_unit * stm.product_qty)
                        else
                        case when loc1.id in ('%(location_id)s') and loc2.id not in ('%(location_id)s') and date(timezone('UTC',stm.date::timestamp)) <= '%(end_date)s'
                        then -1*(stm.price_unit * stm.product_qty)
                        else 0.0 end
                        end end_val            
                    FROM stock_move stm 
                        join stock_location loc1 on stm.location_id=loc1.id
                        join stock_location loc2 on stm.location_dest_id=loc2.id
                        
                        --left join(stock_pack_operation spo join stock_pack_operation_lot spol on spo.id= spol.operation_id)
                        --    on stm.picking_id = spo.picking_id
                    
                    WHERE stm.state= 'done'
                        --and date(timezone('UTC',stm.date::timestamp)) between '%(start_date)s' and '%(end_date)s' 
                        )foo
                left join product_product pp on foo.product_id = pp.id
                    left join product_template pt on pp.product_tmpl_id = pt.id
                    left join product_uom pu on pt.uom_id = pu.id
                
                --left join stock_production_lot spl on foo.lot_id = spl.id
                
                %(where)s
                
                group by pp.id, pp.name_template, pu.name
                
                --,spl.name
                
                order by pp.name_template
            '''%({
              'start_date': self.start_date,
              'end_date': self.date_end,
              'location_id':self.location_id,
              'where': where,
              })
        
        self.cr.execute(sql)
        res =[]
        for i in self.cr.dictfetchall():
            self.total_start_val = self.total_start_val + (i['start_val'] or 0)
            self.total_nhap_val = self.total_nhap_val +(i['nhaptk_val'] or 0.0)
            self.total_xuat_val = self.total_xuat_val +(i['xuattk_val'] or 0.0)
            self.total_end_val = self.total_end_val +(i['end_val'] or 0.0)
            res.append(
                   {
                   'product_id':i['id'],
                   'name_template':i['name_template'],
                   'product_code':i['product_code'],
                   'uom_name': i['uom_name'],
                   'start_onhand_qty':i['start_onhand_qty'],
                   'start_val':i['start_val'] or 0.0,
                   'nhaptk_qty':i['nhaptk_qty'] or 0.0,
                   'nhaptk_val':i['nhaptk_val'] or 0.0,
                   'xuattk_qty':i['xuattk_qty'] or 0.0,
                   'xuattk_val':i['xuattk_val'] or 0.0,
                   'end_onhand_qty':i['end_onhand_qty'] or 0.0,
                   'end_val':i['end_val'] or 0.0,
                   'name':i.has_key('name') or False,
                   'date':i.has_key('date') and self.get_vietname_datetime(i['date']) or False,
                   'life_date':i.has_key('life_date') and self.get_vietname_datetime(i['life_date']) or False
                   })
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
