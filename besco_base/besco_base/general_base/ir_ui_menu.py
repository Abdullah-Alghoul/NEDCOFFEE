# -*- coding: utf-8 -*-
from difflib import get_close_matches
import logging

from openerp import api, tools
import openerp.modules
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import AccessError, UserError
from openerp import SUPERUSER_ID

_logger = logging.getLogger(__name__)

class ir_module_module(osv.osv):
    _inherit = "ir.module.module"
    _columns = {
        'overwrite': fields.boolean('Overwrite'),
    }
    
class ir_translation(osv.osv):
    _inherit = "ir.translation"
    
    #THANH: Check module allows overwrite translation
    def load_module_terms(self, cr, modules, langs, context=None):
        context = dict(context or {}) # local copy
        ir_module = self.pool.get('ir.module.module')
        for module_name in modules:
            modpath = openerp.modules.get_module_path(module_name)
            if not modpath:
                continue
            
            #THANH: Check module allows overwrite translation
            module_ids = ir_module.search(cr, SUPERUSER_ID, [('name','=',module_name)])
            if len(module_ids):
                this_module = ir_module.browse(cr, SUPERUSER_ID, module_ids[0])
                if this_module.overwrite:
                    context.update({'overwrite': True})
            #THANH: Check module allows overwrite translation
            
            for lang in langs:
                lang_code = tools.get_iso_codes(lang)
                base_lang_code = None
                if '_' in lang_code:
                    base_lang_code = lang_code.split('_')[0]

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                if base_lang_code:
                    base_trans_file = openerp.modules.get_module_resource(module_name, 'i18n', base_lang_code + '.po')
                    if base_trans_file:
                        _logger.info('module %s: loading base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(cr, base_trans_file, lang, verbose=False, module_name=module_name, context=context)
                        context['overwrite'] = True # make sure the requested translation will override the base terms later

                    # i18n_extra folder is for additional translations handle manually (eg: for l10n_be)
                    base_trans_extra_file = openerp.modules.get_module_resource(module_name, 'i18n_extra', base_lang_code + '.po')
                    if base_trans_extra_file:
                        _logger.info('module %s: loading extra base translation file %s for language %s', module_name, base_lang_code, lang)
                        tools.trans_load(cr, base_trans_extra_file, lang, verbose=False, module_name=module_name, context=context)
                        context['overwrite'] = True # make sure the requested translation will override the base terms later

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                trans_file = openerp.modules.get_module_resource(module_name, 'i18n', lang_code + '.po')
                if trans_file:
                    _logger.info('module %s: loading translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(cr, trans_file, lang, verbose=False, module_name=module_name, context=context)
                elif lang_code != 'en_US':
                    _logger.info('module %s: no translation for language %s', module_name, lang_code)

                trans_extra_file = openerp.modules.get_module_resource(module_name, 'i18n_extra', lang_code + '.po')
                if trans_extra_file:
                    _logger.info('module %s: loading extra translation file (%s) for language %s', module_name, lang_code, lang)
                    tools.trans_load(cr, trans_extra_file, lang, verbose=False, module_name=module_name, context=context)
        return True
    
class ir_ui_menu(osv.osv):
    _inherit = "ir.ui.menu"

    def init(self, cr):
        mod_obj = self.pool.get('ir.model.data')
        uid = SUPERUSER_ID
        
        #THANH: Delete group from this menu, add new group User Dashboard from xml file, who belonging to this group will see Dashboard
        cr.execute('''
        DELETE FROM ir_ui_menu_group_rel WHERE menu_id in (select id from ir_ui_menu where parent_id IS NULL and name='Dashboards');
        ''')
        
        #THANH: Remove Technical Group from child menus of menu Contacts
        menu_ids = []
        dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'base', "menu_partner_title_contact"))
        if menu_id:
            menu_ids.append(menu_id)
        dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'base', "menu_partner_category_form"))
        if menu_id:
            menu_ids.append(menu_id)
        dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'base', "menu_config_bank_accounts"))
        if menu_id:
            menu_ids.append(menu_id)
        dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'base', "menu_localisation"))
        if menu_id:
            menu_ids.append(menu_id)
        
        if len(menu_ids):
            child_ids = self.search(cr, uid, [('id', 'child_of', menu_ids)])
            if len(child_ids):
                cr.execute('''
                DELETE FROM ir_ui_menu_group_rel
                WHERE menu_id in (%s)
                '''%(','.join(map(str, child_ids))))
            
        