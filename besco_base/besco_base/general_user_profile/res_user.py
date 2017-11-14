# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

import pytz
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class users(osv.osv):
    _inherit = "res.users"
    _columns = {
        'profile_id': fields.many2one('profile', string='Profile', required=False, readonly=False, help='The profile of the user. The admin should have no profile.'),
        'profile_ids': fields.many2many('profile', 'res_users_profiles_rel', 'user_id', 'profile', string='Profiles', 
                                        required=False, readonly=False, help='The profile of the user. The admin should have no profile.'),
                
#        'groups_id': fields.many2many('res.groups', 'res_groups_users_rel', 'uid', 'gid', 'Groups', readonly=True),
    }
    
    def create(self, cr, uid, vals, context=None):         
        new_id = super(users, self).create(cr, uid, vals, context)
        self.pool.get('profile').update_groups(cr, uid, [new_id])
        return new_id
    
    def update_profile(self, cr, uid, ids, context=None):
        self.pool.get('profile').update_groups(cr, uid, ids)   
        return True
    
    def _get_user_tz(self, cr, uid):
        property_pool = self.pool.get('admin.property')
        user = self.read(cr, uid, [uid], ['tz'])[0]
        tz = False
        if user['tz']:
            return user['tz']
        else:
            property_obj = property_pool._get_project_property_by_name(cr, uid, 'vietnamese_timezone') or None
            if property_obj:
                return property_obj.value
        if not tz:
            raise osv.except_osv(_('Invalid Timezone!'), _('The Timezone is not correct set. You should check User Timezone or Property Timezone first!'))
    
    def get_diff_hours_usertz_vs_utctz(self, cr, uid):
        user_timezone = self._get_user_tz(cr, uid)
        diff_hours = 0
        if user_timezone:
            utc = pytz.timezone('UTC')
            today = datetime.now()
            utc_today = utc.localize(today, is_dst=False)
            context_today = utc_today.astimezone(pytz.timezone(user_timezone)).replace(tzinfo=None)
            utc_today = utc.localize(today, is_dst=False).replace(tzinfo=None)
            diff_hours = (context_today - utc_today).seconds / 3600
        return diff_hours
            
    def _convert_user_datetime(self, cr, uid, datetime_value):
        local_tz = pytz.timezone(self._get_user_tz(cr, uid))
        datetime_value = datetime.strptime(datetime_value, DEFAULT_SERVER_DATETIME_FORMAT)
        datetime_value_utc = pytz.utc.localize(datetime_value)
        local_time = datetime_value_utc.astimezone(local_tz)
        return local_time
    
    def get_hours_difference(self, cr, uid):
        diff_hours = 0.0
        local_tz = self._get_user_tz(cr, uid)
        utc = pytz.timezone('UTC')
        today = datetime.now()
        utc_today = utc.localize(today, is_dst=False)
        context_today = utc_today.astimezone(pytz.timezone(local_tz)).replace(tzinfo=None)
        utc_today = utc.localize(today, is_dst=False).replace(tzinfo=None)
        diff_hours = (context_today - utc_today).seconds / 3600
        return diff_hours
    
    def _convert_date_to_utc(self, cr, uid, date_value):
        diff_hours = self.get_hours_difference(cr, uid)
        datetime_value = datetime.strptime(date_value,DEFAULT_SERVER_DATE_FORMAT)
        datetime_value = datetime_value - timedelta(hours=diff_hours)
        return datetime_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    
    def _convert_datetime_to_utc(self, cr, uid, date_value):
        diff_hours = self.get_hours_difference(cr, uid)
        datetime_value = datetime.strptime(date_value,DEFAULT_SERVER_DATETIME_FORMAT)
        datetime_value = datetime_value - timedelta(hours=diff_hours)
        return datetime_value.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    
users()

class groups(osv.osv):
    _inherit = "res.groups"
    _columns = {
        'profiles_ids': fields.many2many('profile', 'profiles_groups_rel', 'group_id', 'profile_id', string='Profiles', required=False, readonly=False),
    }
    
#    def write(self, cr, uid, ids, values, context=None):         
#        super(groups, self).write(cr, uid, ids, values, context)
#        return self.pool.get('profile').update_groups(cr, uid)
    
groups()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
