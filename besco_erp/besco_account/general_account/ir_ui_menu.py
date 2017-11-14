# -*- coding: utf-8 -*-
from openerp import api, tools
import openerp.modules
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import AccessError, UserError
from openerp import SUPERUSER_ID

class ir_ui_menu(osv.osv):
    _inherit = "ir.ui.menu"

    def init(self, cr):
        #Hide menu Discuss
#         cr.execute('''
#         DELETE FROM ir_ui_menu_group_rel WHERE menu_id in (select id from ir_ui_menu where parent_id IS NULL and name='Discuss');
#         ''')
        
        #THANH: Reorder Accounting Menus sequence
        cr.execute("select id from ir_ui_menu where parent_id IS NULL and name='Accounting'")
        parent_ids = [x[0] for x in cr.fetchall()]
        if len(parent_ids):
            cr.execute('''
            UPDATE ir_ui_menu SET sequence=10 WHERE parent_id = %(p_id)s and name='Dashboard';                
            UPDATE ir_ui_menu SET sequence=20 WHERE parent_id = %(p_id)s and name='Sales';
            UPDATE ir_ui_menu SET sequence=30 WHERE parent_id = %(p_id)s and name='Purchases';
            UPDATE ir_ui_menu SET sequence=50 WHERE parent_id = %(p_id)s and name='Stock Account';
            UPDATE ir_ui_menu SET sequence=60 WHERE parent_id = %(p_id)s and name='Adviser';
            UPDATE ir_ui_menu SET sequence=100 WHERE parent_id = %(p_id)s and name='Reporting';
            UPDATE ir_ui_menu SET sequence=120 WHERE parent_id = %(p_id)s and name='Configuration';
            '''%({'p_id': parent_ids[0]}))
        
        return True