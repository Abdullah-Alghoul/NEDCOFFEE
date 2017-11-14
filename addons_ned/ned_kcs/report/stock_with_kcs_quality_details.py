# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
from openerp import SUPERUSER_ID

class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        self.s_contract = False
        self.total = 0.0
        self.localcontext.update({
            'get_date':self.get_date,
            'get_line':self.get_line,
            'get_lot_allocation':self.get_lot_allocation,
            'get_balance_net':self.get_balance_net,
            'get_maize':self.get_maize,
            'get_objcontract':self.get_objcontract,
            'get_aver':self.get_aver,
            'get_total':self.get_total,
            'get_datetime':self.get_datetime
        })
    
    def get_balance_net(self,net,gdp_net,delivery_net):
        return net - (gdp_net + delivery_net)
        
    def get_gdp_net(self,grp):
        sql='''
            SELECT sum(init_qty) init_qty
            FROM
                stock_move 
            WHERE grp_id = %s
            and state ='done'
        '''%(grp)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return i['init_qty'] or 0.0
        return 0
    
    def get_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def get_maize(self,maize_yn):
        if maize_yn:
            return'Y'
        else:
            return 'N'
    def get_total(self):
        return self.total /1000
    def get_line(self):
        self.get_header()
        sql ='''
            SELECT id FROM lot_kcs 
            where contract_id = %s
            order by name
        '''%(self.s_contract)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            return self.pool.get('lot.kcs').browse(self.cr,self.uid,i['id'])
    
    def get_lot_allocation(self):
        self.get_header()
        res = []
        sql ='''
            SELECT id FROM lot_stack_allocation 
            where contract_id = %s
        '''%(self.s_contract)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            res.append(i['id'])
        return self.pool.get('lot.stack.allocation').browse(self.cr,self.uid,res)
    
    def get_aver(self):
        self.get_header()
        total_qty =0
        mc_on_despatch = stick= stone =mold = immature = eaten = burned = belowsc12 = screen13 = screen16 = screen18 = cherry = brown = broken = black = fm = mc = 0;
        
        res = []
        val = []
        sql ='''
            SELECT id FROM lot_stack_allocation 
            where contract_id = %s
        '''%(self.s_contract)
        self.cr.execute(sql)
        for i in self.cr.dictfetchall():
            res.append(i['id'])
        for j in self.pool.get('lot.stack.allocation').browse(self.cr,self.uid,res):
            total_qty += j.quantity
            mc += j.quantity * j.grp_id.kcs_line[0].mc
            fm += j.quantity * j.grp_id.kcs_line[0].fm
            black += j.quantity * j.grp_id.kcs_line[0].black
            broken += j.quantity * j.grp_id.kcs_line[0].broken
            brown += j.quantity * j.grp_id.kcs_line[0].brown
            cherry += j.quantity * j.grp_id.kcs_line[0].cherry
            screen18 += j.quantity * j.grp_id.kcs_line[0].screen18
            screen16 += j.quantity * j.grp_id.kcs_line[0].screen16
            screen13 += j.quantity * j.grp_id.kcs_line[0].screen13
            belowsc12 += j.quantity * j.grp_id.kcs_line[0].belowsc12
            burned += j.quantity * j.grp_id.kcs_line[0].burned
            eaten += j.quantity * j.grp_id.kcs_line[0].eaten
            immature += j.quantity * j.grp_id.kcs_line[0].immature
            mold += j.quantity * j.grp_id.kcs_line[0].mold
            stick += j.quantity * j.grp_id.kcs_line[0].stick_count
            stone += j.quantity * j.grp_id.kcs_line[0].stone_count
            mc_on_despatch += j.quantity * j.mc_on_despatch
        if total_qty ==0:
            return  val
        else:
            self.total =round(total_qty,0)
            val.append({
                    'total_qty':total_qty,
                    'mc':round(mc/total_qty,2),
                    'fm':round(fm/total_qty,2),
                    'black':round(black/total_qty,2),
                    'broken':round(broken/total_qty,2),
                    'brown':round(brown/total_qty,2),
                    'cherry':round(cherry/total_qty,2),
                    'screen18':round(screen18/total_qty,2),
                    'screen16':round(screen16/total_qty,2),
                    'screen13':round(screen13/total_qty,2),
                    'belowsc12':round(belowsc12/total_qty,2),
                    'burned':round(burned/total_qty,2),
                    'eaten':round(eaten/total_qty,2),
                    'immature':round(immature/total_qty,2),
                    'mold':round(mold/total_qty,2),
                    'stick':round(stick/total_qty,2),
                    'stone':round(stone/total_qty,2),
                    'mc_on_despatch':round(mc_on_despatch/total_qty,2),
                    })
            return val
            
        
    
    def get_objcontract(self):
        self.get_header()
        return self.pool.get('s.contract').browse(self.cr,self.uid,self.s_contract)
        
    def get_header(self):
        wizard_data = self.localcontext['data']['form']
        self.s_contract = wizard_data['s_contract'] and wizard_data['s_contract'][0] or False
        return True
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
