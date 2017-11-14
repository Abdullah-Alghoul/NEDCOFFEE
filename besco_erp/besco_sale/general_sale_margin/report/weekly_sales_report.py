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
from dateutil.relativedelta import relativedelta
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        pool = pooler.get_pool(self.cr.dbname)
        self.user_obj = pooler.get_pool(self.cr.dbname).get('res.users')
        self.cr = cr
        self.uid = uid
        self.lead_planned_revenue = 0.0
        self.opp_planned_revenue = 0.0
        self.total_order = 0.0
        self.localcontext.update({
            'get_salesmans': self.get_salesmans,
            'get_salesman_info': self.get_salesman_info,
            'get_total_expected_revenue': self.get_total_expected_revenue,
            'get_salesteam': self.get_salesteam,
            'get_stage': self.get_stage,
            'get_lead': self.get_lead,
            'get_opportunity': self.get_opportunity,
            'get_lead_action': self.get_lead_action,
            'get_lead_issue': self.get_lead_issue,
            'get_lead_history': self.get_lead_history,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'get_partner_address': self.get_partner_address,
            'get_quotation': self.get_quotation,
            'get_order_action': self.get_order_action,
            'get_order_issue': self.get_order_issue,
            'get_total_order': self.get_total_order,
            
            'get_vietname_date':self.get_vietname_date,
        })
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
    def get_partner_address(self, partner):
        address = ''
        if partner:
            address += partner.address and partner.address[0].street or ''
            address += partner.address and partner.address[0].district_id and ', ' +  partner.address[0].district_id.name or ''
            address += partner.address and partner.address[0].state_id and ', ' +  partner.address[0].state_id.name or ''
            address += partner.address and partner.address[0].country_id and ', ' +  partner.address[0].country_id.name or ''
        return address
    
    def date_from(self):
        wizard_data = self.localcontext['data']['form']
        return datetime.strptime(wizard_data['from_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    
    def date_to(self):
        wizard_data = self.localcontext['data']['form']
        return  datetime.strptime(wizard_data['to_date'], '%Y-%m-%d').strftime('%d/%m/%Y')
    
    def get_salesmans(self):
        wizard_data = self.localcontext['data']['form']
        salesman_ids = wizard_data['salesman_ids']
        return salesman_ids
    
    def get_salesman_info(self,salesman_id):
        return pooler.get_pool(self.cr.dbname).get('res.users').browse(self.cr, self.uid, salesman_id).name
    
    def get_salesteam(self):
        wizard_data = self.localcontext['data']['form']
        sale_team = wizard_data['sale_team'][1]
        return sale_team
    
    def get_stage(self):
        stages = []
        wizard_data = self.localcontext['data']['form']
        sale_team_id = wizard_data['sale_team'][0]
        for line in pooler.get_pool(self.cr.dbname).get('crm.case.section').browse(self.cr, self.uid, sale_team_id).stage_ids:
            stages.append(line.name)
        return stages
    
    def get_lead(self, salesman_id):
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT id FROM crm_lead WHERE type='lead' AND user_id=%s AND id in (SELECT DISTINCT lead_id
                FROM opportunity_action_history
                WHERE date_create >= %s and date_create <= %s
                UNION
                SELECT DISTINCT lead_id
                FROM opportunity_customer_issue
                WHERE date_create >= %s and date_create <= %s
                UNION
                SELECT DISTINCT res_id
                FROM mail_message
                WHERE model = 'crm.lead' and create_date >= %s and create_date <= %s)
                ORDER BY id
        ''',(salesman_id,from_date,to_date,from_date,to_date,from_date,to_date,))
        res = self.cr.fetchall()
        lead_ids = [x[0] for x in res]
        if lead_ids:
            res = pooler.get_pool(self.cr.dbname).get('crm.lead').browse(self.cr, self.uid, lead_ids)
            for line in res:
                self.lead_planned_revenue+= line.planned_revenue
            return res
        self.lead_planned_revenue = 0.0
        return []
    
    def get_opportunity(self, salesman_id):
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT id FROM crm_lead WHERE type='opportunity' AND user_id=%s AND id in (SELECT DISTINCT lead_id
                FROM opportunity_action_history
                WHERE date_create >= %s and date_create <= %s
                UNION
                SELECT DISTINCT lead_id
                FROM opportunity_customer_issue
                WHERE date_create >= %s and date_create <= %s
                UNION
                SELECT DISTINCT res_id
                FROM mail_message
                WHERE model = 'crm.lead' and create_date >= %s and create_date <= %s)
                ORDER BY id
        ''',(salesman_id,from_date,to_date,from_date,to_date,from_date,to_date,))
        res = self.cr.fetchall()
        opp_ids = [x[0] for x in res]
        if opp_ids:
            res = pooler.get_pool(self.cr.dbname).get('crm.lead').browse(self.cr, self.uid, opp_ids)
            for line in res:
                self.opp_planned_revenue+= line.planned_revenue
            return res
        self.opp_planned_revenue = 0.0
        return []
    
    def get_quotation(self, salesman_id):
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT id, name
                FROM sale_order
                WHERE user_id = %s AND state not in ('draft','cancel') AND date_confirm >= %s and date_confirm <= %s
                ORDER BY name
        ''',(salesman_id,from_date,to_date,))
        res = self.cr.fetchall()
        order_ids = [x[0] for x in res]
        if order_ids:
            res = pooler.get_pool(self.cr.dbname).get('sale.order').browse(self.cr, self.uid, order_ids)
            for line in res:
                self.total_order+= line.amount_total
            return res
        self.total_order = 0.0
        return []
    
    def get_order_action(self, sale_id):
        action = ''
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT date_create,action
                FROM opportunity_action_history
                WHERE sale_id=%s and date_create >= %s and date_create <= %s order by date_create
        ''',(sale_id,from_date,to_date,))
        res = self.cr.fetchall()
        for x in res:
            x1 = ''
            if x[0]:
                x1 = datetime.strptime(x[0], DATETIME_FORMAT).strftime("%d-%m-%Y")
            action += x1 + ': ' + x[1] + '\n'
        return action
    
    def get_order_issue(self, sale_id):
        action = ''
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT date_create,issue
                FROM opportunity_customer_issue
                WHERE sale_id=%s and date_create >= %s and date_create <= %s order by date_create
        ''',(sale_id,from_date,to_date,))
        res = self.cr.fetchall()
        for x in res:
            x1 = ''
            if x[0]:
                x1 = datetime.strptime(x[0], DATETIME_FORMAT).strftime("%d-%m-%Y")
            action += x1 + ': ' + x[1] + '\n'
        return action
    
    def get_total_expected_revenue(self):
        return (self.opp_planned_revenue + self.lead_planned_revenue)
    
    def get_total_order(self):
        return self.total_order
    
    def get_lead_action(self, lead_id):
        action = ''
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT date_create,action
                FROM opportunity_action_history
                WHERE lead_id=%s and date_create >= %s and date_create <= %s order by date_create
        ''',(lead_id,from_date,to_date,))
        res = self.cr.fetchall()
        for x in res:
            x1 = ''
            if x[0]:
                x1 = datetime.strptime(x[0], DATETIME_FORMAT).strftime("%d-%m-%Y")
            action += x1 + ': ' + x[1] + '\n'
        return action
    
    def get_lead_issue(self, lead_id):
        action = ''
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT date_create,issue
                FROM opportunity_customer_issue
                WHERE lead_id=%s and date_create >= %s and date_create <= %s order by date_create
        ''',(lead_id,from_date,to_date,))
        res = self.cr.fetchall()
        for x in res:
            x1 = ''
            if x[0]:
                x1 = datetime.strptime(x[0], DATETIME_FORMAT).strftime("%d-%m-%Y")
            action += x1 + ': ' + x[1] + '\n'
        return action
    
    def get_lead_history(self, lead_id):
        action = ''
        wizard_data = self.localcontext['data']['form']
        from_date = wizard_data['from_date']
        to_date = wizard_data['to_date']
        self.cr.execute('''
                SELECT date,subject
                FROM mail_message
                WHERE model = 'crm.lead' and res_id=%s and create_date >= %s and create_date <= %s order by date
        ''',(lead_id,from_date,to_date,))
        res = self.cr.fetchall()
        for x in res:
            x1 = ''
            if x[0]:
                x1 = datetime.strptime(x[0], DATETIME_FORMAT).strftime("%d-%m-%Y")
            action += x1 + ': ' + x[1] + '\n'
        return action
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
