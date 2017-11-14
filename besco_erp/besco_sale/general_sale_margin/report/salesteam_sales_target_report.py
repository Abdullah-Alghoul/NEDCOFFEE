# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import time
from openerp.report import report_sxw
from datetime import datetime
import pooler

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_month': self.get_month,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'get_salesteam': self.get_salesteam,
            'get_line': self.get_line,
        })
    def date_from(self):
        wizard_data = self.localcontext['data']['form']
        return datetime.strptime(wizard_data['from_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
    
    def date_to(self):
        wizard_data = self.localcontext['data']['form']
        return  datetime.strptime(wizard_data['to_date'], '%Y-%m-%d').strftime('%d-%m-%Y')
    
    def get_month(self):
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        from_month = datetime.strptime(from_date, '%Y-%m-%d').month
        to_month = datetime.strptime(to_date, '%Y-%m-%d').month
        return [i for i in range(from_month,to_month+1)]
    
    def get_line(self, fiscal_id, salesteam_id):
        sales_period_pool = pooler.get_pool(self.cr.dbname).get('sales.period')
        result = []
        months = self.get_month()
        for month in months:
            self.cr.execute("SELECT id FROM sales_period WHERE fiscalyear_id=%s AND EXTRACT(MONTH FROM date_start)=%s",(fiscal_id,month,))
            res = self.cr.fetchall()
            period_ids = [x[0] for x in res] or []
            minimum = 0.0
            actual = 0.0
            percentage = 0.0
            for period in sales_period_pool.browse(self.cr, self.uid, period_ids):
                minimum += period.total_minimum_line
                actual += period.total_actual_line
            percentage = minimum and round(actual * 100 / minimum,3) or 0.0
            result.append([minimum, actual, percentage])
        return result
    
    def get_salesteam(self):
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        result = []
        self.cr.execute("SELECT s.id, st.salesteam_id, cs.name FROM sales_fiscalyear s inner join fiscalyear_salesteam st on s.id = st.fiscalyear_id inner join crm_case_section cs on st.salesteam_id = cs.id WHERE s.date_start <= %s and s.date_stop >= %s",(from_date,to_date,))
        res = self.cr.fetchall()
        data = [x for x in res]
        
        for line in data:
            amount = [0,0,0]
            if line[0] and line[1]:
                res = self.get_line(line[0],line[1])
                for month in res:
                    amount[0] += month[0]
                    amount[1] += month[1]
                amount[2] = amount[0] and round(amount[1] * 100 / amount[0],3) or 0.0
            line = line + (amount[0],amount[1],amount[2],)
            result.append(line)
        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
