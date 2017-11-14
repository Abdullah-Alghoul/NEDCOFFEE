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
        pool = pooler.get_pool(self.cr.dbname)
        user = pool.get('res.users').browse(cr, uid, uid)
        self.local = True
        self.localcontext.update({
            'local': self._local,
            'set_local': self._set_local,
            'user': user,
            'get_vietname_date':self.get_vietname_date,
            'get_partner_address': self.get_partner_address,
            'get_taxes': self.get_taxes,
            'get_translate': self.get_translate,
            'get_partner_name': self.get_partner_name,
        })
    
    def get_partner_name(self, order):
        name = self.get_translate('res.partner', 'name', order.partner_id.id, order.partner_id.name)
        title = ''
        if order.partner_id.title:
            title = self.get_translate('res.partner.title', 'name', order.partner_id.title.id, order.partner_id.title.name)
        if title and self.local == 'en_US':
            name = name + ' ' + title
        if title and self.local == 'vi_VN':
            name = title + ' ' + name
        return name
        
    def get_translate(self, object, field, res_id, from_value):
        to_value = from_value
        language_code = self.local
        if object and field and from_value and language_code:
            translate_obj = pooler.get_pool(self.cr.dbname).get('ir.translation')
            lang = ('lang','=',language_code)
            type = ('type','=','model')
            name = ('name','=',object + ',' + field)
            source_id = ('res_id','=', res_id)
            translate_ids = translate_obj.search(self.cr, self.uid, [lang,type,name,source_id])
            if translate_ids:
                to_value = translate_obj.browse(self.cr, self.uid, translate_ids[0]).value
        return to_value

    def _set_local(self, value):
        self.local = value
        
    def _local(self):
        return self.local
    
    def get_taxes(self, taxes):
        res = taxes and str(taxes[0].amount * 100) or ''
        if taxes:
            del(taxes[0])
        for tax in taxes:
            res += '\n' + str(tax.amount * 100)
        return res
    
    def get_partner_address(self, order):
        address = ''
        if order.partner_order_id:
            address += self.get_translate('res.partner.address', 'street', order.partner_order_id.id, order.partner_order_id.street) or ''
            address += order.partner_order_id.district_id and ', ' + self.get_translate('res.district', 'name', order.partner_order_id.district_id.id, order.partner_order_id.district_id.name) or ''
            address += order.partner_order_id.state_id and ', ' + self.get_translate('res.country.state', 'name', order.partner_order_id.state_id.id, order.partner_order_id.state_id.name) or ''
            address += order.partner_order_id.country_id and ', ' + self.get_translate('res.country', 'name', order.partner_order_id.country_id.id, order.partner_order_id.country_id.name) or ''
        return address
    
    def get_vietname_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)        
        return date.strftime('%d-%m-%Y')
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
