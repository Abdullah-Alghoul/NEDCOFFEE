# -*- coding: utf-8 -*-
from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models, _
from openerp import SUPERUSER_ID

from openerp.exceptions import AccessError, UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _inherit = 'account.account'

    name_eng = fields.Char(string="Name Eng")
    
    def init(self, cr):
        ir_values_obj = self.pool['ir.values']
        PropertyObj = self.pool['ir.property']
        company_ids = self.pool.get('res.company').search(cr, SUPERUSER_ID, [])
            
        #THANH:  Set default tax 10% for all product (VAT IN, VAT OUT)
        taxes_ids = self.pool['account.tax'].search(cr, SUPERUSER_ID, [('type_tax_use', '=', 'sale'), ('transaction_type', '=', 'none'), ('amount', '=', 10.0)])
        if len(taxes_ids):
            search_criteria = [
                ('key', '=', 'default'),
                ('key2', '=', False),
                ('model', '=', 'product.template'),
                ('name', '=', 'taxes_id'),
                ('user_id', '=', False)
                
                ]
            res_ids = ir_values_obj.search(cr, SUPERUSER_ID, search_criteria)
            if not len(res_ids):
                ir_values_obj.set_default(cr, SUPERUSER_ID, 'product.template', "taxes_id", taxes_ids, for_all_users=True, company_id=True)
        
        taxes_ids = self.pool['account.tax'].search(cr, SUPERUSER_ID, [('type_tax_use', '=', 'purchase'), ('transaction_type', '=', 'none'), ('amount', '=', 0.0)])
        if len(taxes_ids):
            search_criteria = [
                ('key', '=', 'default'),
                ('key2', '=', False),
                ('model', '=', 'product.template'),
                ('name', '=', 'supplier_taxes_id'),
                ('user_id', '=', False),
                ]
            res_ids = ir_values_obj.search(cr, SUPERUSER_ID, search_criteria)
            if not len(res_ids):
                ir_values_obj.set_default(cr, SUPERUSER_ID, 'product.template', "supplier_taxes_id", taxes_ids, for_all_users=True, company_id=True)
        
        #THANH:  Set default receivable and payable account for partner
        todo_list = [
            ('property_account_receivable_id', 'res.partner', 'account.account', '131101'),
            ('property_account_payable_id', 'res.partner', 'account.account', '331101'),
            ('property_customer_advance_acc_id', 'res.partner', 'account.account', '131103'),
            ('property_vendor_advance_acc_id', 'res.partner', 'account.account', '331103'),
#             ('property_account_expense_categ_id', 'product.category', 'account.account'),
#             ('property_account_income_categ_id', 'product.category', 'account.account'),
#             ('property_account_expense_id', 'product.template', 'account.account'),
#             ('property_account_income_id', 'product.template', 'account.account'),
        ]
        for company_id in company_ids:
            for record in todo_list:
                account_ids = self.pool['account.account'].search(cr, SUPERUSER_ID, [('code', '=', record[3]), ('company_id', '=', company_id)])
                if len(account_ids):
                    value = 'account.account,' + str(account_ids[0])
                    if value:
                        field_id = self.pool['ir.model.fields'].search(cr, SUPERUSER_ID, [('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                        vals = {
                            'name': record[0],
                            'company_id': company_id,
                            'fields_id': field_id[0],
                            'value': value,
                        }
                        properties = PropertyObj.search(cr, SUPERUSER_ID, [('name', '=', record[0]), ('company_id', '=', company_id)])
                        if len(properties):
                            #the property exist: modify it
                            PropertyObj.write(cr, SUPERUSER_ID, properties, vals)
                        else:
                            #create the property
                            PropertyObj.create(cr, SUPERUSER_ID, vals)
        return True