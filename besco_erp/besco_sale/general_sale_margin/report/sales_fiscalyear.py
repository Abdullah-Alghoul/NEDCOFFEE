# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import time
from openerp.report import report_sxw

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_salesman': self.get_salesman,
            'get_line': self.get_line,
        })
    
    def get_salesman(self, object):
        self.cr.execute('''SELECT DISTINCT ru.id,ru.name
                        FROM sales_period sp inner join sales_period_line pl on sp.id = pl.sales_period_id
                        inner join res_users ru on pl.salesman_id = ru.id
                        WHERE sp.fiscalyear_id = %s''',(object.id,))
        res = self.cr.fetchall()
        data = []
        users = res and [x for x in res]
        if users:
            for user in users:
                vals = [user[0],user[1]]
                minimum_sales = 0.0
                actual_sales = 0.0
                for line in object.period_ids:
                    for x in line.sales_period_line:
                        if x.salesman_id.id == user[0]:
                            minimum_sales += x.minimum_sales
                            actual_sales += x.actual_sales
                vals.append(round(minimum_sales,2))
                vals.append(round(actual_sales,2))
                vals.append(minimum_sales and round(actual_sales * 100 / minimum_sales,3) or 0.0)
                data.append(vals)
        return data
    
    def get_line(self, object, salesman_id):
        res = []
        for line in object.period_ids:
            data = [None,None,None]
            for x in line.sales_period_line:
                if x.salesman_id.id == salesman_id:
                    data = [round(x.minimum_sales,2),round(x.actual_sales,2),round(x.percentage,3)]
            res.append(data)
        return res
    
#    def get_line(self, object):
#        periods_name = []
#        i = 0
#        while i < 13:
#            periods_name.append('')
#            i += 1
#        i = 0
#        for period in object.period_ids:
#            periods_name[0] = period.name
#            i += 1
#        return periods_name
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
