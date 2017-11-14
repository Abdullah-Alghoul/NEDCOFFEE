# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID

class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'
    
    def init(self, cr):
        mod_obj = self.pool.get('ir.model.data')
        uid = SUPERUSER_ID
        #THANH: Hide these menus by adding group no_body to the menu
        dummy, group_nobody_id = tuple(mod_obj.get_object_reference(cr, uid, 'general_base', "group_nobody"))
        if group_nobody_id:
            menu_ids = []
            #MENU: Schedule
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', "menu_stock_sched"))
            if menu_id:
                menu_ids.append(menu_id)
            #MENU: Procurement Exceptions
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', "menu_stock_procurement_action"))
            if menu_id:
                menu_ids.append(menu_id)
            #MENU: Operations
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', "menu_stock_warehouse_mgmt"))
            if menu_id:
                menu_ids.append(menu_id)
            if len(menu_ids):
                self.write(cr, uid, menu_ids, {'groups_id': [(6,0,[group_nobody_id])]})
        return True