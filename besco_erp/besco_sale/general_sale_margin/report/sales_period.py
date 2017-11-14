# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import time
from report import report_sxw
import pooler
from osv import osv
from tools.translate import _
import random
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_salesman': self.get_salesman,
            'get_vietname_date':self.get_vietname_date,
        })
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_salesman(self, object):
        self.cr.execute('''SELECT DISTINCT ru.id,ru.name
                        FROM sales_period sp inner join sales_period_line pl on sp.id = pl.sales_period_id
                        inner join res_users ru on pl.salesman_id = ru.id
                        WHERE sp.id = %s''',(object.id,))
        res = self.cr.fetchall()
        data = []
        users = res and [x for x in res]
        if users:
            for user in users:
                vals = [user[0],user[1]]
                minimum_sales = 0.0
                actual_sales = 0.0
                for x in object.sales_period_line:
                    if x.salesman_id.id == user[0]:
                        minimum_sales += x.minimum_sales
                        actual_sales += x.actual_sales
                vals.append(round(minimum_sales,2))
                vals.append(round(actual_sales,2))
                vals.append(minimum_sales and round(actual_sales * 100 / minimum_sales,3) or 0.0)
                data.append(vals)
        return data
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
