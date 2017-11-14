# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from osv import osv, fields
from tools.translate import _
DATETIME_FORMAT = "%Y-%m-%d"
DATE_FORMAT = "%Y-%m-%d"
import time
from datetime import datetime

class asset_depreciation_confirmation_wizard(osv.osv_memory):
    _inherit = "asset.depreciation.confirmation.wizard"
    _columns = {
       'date': fields.date('Date',required=True), 
       'period_id': fields.many2one('account.period', 'Period', required=True, domain=[('state','=','draft')], help="Choose the period for which you want to automatically post the depreciation lines of running assets")
    }
    
    
    def default_get(self, cr, uid, fields, context=None):
        res = {}
        period_obj = self.pool.get('account.period')
        depreciation_obj = self.pool.get('account.asset.depreciation.line')
        
        if 'active_ids' in context and  context['active_ids']:
            depreciation_ids = depreciation_obj.browse(cr,uid,context['active_ids'][0])
            if depreciation_ids:
                res.update({'date':depreciation_ids.depreciation_date}) 
        return res
    
    def onchange_date(self,cr,uid,ids,date,period_id):
        value ={}
        warning ={}
        period_id_after = False
        period_ids = self.pool.get('account.period').search(cr,uid,[('date_start','<=',date),('date_stop','>=',date),('state','=','draft')])
        if period_ids:
            period_id_after = self.pool.get('account.period').browse(cr,uid,period_ids[0])
        
        if period_id_after:
            value.update({'period_id':period_id_after.id}) 
        else:
            value.update({'date':False})
            warning = {
               'title': _('Period Warning!'),
               'message' : _('You must open Period')
           }
        return {'value': value, 'warning': warning} 
    
    def asset_compute(self, cr, uid, ids, context):
        ass_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        asset_ids = ass_obj.search(cr, uid, [('state','=','open')], context=context)
        data = self.browse(cr, uid, ids, context=context)
        period_id = data[0].period_id.id
        period = period_obj.browse(cr, uid, period_id, context=context)
        
        date = data and data[0].date
        if period:
            if (date >= period.date_start and date <= period.date_stop)==False:
                raise osv.except_osv(_('Error !'), _('You must choose date between start_date and end_date in period'))
#             sql ='''
#             select '%s' between '%s' and '%s' condition
#             ''' %(date,period.date_start,period.date_stop)
#             cr.execute(sql)
#             res = cr.dictfetchone()
#             if res['condition'] == False:
#                 raise osv.except_osv(_('Error !'), _('You must choose date between start_date and end_date in period'))
        
#         date_now = time.strftime(DATE_FORMAT)
#         date_now = datetime.strptime(date_now, DATE_FORMAT)
#         month_now = int(date_now.strftime('%m'))
#         year_now = int(date_now.strftime('%Y'))
#         
#         date_compare = datetime.strptime(date, DATE_FORMAT)
#         month_compare = int(date_compare.strftime('%m'))
#         year_compare =  int(date_compare.strftime('%Y'))
#         
#         if (month_now >= month_compare and year_now >= year_compare)==False:
#             raise osv.except_osv(_('Error !'), _('Period must smaller Current Date'))
        
        
#         sql ='''
#             select '%s' >= '%s' and '%s' >= '%s' condition
#         ''' %(month_now,month_compare,year_now,year_compare)
#         cr.execute(sql)
#         res = cr.dictfetchone()
#         if res['condition'] == False:
#             
        
        context.update({'date':date})
        if 'asset_type' in context and context['asset_type'] == 'create_move':
            
            active_ids = context.get('active_ids') 
            depreciation_obj = self.pool.get('account.asset.depreciation.line')
            depreciation_ids = depreciation_obj.search(cr, uid, [('id', 'in', active_ids), ('depreciation_date', '<=', period.date_stop), ('depreciation_date', '>=', period.date_start), ('move_check', '=', False)], context=context)
            created_move_ids = self.pool.get('account.asset.depreciation.line').create_move(cr,uid,depreciation_ids,context)
            
        else:
            created_move_ids = ass_obj._compute_entries(cr, uid, asset_ids, period_id, context=context)
        return {
            'name': _('Created Asset Moves'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'domain': "[('id','in',["+','.join(map(str,created_move_ids))+"])]",
            'type': 'ir.actions.act_window',
        }
asset_depreciation_confirmation_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
