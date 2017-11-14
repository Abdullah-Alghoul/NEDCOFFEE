# -*- coding: utf-8 -*-
##############################################################################
#
#    HLVSolution, Open Source Management Solution
#
##############################################################################


from report import report_sxw
import pooler
from osv import osv
from tools.translate import _
import random
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"


class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.company_name = False
        self.company_address = False
        self.get_company(cr, uid)
        self.localcontext.update({
            'get_company_name':self.get_company_name,
            'get_company_address':self.get_company_address,
            'get_line':self.get_line,
            'get_current_date':self.get_current_date,
            'get_no':self.get_no,
        })
        
    def get_current_date(self):
        date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_company(self,cr,uid):
        user_obj = self.pool.get('res.users').browse(cr,uid,uid)
        self.company_name = user_obj and user_obj.company_id and user_obj.company_id.name or ''
        self.company_address = user_obj and user_obj.company_id and user_obj.company_id.street or ''
        self.vat = user_obj and user_obj.company_id and user_obj.company_id.vat or ''
        
    def get_company_name(self):
        return self.company_name
    
    def get_company_address(self):
        return self.company_address 
    
    def get_no(self,check):
        if check == True:
            return 'x'
        else:
            return ' '
    
    def get_line(self,partner_obj,o):
        sql ='''
            SELECT po.name,pp.name_template ,cn.* 
            FROM 
                purchase_congno_chitiet_khachhang cn
                inner join purchase_order po on cn.purchase_id = po.id
                inner join product_product pp on pp.id = cn.product_id
            WHERE
                cn.partner_id = %s
            and master_id = %s
            order by id
        '''%(partner_obj.id,o.id)
        self.cr.execute(sql)
        return self.cr.dictfetchall()
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
