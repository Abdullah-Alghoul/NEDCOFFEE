# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.osv import expression
from openerp.exceptions import UserError

import xlrd
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_base'))

class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            #THANH: filter bank account
            domain = ['|', '|', 
                        ('bank_id.name', operator, name),
                        ('bank_id.bic', operator, name), 
                        ('acc_number', operator, name)]
        accounts = self.search(domain + args, limit=limit)
        return accounts.name_get()
    
    @api.multi
    def name_get(self):
        result = []
        for bank in self:
            name = bank.acc_number
            if bank.bank_id:
                name +=  ' - ' + _(bank.bank_id.name)
            result.append((bank.id, name))
        return result

class Bank(models.Model):
    _inherit = 'res.bank'

    @api.one
    @api.constrains('bic')
    def _check_bic(self):
        #THANH: check duplicate Bank Code (BIC)
        if self.bic:
            e_ids = self.search([('id','!=',self.id),('bic','=',self.bic)])
            if len(e_ids):
                raise UserError(("BIC '%s' is already exist for Bank '%s'!")%(self.bic, self.name))
        
    def init(self, cr):
        cr.execute('select bank_imported from res_company where bank_imported=True limit 1')
        res = cr.fetchone()
        bank_imported = False
        if res and res[0]:
            bank_imported = True
        
        if not bank_imported:
            wb = xlrd.open_workbook(base_path + '/general_base/data/res_bank.xls')
            wb.sheet_names()
            sh = wb.sheet_by_index(0)
            
            i = -1
            for rownum in range(sh.nrows):
                i += 1
                row_values = sh.row_values(rownum)
                
                if i == 0:
                    continue
                
                try:
                    cr.execute('''
                    BEGIN;
                    
                    INSERT INTO res_bank(name,bic,active,country)
                    SELECT '%s', '%s', True, (select id from res_country where code='VN')
                    WHERE not exists (select id from res_bank where name='%s' or bic='%s');
                    
                    COMMIT;
                    '''%(row_values[0],
                         row_values[1],
                         row_values[0],
                         row_values[1]))
                except Exception, e:
                    continue
            cr.execute('''
                BEGIN;
                update res_company set bank_imported=True;
                COMMIT;
                ''')
        return True