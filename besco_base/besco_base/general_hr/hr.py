# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp import api, SUPERUSER_ID
from lxml import etree

from xlrd import open_workbook
import os
from openerp import modules
base_path = os.path.dirname(modules.get_module_path('general_hr'))

EDUCATION_SELECTION = [
    ('none', 'No Education'),
    ('primary', 'Primary School'),
    ('secondary', 'Secondary School'),
    ('diploma', 'Diploma'),
    ('degree1', 'First Degree'),
    ('masters', 'Masters Degree'),
    ('phd', 'PhD'),
]

class resource_calendar(osv.osv):
    _inherit = "resource.calendar"
    _columns = {
                'break_hours': fields.float('Break Hours (per day)'),
                'code': fields.char('Code', size=10, required=True, copy=False),
                'unskilled_worker': fields.boolean('Unskilled Worker')
            }
    
    _defaults = {
                'code': '/',
                'unskilled_worker': False
                }
    
    def _check_code(self, cr, uid, ids, context=None):
        for calendar in self.browse(cr, uid, ids, context=context):
            calendar_ids = self.search(cr, uid, [('code','=',calendar.code),('id','!=',calendar.id)])
            if len(calendar_ids) > 0:
                return False
        return True
    
    _constraints = [
        (_check_code, 'Shift Code must be unique per Company!', ['code']),
        ]
    
class resource_calendar_attendance(osv.osv):
    _inherit = "resource.calendar.attendance"
#     
#     def _check_dayofweek(self, cr, uid, ids, context=None):
#         for attendance in self.browse(cr, uid, ids, context=context):
#             attendance_ids = self.search(cr, uid, [('dayofweek','=',attendance.dayofweek)],('calendar_id','=',attendance.calendar_id.id),('id','!=',attendance.id))
#             if len(attendance_ids) > 0:
#                 return False
#         return True
#  
#     _constraints = [
#         (_check_dayofweek, "Day of week was exist on resource calendar.", ['dayofweek']),
#     ]
    
class hr_department(osv.osv):
    _inherit = "hr.department"
    
    # THANH: Add field parent_left and right for order purpose
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    
    _columns = {
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
    }
    
    @api.multi
    def name_get(self):
        def get_names(dep):
            """ Return the list [cat.name, cat.parent_id.name, ...] """
            res = [dep.name]
            return res
        res = [(dep.id, " / ".join(reversed(get_names(dep)))) for dep in self]
        return res
    
# Location    
class hr_work_location(osv.osv):
    _name = "hr.work.location"
    
    _columns = {
        'name': fields.char('Name', required=True),
        'state_id': fields.many2one('res.country.state', 'State'),
#         'parent_id': fields.many2one('hr.work.location', 'Parent', required=False),
        'manager_id': fields.many2one('hr.employee', 'Manager'),
    }

# Management Region 
class res_region (osv.osv):
    _name = 'res.region'
    
    _columns = {
        'name': fields.char('Region', required=True),
        'state_ids':  fields.many2many('res.country.state', 'work_location_region_res_cou_state_rel' 'work_location_region_id', 'state_id', string='State'),
    }
    
# Area
class res_area(osv.osv):
    _name = 'res.area'
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        if context.get('area_hr', False) and context.get('work_location_id'):
            arg = ('work_location_id', '=', context.get('work_location_id'))
            args.append(arg)
        return super(res_area, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    _columns = {
        'state_id': fields.many2one('res.country.state', 'State'),
        'region_id':  fields.many2one('res.region', 'Region'),
        'name': fields.many2one('res.area.define', 'Area', required=True, ondelete='cascade'),
        'district_ids':  fields.many2many('res.district', 'res_area_res_cou_district_rel' 'res_area_id', 'district_id', string='Districts'),
    }

class res_area_define(osv.osv):
    _name = 'res.area.define'
    
    _columns = {
        'name': fields.char('Name', required=True)
    }
    
class res_ward(osv.osv):
    _name = "res.ward"
    
    def init(self, cr):
        cr.execute('select ward_imported from res_ward where ward_imported=True limit 1')
        res = cr.fetchone()
        ward_imported = False
        if res and res[0]:
            ward_imported = True
        if not ward_imported:
            country_obj = self.pool.get('res.country')
            district_obj = self.pool.get('res.district')
            ward_obj = self.pool.get('res.ward')
            country_state_obj = self.pool.get('res.country.state')
            wb = open_workbook(base_path + '/general_hr/data/DiaChinh.xls')
            for s in wb.sheets():
                if (s.name =='Sheet1'):
                    for row in range(1,s.nrows):
                        code_state = s.cell(row,0).value
                        val_state = s.cell(row,1).value
                        code_dis = s.cell(row,2).value
                        val_dis = s.cell(row,3).value
                        code_ward = s.cell(row,4).value
                        val_ward = s.cell(row,5).value
                         
                        country_ids = country_obj.search(cr, 1, [('code','=','VN')])
                        state_ids = country_state_obj.search(cr, 1, [('name','=',val_state)])
                        if state_ids:
                            state_ids = state_ids[0]
                        if not state_ids:
                            state_ids = country_state_obj.create(cr, 1, {'name': val_state,'code':code_state,'country_id':country_ids[0]})

                        district_ids = district_obj.search(cr, 1, [('name','=',val_dis),('state_id','=',state_ids)])
                        if district_ids:
                            district_ids = district_ids[0]
                        if not district_ids:
                            district_ids = district_obj.create(cr, 1, {'name': val_dis,'code':code_dis,'state_id':state_ids})
                        
                        ward_ids = ward_obj.search(cr, 1, [('name','=',val_ward),('district_id','=',district_ids)])
                        if not ward_ids:
                            ward_ids = self.create(cr, 1, {'name': val_ward,'code':code_ward,'district_id':district_ids})
                            
            cr.execute('update res_ward set ward_imported=True')   
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        
        if context.get('district_id'):
            arg = ('district_id', '=', context.get('district_id'))
            args.append(arg)
                
        return super(res_ward, self).search(cr, uid, args, offset, limit, order, context=context, count=count) 
    
    _columns = {
        'name': fields.char('Name', required=True),
        'code': fields.char('Code'),
        'district_id': fields.many2one('res.district', 'District'),
        'ward_imported':  fields.boolean(string='Ward Imported'),
    }

class res_district(osv.osv):
    _inherit = "res.district"
     
    _columns = {
        'ward_ids': fields.one2many('res.ward', 'district_id', 'Wards'),
    }
    
class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    def _calculate_age(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for ee in self.browse(cr, uid, ids, context=context):
            if ee.birthday:
                dBday = datetime.strptime(ee.birthday, DEFAULT_SERVER_DATE_FORMAT).date()
                dToday = datetime.now().date()
                res[ee.id] = (dToday - dBday).days / 365
        return res
    
    def _cal_worked_years(self, cr, uid, ids, field_name, arg, context=None):
            res = {}
            for employee in self.browse(cr, uid, ids, context=context):
                res[employee.id] = 0
                if employee.joining_date:
                    Fromday = datetime.strptime(employee.joining_date, DEFAULT_SERVER_DATE_FORMAT).date()
                    Today = datetime.now().date()
                    res[employee.id] = round((Today - Fromday).days / 365.2425,1) #THANH: 365.2425 means The Gregorian Calendar, also known as the Western or Christian Calendar
            return res
        
    _columns = {
        'code': fields.char('Code', size=64, readonly=True),
        'scanner_code': fields.char('Scanner Code', size=128),
        
        'identification_date_issue': fields.date('Identification Date Issue'),
        'identification_place_issue': fields.char('Identification Place Issue', size=128),
        
        'degree_id': fields.many2one('hr.recruitment.degree', 'Degree'),
        'age': fields.function(_calculate_age, type='integer', method=True, string='Age', readonly=True),
        'employee_dependents': fields.one2many('hr.employee.dependent','employee_id', 'Dependents'),
        'joining_date': fields.date('Joining Date', required=False),
        'official_joining_date': fields.date('Official Joining Date', required=False),
        'worked_years': fields.function(_cal_worked_years, type='float', method=True, string='Worked Years', readonly=True,
                                        store={'hr.employee': (lambda self, cr, uid, ids, c={}: ids, ['joining_date'], 10)}),
        'employee_history': fields.one2many('hr.employee.history', 'employee_id', 'History', readonly=True),
        'dependant_of_taxpayer': fields.integer('Dependants', compute='get_dependant_of_taxpayer', store=True, readonly=True),
        'work_location_id': fields.many2one('hr.work.location', string='Work Location'),
        'area_id': fields.many2one('res.area', string='Area'),
        'tin': fields.char(string='TIN'),
        # tạm trú
        'mobile': fields.char('Mobile'),
        'email': fields.char('Email'),
        'phone': fields.char('Phone'),
        'temporary_street': fields.char('Temporary Street'),
        'temporary_ward_id': fields.many2one("res.ward", 'Ward'),
        'temporary_district_id': fields.many2one('res.district', 'District'),
        'temporary_city': fields.char('City'),
        'temporary_state_id': fields.many2one("res.country.state", 'State', ondelete='restrict'),
        'temporary_country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        # thường trú
        'permanent_street': fields.char('Permanent Street'),
        'permanent_ward_id': fields.many2one("res.ward", 'Ward'),
        'permanent_district_id': fields.many2one('res.district', 'District'),
        'permanent_city': fields.char('City'),
        'permanent_state_id': fields.many2one("res.country.state", 'State', ondelete='restrict'),
        'permanent_country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
        # place of birth
        'place_birth_ward_id': fields.many2one("res.ward", 'Ward'),
        'place_birth_district_id': fields.many2one("res.district", 'District', ondelete='restrict'),
        'place_birth_state_id': fields.many2one("res.country.state", 'State', ondelete='restrict'),
        'religion': fields.char(string='Religion'),
        'nation': fields.char(string='Ethnic'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'job_id': fields.many2one('hr.job', 'Job Title'),
        'address_id': fields.many2one('res.partner', 'Working Address', default=1),
#         'vn_job_name': fields.many2one('hr.job', 'VN Job Name'),
        
        # kiet them add danh sach ban hang cho nhan vien
#         'emp_sale_ids':fields.many2many('sale.order', 'emp_sale_rel', 'employee_id', 'sale_id', 'List Sale'),
#         'times': fields.selection([
#             ('dates','Date'),
#             ('periods', 'Periods'),
#             ('quarter','Quarter'),
#             ('years','Years')], 'Periods Type',),
#         'period_id': fields.many2one('account.period', 'Period',  domain=[('state','=','draft')],),
#         'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscalyear', domain=[('state','=','draft')],),
#         'date_start': fields.date('Date Start'),
#         'date_end':   fields.date('Date end'),
#         'quarter':fields.selection([
#             ('1', '1'),
#             ('2','2'),
#             ('3','3'),
#             ('4','4')], 'Quarter'),
            }
    
    @api.depends('employee_dependents')
    def get_dependant_of_taxpayer(self):
        temp = 0
        for i in self.employee_dependents:
            if i.is_dependent:
                temp+=1
        self.dependant_of_taxpayer = temp 
    
    def onchange_department_id(self, cr, uid, ids, department_id , context=None):
        domain = {}
        if department_id:
            job_ids = self.pool.get('hr.job').search(cr, uid, [('department_id', '=', department_id)])
            if job_ids:
                domain.update({'job_id':[('id', '=', job_ids)]})
        return {'domain': domain}
    
    def onchange_temporary_country_id(self, cr, uid, ids, temporary_country_id , context=None):
        domain = {}
        if temporary_country_id:
            state_ids = self.pool.get('res.country.state').search(cr, uid, [('country_id', '=', temporary_country_id)])
            if state_ids:
                domain.update({'temporary_state_id':[('id', '=', state_ids)]})
        return {'domain': domain}
    
    def onchange_temporary_state_id(self, cr, uid, ids, temporary_state_id , context=None):
        domain = {}
        if temporary_state_id:
            district_ids = self.pool.get('res.district').search(cr, uid, [('state_id', '=', temporary_state_id)])
            if district_ids:
                domain.update({'temporary_district_id':[('id', '=', district_ids)]})
        return {'domain': domain}
    
    def onchange_temporary_district_id(self, cr, uid, ids, temporary_district_id, context=None):
        domain = res = {}
        if temporary_district_id:
            ward_ids = self.pool.get('res.ward').search(cr, uid, [('district_id', '=', temporary_district_id)])
            if ward_ids:
                domain.update({'temporary_ward_id':[('id', '=', ward_ids)]})
            district = self.pool.get('res.district').browse(cr, uid, temporary_district_id)
            res = {'temporary_state_id': district.state_id.id or False}
            domain.update({'temporary_state_id':[('id', '=', district.state_id.id)]})
        return {'value': res, 'domain': domain}
    
    def onchange_permanent_country_id(self, cr, uid, ids, permanent_country_id , context=None):
        domain = {}
        if permanent_country_id:
            state_ids = self.pool.get('res.country.state').search(cr, uid, [('country_id', '=', permanent_country_id)])
            if state_ids:
                domain.update({'permanent_state_id':[('id', '=', state_ids)]})
        return {'domain': domain}
    
    def onchange_permanent_state_id(self, cr, uid, ids, permanent_state_id , context=None):
        domain = {}
        if permanent_state_id:
            district_ids = self.pool.get('res.district').search(cr, uid, [('state_id', '=', permanent_state_id)])
            if district_ids:
                domain.update({'permanent_district_id':[('id', '=', district_ids)]})
        return {'domain': domain}
    
    def onchange_permanent_district_id(self, cr, uid, ids, permanent_district_id, context=None):
        domain = res = {}
        if permanent_district_id:
            ward_ids = self.pool.get('res.ward').search(cr, uid, [('district_id', '=', permanent_district_id)])
            if ward_ids:
                domain.update({'permanent_ward_id':[('id', '=', ward_ids)]})
            district = self.pool.get('res.district').browse(cr, uid, permanent_district_id)
            res = {'permanent_state_id': district.state_id.id or False}
            domain.update({'permanent_state_id':[('id', '=', district.state_id.id)]})
        return {'value': res, 'domain': domain}
    
    def _get_default_job_status(self, cr, uid, context=None):
        res = self.pool.get('job.status').search(cr, uid, [(1, '=', 1)], context=context)
        if len(res) > 0:
            return  res[0]
        else:
            return ""
    
    _defaults = {
        'job_status':_get_default_job_status
    }
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        context = self._context
         
        res = super(hr_employee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ['form']:
            doc = etree.XML(res['arch'])
             
            for node in doc.xpath("//page[@name='page_history']"):
                if not self.env['ir.model.access'].check_groups("base.group_hr_user") or not SUPERUSER_ID:
                    if self.coach_id.user_id.id != self.env.user.id or self.parent_id.user_id.id != self.env.user.id:
                        node.set('attrs', "{'invisible': [('user_id','!=',%s)]}" % self.env.user.id)
            for node in doc.xpath("//page[@name='dependents']"):
                if not self.env['ir.model.access'].check_groups("base.group_hr_user") or not SUPERUSER_ID:
                    if self.coach_id.user_id.id != self.env.user.id or self.parent_id.user_id.id != self.env.user.id:
                        node.set('attrs', "{'invisible': [('user_id','!=',%s)]}" % self.env.user.id)
            for node in doc.xpath("//page[@name='personal_information']"):
                if not self.env['ir.model.access'].check_groups("base.group_hr_user") or not SUPERUSER_ID:
                    if self.coach_id.user_id.id != self.env.user.id or self.parent_id.user_id.id != self.env.user.id:
                        node.set('attrs', "{'invisible': [('user_id','!=',%s)]}" % self.env.user.id)
            for node in doc.xpath("//page[@name='hr_setting']"):
                if not self.env['ir.model.access'].check_groups("base.group_hr_user") or not SUPERUSER_ID:
                    if self.coach_id.user_id.id != self.env.user.id or self.parent_id.user_id.id != self.env.user.id:
                        node.set('attrs', "{'invisible': [('user_id','!=',%s)]}" % self.env.user.id)
                
            xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res

    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {'value': {}}
    
    def onchange_work_location_id(self, cr, uid, ids, work_location_id, context=None):
        domain = {}
        if work_location_id:
            work_obj = self.pool.get('hr.work.location').browse(cr, uid, work_location_id)
            state_id = work_obj.state_id.id or False
            if state_id:
                area_ids = self.pool.get('res.area').search(cr, uid, [('state_id', '=', state_id)])
                if area_ids:
                    domain.update({'area_id':[('id', '=', area_ids)]})
        return {'domain': domain}
    
    def onchange_place_birth_state_id(self, cr, uid, ids, place_birth_state_id, context=None):
        domain = {}
        if place_birth_state_id:
            district_ids = self.pool.get('res.district').search(cr, uid, [('state_id', '=', place_birth_state_id)])
            if district_ids:
                domain.update({'place_birth_district_id':[('id', '=', district_ids)]})
        return {'domain': domain}
    
    def onchange_place_birth_district_id(self, cr, uid, ids, place_birth_district_id, context=None):
        domain = {}
        if place_birth_district_id:
            ward_ids = self.pool.get('res.ward').search(cr, uid, [('district_id', '=', place_birth_district_id)])
            if ward_ids:
                domain.update({'place_birth_ward':[('id', '=', ward_ids)]})
        return {'domain': domain}
    
### TAG BY THINH: Tag to generate code via addons
    def create(self, cr, uid, vals, context=None):
#         if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "general_product.group_product_creation"):
#             raise AccessError(_("You're not able to create a product!!!"))
         
        system_sequence_obj = self.pool.get('system.sequence')
        code = system_sequence_obj.get_current_sequence(cr, 'employee_code')
        vals.update({'code': code})
        return super(hr_employee, self).create(cr, uid, vals, context=context)
     
    def init(self, cr):
        system_sequence_obj = self.pool.get('system.sequence')
        employee_ids = self.search(cr, SUPERUSER_ID, [('code', '=', False)])
        if len(employee_ids):
            for employee_id in employee_ids:
                code = system_sequence_obj.get_current_sequence(cr, 'employee_code')
                if code:
                    cr.execute('''
                    UPDATE hr_employee
                    SET code='%s'
                    WHERE id=%s
                    ''' % (code, employee_id))
        return True
    
    def _check_code(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.code:
            pids = self.search(cr, uid, [('code', '=', obj.code), ('id', '<>', obj.id)])
            if pids:
                raise osv.except_osv(_('Trùng lắp dữ liệu!'), _('Trùng mã nhân viên: %s') % (obj.code))
        if obj.scanner_code:
            pids = self.search(cr, uid, [('scanner_code', '=', obj.scanner_code), ('id', '<>', obj.id)])
            if pids:
                raise osv.except_osv(_('Trùng lắp dữ liệu!'), _('Trùng mã vân tay: %s') % (obj.scanner_code))
        if obj.identification_id:
            pids = self.search(cr, uid, [('identification_id', '=', obj.identification_id), ('id', '<>', obj.id)])
            if pids:
                raise osv.except_osv(_('Trùng lắp dữ liệu!'), _('Trùng Số CMND: %s') % (obj.identification_id))
        return True
 
    _constraints = [
        (_check_code, 'Mã nhân viên bị trùng', ['code']),
    ]
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        # Thanh: Search Employee
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
        if operator:
            args.append('|')
            args.append('|')
            args.append('|')
            args.append('|')
            args.append(['name', operator, value])
            args.append(['code', operator, value])
            args.append(['scanner_code', operator, value])
            args.append(['identification_id', operator, value])
            args.append(['passport_id', operator, value])
        return super(hr_employee, self).search(cr, uid, args, offset, limit, order, context=context, count=count)
    
    
    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        args = args or []
        domain = []
        if name:
            domain = [('name', operator, name)]
        ids = self.search(cr, user, domain + args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
                    ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'code'], context=context)
        res = []
        for record in reads:
            name = record['name']
            if record['code']:
                name = record['code'] + ' ' + name
            res.append((record['id'], name))
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        employee_history_pool = self.pool.get('hr.employee.history')
        for line in self.browse(cr, uid, ids):
            employee_history_vals = {}
            if vals.get('parent_id', False):
                employee_history_vals.update({'parent_id':vals.get('parent_id') or False})
            if vals.get('department_id', False):
                employee_history_vals.update({'department_id':vals.get('department_id') or False})
            if vals.get('job_id', False):
                employee_history_vals.update({'job_id':vals.get('job_id') or False})
            if vals.get('user_id', False):
                employee_history_vals.update({'user_id':vals.get('user_id') or False})
            if vals.get('effective_date', False):
                employee_history_vals.update({'effective_date':vals.get('effective_date') or False})
            if vals.get('worked_years', False):
                employee_history_vals.update({'worked_years':vals.get('worked_years') or False})
            if vals.get('create_date', False):
                employee_history_vals.update({'create_date':vals.get('create_date') or False})
            if employee_history_vals:
                employee_history_vals.update({'employee_id':line.id})
                employee_history_pool.create(cr, uid, employee_history_vals)
        return super(hr_employee, self).write(cr, uid, ids, vals, context)
    
hr_employee()

class hr_home_address(osv.osv):
    _name = 'hr.home.address'
    _columns = {
            'name': fields.char('Name', select=True),
            'ref': fields.char('Internal Reference', select=1),
            'street': fields.char('Street'),
            'street2': fields.char('Street2'),
            'zip': fields.char('Zip', size=24, change_default=True),
            'city': fields.char('City'),
            'state_id': fields.many2one("res.country.state", 'State', ondelete='restrict'),
            'country_id': fields.many2one('res.country', 'Country', ondelete='restrict'),
            'email': fields.char('Email'),
            'phone': fields.char('Phone'),
            'fax': fields.char('Fax'),
            'mobile': fields.char('Mobile'),
              }
    
    def name_get(self, cr, uid, ids, context=None):
        res = []
        address = ''
        for record in self.browse(cr, uid, ids):
            address += record.street or ''
            address += record.state_id and ', ' + record.state_id.name or ''
            address += record.country_id and ', ' + record.country_id.name or ''
            res.append((record['id'], address))
        return res
        
    
    @api.multi
    def onchange_state(self, state_id):
        if state_id:
            state = self.env['res.country.state'].browse(state_id)
            return {'value': {'country_id': state.country_id.id}}
        return {'value': {}}
hr_home_address()

class hr_employee_history(osv.osv):
    _name = 'hr.employee.history'
    _order = 'create_date desc'
    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
        'user_id': fields.many2one('res.users', 'Modified By', readonly=True),
        'parent_id': fields.many2one('hr.employee', 'Manager', ondelete='cascade'),
        'department_id':fields.many2one('hr.department', 'Department', readonly=True),
        'job_id': fields.many2one('hr.job', 'Job', readonly=True),
        'effective_date': fields.date('Effective Date', readonly=True),
        'worked_years': fields.float('Worked Years', digits=(16, 2)),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, ondelete='cascade', select=True),
        'company':fields.char('Company', readonly=True),
    }
    
    _defaults = {
        'user_id': lambda obj, cr, uid, context = None: uid,
    }
    
hr_employee_history()

class hr_employee_dependent(osv.osv):
    _name = "hr.employee.dependent"
    
    def _calculate_age(self, cr, uid, ids, field_name, arg, context=None):

        res = dict.fromkeys(ids, False)
        for ee in self.browse(cr, uid, ids, context=context):
            if ee.birthday:
                dBday = datetime.strptime(ee.birthday, DEFAULT_SERVER_DATE_FORMAT).date()
                dToday = datetime.now().date()
                res[ee.id] = (dToday - dBday).days / 365
        return res
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Related Employee', required=True),
        'name': fields.char('Name', size=128, required=True),
        'relationship': fields.char('Relationship', required=True),
        'gender': fields.selection([('male', 'Male'), ('female', 'Female')], 'Gender', required=True),
        'birthday': fields.date("Date of Birth"),
        'age': fields.function(_calculate_age, type='integer', method=True, string='Age', readonly=True),
        'education': fields.selection(EDUCATION_SELECTION, 'Education'),
        'employed': fields.boolean('Employed'),
        'is_dependent': fields.boolean('Is Dependant'),
        'mobile':fields.char('Mobile'),
        'address':fields.char('Address'),
        'identification_no':fields.text('Identification No'),
        'identification_date_issue':fields.date('Identification Date Issue'),
        'identification_place_issue':fields.text('Identification Place Issue'),
    }
    _defaults = {
        'is_dependent': False,
        'employed': False,
        'gender': 'male'
                }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
class hr_employee_insurances(osv.osv):
    _name = "hr.employee.insurances"
    _columns = {
        'name': fields.char('Insurance Name', required=True),
        }
    