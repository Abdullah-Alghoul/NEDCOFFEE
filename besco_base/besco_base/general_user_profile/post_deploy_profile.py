from mx.DateTime import *
from datetime import date
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pooler
from osv import osv, fields
from tools.translate import _


class post_user_profile(osv.osv):
    _name = "post.user.profile"
    _description = "Post Deployment"
    _auto = False
    
    def start(self, cr, uid):
        self.update_all_sub_menu_administration(cr, uid)  
        self.update_shortcut_for_admin(cr, uid)
        return True
    
    def update_all_sub_menu_administration(self, cr, uid):
        '''
        Ticket 2942.
         * Add groups "Administration / Access Rights" and "Administration / Configuration" into 
             all submenus of Administration
         * Add groups "Administration / User" into menu "Administration / Users / User"
        '''
        menu_obj = self.pool.get('ir.ui.menu')
        group_obj = self.pool.get('res.groups')
        group_access_right = group_obj.search(cr, uid, [('name', '=', 'Administration / Access Rights')])
        group_configuration = group_obj.search(cr, uid, [('name', '=', 'Administration / Configuration')])
        group_configure_user = group_obj.search(cr, uid, [('name', '=', 'Administration / User')])
        admin_menu = menu_obj.search(cr, uid, [('name', '=', 'Administration')])
        if group_configure_user:
            menu_obj.write(cr, uid, admin_menu, {'groups_id': [(4, group_configure_user[0])]})
        list_administation_children_ids = menu_obj.search(cr, uid, [('parent_id', '=', 'Administration')])
                      
        if list_administation_children_ids:
            if group_access_right:
                menu_obj.write(cr, uid, list_administation_children_ids, {'groups_id': [(4, group_access_right[0])]})
            if group_configuration:
                menu_obj.write(cr, uid, list_administation_children_ids, {'groups_id': [(4, group_configuration[0])]})
        
        profile_menu = menu_obj.search(cr, uid, [('parent_id', '=', 'Users'),
                                                ('name', '=', 'Profiles')])
        if profile_menu:
            if group_access_right:
                menu_obj.write(cr, uid, profile_menu, {'groups_id': [(4, group_access_right[0])]})
            if group_configuration:
                menu_obj.write(cr, uid, profile_menu, {'groups_id': [(4, group_configuration[0])]})  
        
        list_user_menu_ids = menu_obj.search(cr, uid, [('parent_id', '=', 'Administration'),
                                                       ('name', '=', 'Users')]) or []
        menu_user = menu_obj.search(cr, uid, [('parent_id', '=', 'Users'),
                                                       ('name', '=', 'Users')]) or []
                                
        if group_configure_user:
            if list_user_menu_ids:                    
                menu_obj.write(cr, uid, list_user_menu_ids, {'groups_id': [(4, group_configure_user[0])]})
            if menu_user:                    
                menu_obj.write(cr, uid, menu_user, {'groups_id': [(4, group_configure_user[0])]})
        return True
    
    
    def update_shortcut_for_admin(self, cr, uid):
        '''
        Ticket 3122.
         
        '''        
        shortcut_obj = self.pool.get('ir.ui.view_sc')
        shorcut_names = ['Modules', 'Companies', 'Users', 'Profiles', 'Project Properties']
        admin_user = self.pool.get('res.users').search(cr, uid, [('login', '=', 'admin')]) or False
        if admin_user:
            admin_user = admin_user[0]
                
        for shortcut_name in shorcut_names:
            shortcut_res = shortcut_obj.search(cr, uid, [('user_id', '=', admin_user),
                                                         ('name', '=', shortcut_name)])
            if shortcut_res:
                continue
            search_criteria = [('name', '=', shortcut_name)]
            if shortcut_name in ['Modules', 'Companies', 'Users']:
                search_criteria.append(('parent_id.name', '=', shortcut_name))
            menu_ids = self.pool.get('ir.ui.menu').search(cr, uid, search_criteria)
            if menu_ids:
                data = {
                    'user_id' : admin_user,
                    'res_id' : menu_ids[0],
                    'resource' : 'ir.ui.menu',
                    'name' : shortcut_name,
                }
                shortcut_obj.create(cr, uid, data)
        print 'Finish updating the shortcuts for Admin user'
        return True

    
post_user_profile()