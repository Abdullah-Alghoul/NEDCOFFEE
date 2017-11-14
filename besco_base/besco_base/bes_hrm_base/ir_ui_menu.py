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
        mod_obj = self.pool.get('ir.model.data')
        menu_obj = self.pool.get('ir.ui.menu')
        uid = SUPERUSER_ID
        
        try:
#             dummy, parent_id = tuple(mod_obj.get_object_reference(cr, uid, 'bes_hrm_base', "menu_base_hrm"))
#             if parent_id:
                
#             #Menu Recruitment
#             dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_recruitment', "menu_hr_recruitment_root"))
#             if menu_id:
#                 menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
#                                                     'sequence':'156'})
                
            #Menu Employee
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr', "menu_hr_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'160'})
            
            #Menu Leaves
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_holidays', "menu_hr_holidays_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'165'})
            
            #Menu Attendance
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_attendance', "menu_hr_attendance_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'166'})
            
            #Menu Timesheet
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_attendance', "timesheet_menu_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'167'})
            
            #Menu Payroll
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_payroll', "menu_hr_payroll_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'168'})
                
                
            #Menu Equipments
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_equipment', "menu_equipment_title"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'169'})
                
            #Menu Recruitment
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_recruitment', "menu_hr_recruitment_root"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'180'})
            
            
            #Menu Appraisal
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'hr_evaluation', "menu_hr_appraisal"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'171'})
           
            #Menu Surveys
            dummy, menu_id = tuple(mod_obj.get_object_reference(cr, uid, 'survey', "menu_survey_form"))
            if menu_id:
                menu_obj.write(cr, uid, [menu_id], {'parent_id': False,
                                                    'sequence':'175'})
            
        except Exception, e:
            pass