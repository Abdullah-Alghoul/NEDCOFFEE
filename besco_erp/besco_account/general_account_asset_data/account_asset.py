# -*- encoding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF

import xlrd
from openerp import SUPERUSER_ID

import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_account_asset_data'))

class AccountAssetCategory(models.Model):
    _inherit = 'account.asset.category'

    def init(self, cr):
        wb = xlrd.open_workbook(base_path + '/general_account_asset_data/data/asset_categories.xls')
        wb.sheet_names()
        sh = wb.sheet_by_index(0)
        
        company_ids = self.pool.get('res.company').search(cr, SUPERUSER_ID, [])
        if company_ids:
            i = -1
            for rownum in range(sh.nrows):
                i += 1
                row_values = sh.row_values(rownum)
                
                if i == 0:
                    continue
                
                for company_id in company_ids:
                    try:
                        cr.execute('''
                        INSERT INTO account_asset_category(name,
                        journal_id,
                        account_asset_id,
                        account_depreciation_id,
                        method_time,method,method_number,prorata,method_period,company_id,type,active)
                        
                        SELECT '%s',
                        coalesce((select id from account_journal where name='%s'),null),
                        coalesce((select id from account_account where code='%s'),null),
                        coalesce((select id from account_account where code='%s'),null),
                        'number','linear',%s,true,1,%s,'purchase',true
                        
                        WHERE not exists (select id from account_asset_category where account_asset_id=(select id from account_account where code='%s'))
                        '''%(row_values[0],
                             row_values[1],
                             row_values[2],
                             row_values[3],
                             row_values[4],
                             company_id,
                             row_values[2],
                             ))
                        cr.execute('commit;')
                    except Exception, e:
                        continue
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
