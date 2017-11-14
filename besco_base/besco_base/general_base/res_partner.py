# -*- coding: utf-8 -*-
import openerp
from openerp import tools, api
from openerp.osv import osv, fields
from openerp.osv.expression import get_unaccent_wrapper
from openerp.tools.translate import _
from openerp.exceptions import UserError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

from xlrd import open_workbook
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_base'))

class res_partner(osv.Model):
    _inherit = "res.partner"
    
    def simple_vat_check(self, cr, uid, country_code, vat_number, context=None):
        '''
        Check the VAT number depending of the country.
        http://sima-pc.com/nif.php
        '''
#         if not ustr(country_code).encode('utf-8').isalpha():
#             return False
#         check_func_name = 'check_vat_' + country_code
#         check_func = getattr(self, check_func_name, None) or \
#                         getattr(vatnumber, check_func_name, None)
#         if not check_func:
#             # No VAT validation available, default to check that the country code exists
#             if country_code.upper() == 'EU':
#                 # Foreign companies that trade with non-enterprises in the EU
#                 # may have a VATIN starting with "EU" instead of a country code.
#                 return True
#             res_country = self.pool.get('res.country')
#             return bool(res_country.search(cr, uid, [('code', '=ilike', country_code)], context=context))
#         return check_func(vat_number)
        return True
    
    _columns = {
    }
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.shortname or record.name
            if record.partner_code:
                name = "[%s] %s" % (record.partner_code, name)
            if record.parent_id:
                parent_name = self.name_get(cr, uid, [record.parent_id.id], context)
                name = "%s, %s" % (parent_name[0][1], name)
            res.append((record.id, name))
        return res
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        domain = []
        if name:
            #THANH: filter both partner name and parent name
            domain = ['|', ('name', operator, name), ('parent_id.name', operator, name)]
        ids = self.search(cr, user, domain + args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        #Thanh: Search ten khach hang, ma noi bo, ma so thue, email
        operator = False
        value = False
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'name' and args[pos][1] in ('like', 'ilike', '=') and args[pos][2]:
                operator = args[pos][1]
                value = args[pos][2]
                args.pop(pos)
                break
            pos += 1
            
        #Thanh: Extend search for Internal Partner (usually Employee)
        if context.get('filter_internal', False):
            user = self.pool.get('res.users').browse(cr, uid, uid)
            if user.company_id and user.company_id.partner_id:
                arg = ('parent_id','=',user.company_id.partner_id.id)
                args.append(arg)
                
        #THANH: Suggest search these field
        if operator:
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append(['name', operator, value])
            args.append(['ref', operator, value])
            args.append(['partner_code', operator, value])
            args.append(['shortname', operator, value])
            args.append(['vat', operator, value])
            args.append(['identification_id', operator, value])
            args.append(['email', operator, value])
            args.append(['phone', operator, value])
            args.append(['mobile', operator, value])
        return super(res_partner, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
     
    def create(self, cr, uid, vals, context=None):
        system_sequence_obj = self.pool.get('system.sequence')
        #THANH: No need to seperate customer supplier, contact, only one code for all types
        code = system_sequence_obj.get_current_sequence(cr, 'partner_code')
        vals.update({'ref': code})
        
#         if not vals.get('parent_id',False) and vals.get('customer',False) and not vals.get('supplier',False):
#             code = system_sequence_obj.get_current_sequence(cr, 'customer_code')
#             vals.update({'ref': code})
#         
#         if not vals.get('parent_id',False) and not vals.get('customer',False) and vals.get('supplier',False):
#             code = system_sequence_obj.get_current_sequence(cr, 'supplier_code')
#             vals.update({'ref': code})
#         
#         if vals.get('parent_id',False):
#             code = system_sequence_obj.get_current_sequence(cr, 'contact_code')
#             vals.update({'ref': code})
            
        return super(res_partner, self).create(cr, uid, vals, context=context)
    
class res_district(osv.osv):
    _description = 'District'
    _name = "res.district"
    _order = 'name'
    _columns = {
        'name': fields.char('Name', size=64, select=True, required=True, translate=True),
        'state_id': fields.many2one('res.country.state', 'Province', select=True, required=True),
        'active':fields.boolean("Active")
        }
        
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        if context.get('state_id'):
            arg = ('state_id', '=', context.get('state_id'))
            args.append(arg)
        return super(res_district, self).search(cr, uid, args, offset, limit, order, context=context, count=count) 
    
#     def init(self, cr):
#         cr.execute('select district_imported from res_company where district_imported=True limit 1')
#         res = cr.fetchone()
#         district_imported = False
#         if res and res[0]:
#             district_imported = True
#         
#         if not district_imported:
#             state_obj = self.pool.get('res.country.state')
#             wb = open_workbook(base_path + '/general_base/data/QuanHuyen.xls')
#             for s in wb.sheets():
#                 if (s.name =='Sheet1'):
#                     for row in range(1,s.nrows):
#                         val0 = s.cell(row,0).value
#                         val1 = s.cell(row,1).value
#                         state_ids = state_obj.search(cr, 1, [('name','=',val1)])
#                         if state_ids:
#                             print 'State 1 ' + str(state_ids)
#                             quan_huyen_ids = self.search(cr, 1, [('name','=',val0),('state_id','in',state_ids)])
#                             if not quan_huyen_ids:
#                                 print 'State 2 ' + str(state_ids)
#                                 self.create(cr, 1, {'name': val0,'state_id':state_ids[0]})
#             cr.execute('update res_company set district_imported=True')
            
                            
class CountryState(osv.osv):
    _inherit = 'res.country.state'
    _columns = {
        'districts': fields.one2many('res.district', 'state_id', 'Districts'),

    }
    
#     def init(self, cr):
#         cr.execute('select state_imported from res_company where state_imported=True limit 1')
#         res = cr.fetchone()
#         state_imported = False
#         if res and res[0]:
#             state_imported = True
#         
#         if not state_imported:
#             country_obj = self.pool.get('res.country')
#             wb = open_workbook(base_path + '/general_base/data/TinhTP.xls')
#             for s in wb.sheets():
#                 if (s.name =='Sheet1'):
#                     for row in range(1,s.nrows):
#                         val0 = s.cell(row,0).value
#                         val1 = s.cell(row,1).value
#                         val2 = s.cell(row,2).value
#                         country_ids = country_obj.search(cr, 1, [('code','=',val2)])
#                         if country_ids:
#                             state_ids = self.search(cr, 1, [('name','=',val1),('code','=',val0),('country_id','in',country_ids)])
#                             if not state_ids:
#                                 self.create(cr, 1, {'name': val1,'code':val0,'country_id':country_ids[0]})
#             cr.execute('update res_company set state_imported=True')
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
