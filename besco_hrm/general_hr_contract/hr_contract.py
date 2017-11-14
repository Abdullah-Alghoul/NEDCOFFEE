# -*- coding: utf-8 -*-
import time
from psycopg2 import OperationalError

from openerp import SUPERUSER_ID
import openerp.addons.decimal_precision as dp
import openerp

from datetime import date, datetime, timedelta
from dateutil import relativedelta
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import netsvc
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.exceptions import AccessError, UserError
from openerp import api
DATE_FORMAT = "%Y-%m-%d"

class hr_contract(osv.osv):
    _inherit = 'hr.contract'
    _description = 'Contract'
    _order = "state DESC, date_start DESC"
    
    _columns = {
        'contract_history': fields.one2many('hr.contract.history', 'contract_id', 'History', readonly=True),
        'other_wage': fields.float('Basic Wage', digits=(16, 0), required=False, help='Use this field to calculate Insurances'),
        # TOAN: add field no_attendance for some person have no rule in Attendance
        'no_attendance': fields.boolean(string="No Attendance"),
        # THANH: add state Trial
        'state': fields.selection([('draft','New'),('trial','Trial'),('open','Offical'),('pending', 'To Renew'),('close','Expired')],string='Status', track_visibility='onchange'),
                
        'name' : fields.char('Contract Reference', readonly=True, default='New'),
        'company_id': fields.many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('hr.contract')),
        
        'trial_date_start': fields.date('Trial Start Date'),
        'trial_date_end': fields.date('Trial End Date'),
        'date_start': fields.date('Start Date'),
        'date_end': fields.date('End Date'),
        
        'history_checked': fields.boolean(string='History Checked'),
        'old_id' : fields.many2one('hr.contract', ondelete='cascade'),
        'is_old_contract': fields.boolean(string='Is Old Contract'),
        #Kim: 
        'trial_salary': fields.float('Trial Salary', digits=(16,0)),  
        'wage': fields.float(string="NET Salary", digits=(16, 0)),
        'currency_id': fields.many2one("res.currency", string="Currency"),        
        'type_salary': fields.selection([('net','NET Salary'),('gross','Gross Salary')], string="Type Salary", required=True),
        'gross_salary': fields.float('Gross Salary', digits=(16,0)), 
        'trial': fields.boolean('Check Trial'),
        'priority': fields.selection([('normal','Normal'),('warning','Warning')],string='Priority'),
        #Toan:
        'expire_date' : fields.date('Expire Date'),
        'user_approve_id': fields.many2one('res.users', 'User Approve', readonly=True, copy=False),
        }
    
    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Contract Code must be unique per Company!'),
    ]
    
    def _default_currency_id(self, cr, uid, context=None):
        res_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.second_currency_id.id or False
        if not res_id:
            res_id = self.pool.get('res.currency').search(cr, uid, [('name','=','VND')])[0]
        return res_id
        
    _defaults = {
        'name': 'New',
        'state': 'draft',
        'priority': 'normal',
        'currency_id': _default_currency_id, 
        'type_salary': 'net',
        'trial_date_start': fields.date.context_today,
        'trial': False
        }
    @api.multi
    def button_run_trial(self):
        self.write({'state': 'trial'})
    
    def set_as_warning(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'priority': 'warning'}, context=context)
    
    def check(self, cr, uid, ids, autocommit=False, context=None):
        close_ids = []
        for contract in self.browse(cr, uid, ids, context=context):
            today = datetime.now().strftime("%Y-%m-%d")
            if contract.state == 'trial':
                date = contract.trial_date_end or False
            else:
                date = contract.date_end or False
            if contract.expire_date:
                date = contract.expire_date or False
            if date and today >= date:
                close_ids.append(contract.id)
        if close_ids:
            self.write(cr, uid, close_ids, {'state': 'close'}, context=context)
        return close_ids
    
    def run_check(self, cr, uid, use_new_cursor=False, company_id = False, context=None):
        print 'abc'
        if context is None:
            context = {}
        try:
            if use_new_cursor:
                cr = openerp.registry(cr.dbname).cursor()
            dom = [('state', 'in',['trial','open'])]
            if company_id:
                dom += [('company_id', '=', company_id)]
            contract_ids = []
            while True:
                ids = self.search(cr, SUPERUSER_ID, dom, context=context)
                if not ids or contract_ids == ids:
                    break
                else:
                    contract_ids = ids
                self.check(cr, SUPERUSER_ID, ids, autocommit=use_new_cursor, context=context)
                if use_new_cursor:
                    cr.commit()
        finally:
            if use_new_cursor:
                try:
                    cr.close()
                except Exception:
                    pass
        return {}
    
    @api.multi
    def create_contract_history(self):
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('general_hr_contract.action_hr_contract_history_relation')
        form_view_id = imd.xmlid_to_res_id('general_hr_contract.view_hr_contract_history_relation_form')
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'context': {'default_contract_id': self.id or False,'default_type_salary': self.type_salary or False, 
                'default_employee_id': self.employee_id.id or False, 'default_company_id': self.company_id.id or False},
            'res_model': action.res_model,
            }
        return result
    
    @api.onchange('company_id')
    def onchange_company_id(self):
        if not self.company_id:
            return
        currency_id = self.company_id.currency_id.id or False
        self.update({'currency_id': currency_id})
    
    def renew_event(self, cr, uid, ids, context=None):
        imd = self.pool.get('ir.model.data')
        action = imd.xmlid_to_object(cr, uid, 'hr_contract.action_hr_contract')
        form_view_id = imd.xmlid_to_res_id(cr, uid, 'hr_contract.hr_contract_view_form_add_page_history')
        this = self.browse(cr, uid, ids[0])
        working_hours = False
        if this.working_hours:
            working_hours = this.working_hours.id
        first_date=self.first_date(cr,uid,this.date_end,this.expire_date,working_hours,this.company_id.id)
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[form_view_id, 'form']],
            'target': action.target,
            'res_model': action.res_model,
            'context' : {'default_employee_id' : this.employee_id.id or form_view_id,
                'default_company_id' : this.company_id.id or False,
                'default_job_id' : this.company_id.id or False,
                'default_department_id' : this.department_id.id or False,
                'default_type_id' : this.type_id.id or False,
                'default_date_start' : this.date_end or '',
                'default_old_id' : this.id or False,
                'default_trial' : False,
                'default_state': 'draft',
                'default_date_start' : first_date or '',
                'default_trial_date_start' :this.trial_date_start,
                'default_trial_date_end': this.trial_date_end or '',
                    }
            }
        return result
    
    def button_offical_contract(self, cr, uid, ids, context=None):
        result = {}
        imd = self.pool.get('ir.model.data')
        action = imd.xmlid_to_object(cr, uid, 'hr_contract.action_hr_contract')
        form_view_id = imd.xmlid_to_res_id(cr, uid, 'hr_contract.hr_contract_view_form_add_page_history')
        for this in self.browse(cr, uid, ids):
            working_hours = False
            if this.working_hours:
                working_hours = this.working_hours.id
            first_date=self.first_date(cr,uid,this.trial_date_end,this.expire_date,working_hours,this.company_id.id)
            result = {
                'name': action.name,
                'help': action.help,
                'type': action.type,
                'views': [[form_view_id, 'form']],
                'target': action.target,
                'res_model': action.res_model,
                'context' : {
                    'default_employee_id' : this.employee_id.id or form_view_id,
                    'default_company_id' : this.company_id.id or False,
                    'default_job_id' : this.job_id.id or False,
                    'default_department_id' : this.department_id.id or False,
                    'default_working_hours': working_hours or False,
                    'default_date_start' : first_date or '',
                    'default_old_id' : this.id or False,
                    'default_trial' : False,
                    'default_trial_date_start' :this.trial_date_start,
                    'default_trial_date_end': this.trial_date_end or '',
                    }
            }
        return result
    
    def first_date(self,cr,uid,date_end,expire_date,working_time_id,company_id):
        last_date = datetime.now()
        if date_end:
            last_date = datetime.strptime(date_end,DATE_FORMAT)
        if expire_date:
            last_date = datetime.strptime(expire_date,DATE_FORMAT)
        shut_day = last_date.weekday()
        if not working_time_id or not company_id:
            last_date = last_date + timedelta(days=1)
            return str(last_date)
        working_time_obj = self.pool.get('resource.calendar').browse(cr, uid,working_time_id)
        flag = 0
        while shut_day < 7 :
            shut_day+=1
            if shut_day==7:
                shut_day=0
            last_date = last_date + timedelta(days=1)
            for i in working_time_obj.attendance_ids:
                if shut_day == int(i.dayofweek):
                    self.pool.get('hr.payslip').get_holiday_day(cr, uid, last_date, last_date, company_id,context=None)
                    flag = 1
            if flag ==1:
                break
        return str(last_date)
    
    @api.multi
    def button_run_official(self):
        self.write({'state': 'open'})
       
    @api.multi
    def button_set_to_draft(self):
        self.write({'state': 'draft'})  
        
    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
                
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        if not employee_id:
            return {'value': {'job_id': False, 'department_id': False}}
        emp_obj = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        job_id = dept_id = False
        if emp_obj.job_id:
            job_id = emp_obj.job_id.id
            job_obj = self.pool.get('hr.job').browse(cr, uid, job_id, context=context)
        if emp_obj.department_id:
            dept_id = emp_obj.department_id.id
        return {'value': {'job_id': job_id, 'department_id': dept_id}} 
    
    @api.constrains('name')
    def _check_name(self):
        for contract in self:
            contract_ids = self.search([('name','=',contract.name),('id','!=',contract.id),('state','!=','cancel')])
            if contract_ids:
                raise UserError(_("Contract (%s) was exist.")%(contract.name))
            return True
 
    def create(self, cr, uid, vals, context=None):
# THINH: TAG to dodge conflict with generate-code addons
#             employee_id = vals.get('employee_id', False)
#             employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
#             ir_sequence_obj = self.pool.get('ir.sequence')
#             code = ir_sequence_obj.next_by_code(cr,uid, 'contract_code')
#             vals.update({'name': code})
######
        if vals.get('name', 'New'):
            employee_id = vals.get('employee_id', False)
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
             
            if vals.get('date_start', False):
                year = vals.get('date_start', False)[0:4]
                code = employee.code+'/HR/'+year
            else:
                year = vals.get('trial_date_start', False)[0:4]
                code = employee.code+'/HR-TV/'+year
            vals.update({'name' : code})
        if vals.get('old_ids',False) and vals.get('old_ids')[0] and vals.get('old_ids')[0][1]:
            self.write(cr,uid,vals.get('old_ids')[0][1], {'is_old_contract':True})
            
        if context and context.get('default_contract_id', False):
                contract_id = context['default_contract_id']   
        
        return super(hr_contract, self).create(cr, uid, vals, context=context)
#     def create(self, cr, uid, vals, context=None):
# #         if vals.get('date_start', False):
# #             date_start = vals.get('date_start', False)
# #             
#         if vals.get('trial_date_start', False):
#             trial_date_start = vals.get('trial_date_start', False)
#             
# #         if vals.get('date_end', False):
# #             date_end = vals.get('date_end', False)
# #             
#         if vals.get('trial_date_end', False):
#             trial_date_end = vals.get('trial_date_end', False)
#         
#         if vals.get('name', 'New'):
#             employee_id = vals.get('employee_id', False)
#             employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
#             
#             if vals.get('expire_date', False):
#                 year = vals.get('expire_date', False)[0:4]
#                 code = employee.code+'/HR/'+year
#             else:
#                 year = vals.get('trial_date_start', False)[0:4]
#                 code = employee.code+'/HR/TRIAL/'+year
#             vals.update({'name' : code})
#         return super(hr_contract, self).create(cr, uid, vals, context=context)
        
#     def write(self, cr, uid, ids, vals, context=None):
#         contract_history = self.pool.get('hr.contract.history')
#         for this in self.browse(cr, uid, ids, context=context):
#             if vals.get('state', False):
#                 state = vals.get('state', False)
#                 if state == 'cancel':
#                     for history in this.contract_history:
#                         contract_history_obj = contract_history.browse(cr, uid, history.id, context=context)
#                         contract_history.button_cancel(cr, uid, contract_history_obj.id, context=context)
#                     vals['state'] = state
#                 elif state == 'trial':
#                     contract_ids = self.search(cr, uid, [('employee_id','=',this.employee_id.id),('state','in',('trial','open'))])
#                     if contract_ids:
#                         raise UserError(_("Can not be converted to a Trial Contract new when the old contract being used."))
#                 elif state == 'open':
#                     contract_ids = self.search(cr, uid, [('employee_id','=',this.employee_id.id),('state','=','open')])
#                     if contract_ids:
#                         raise UserError(_("Can not be converted to a Trial Contract new when the old contract being used."))
#                 else:
#                     if this.state != 'draft':
#                         if this.trial == True and this.state == 'trial' and state == 'open':
#                             contract_ids = self.search(cr, uid, [('employee_id','=',this.employee_id.id),('state','=','open')])
#                             if contract_ids:
#                                 raise UserError(_("Can not be converted to a Offical Contract new when the old contract being used."))
#                             
#                             if vals.get('trial_date_start',False):
#                                 raise UserError(_("Can not edit probationary period."))
#                             if vals.get('trial_date_end',False):
#                                 raise UserError(_("Can not edit probationary period."))
#                             if vals.get('employee_id',False):
#                                 raise UserError(_("Can not edit Employee when state not draft."))
#                             
#                             if vals.get('date_start',False):
#                                 date_start = vals.get('date_start',False)
#                             else:
#                                 date_start = this.date_start or False
#                             if not date_start:
#                                 raise UserError(_("Lack of information Start Dates of Offical Contract."))
#                             
#                             if vals.get('wage', False):
#                                 wage = vals.get('wage', False)
#                             else:
#                                 wage = this.wage or 0.0
#                             if not wage:
#                                 raise UserError(_("Lack of information Wage of Offical Contract."))
#                             vals['trial'] = False
#                         
#                         elif this.state == 'trial' and state == 'close':
#                             vals['state'] = state
#                         elif this.state == 'open' and state == 'close':
#                             if not this.date_end and not vals.get('date_end',False):
#                                 vals['date_end'] = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
#                         else:
#                             raise UserError(_("Can not edit when state not draft."))
#             if vals.get('state', False) == 'close' and not vals.get('history_checked', False):
#                 raise UserError(_("Please Expire Contract form Employee Information."))
#             if not vals.get('state', False):
#                 if this.state != 'draft':
#                     if this.state == 'open':
#                         if vals.get('history_checked',False) == True:
#                             vals['history_checked'] = False 
# #                         else:
# #                             raise UserError(_("Can not edit when state not draft."))
#                     elif this.state in ('trial','close') and this.trial == True:
#                         if vals.get('employee_id',False):
#                             raise UserError(_("Can not edit Employee when state not draft."))
#                         if vals.get('trial_date_start',False):
#                             raise UserError(_("Can not edit probationary period."))
#                         if vals.get('trial_date_end',False):
#                             raise UserError(_("Can not edit probationary period."))
#                     else:
#                         raise UserError(_("Can not edit when state not draft."))
#         return super(hr_contract, self).write(cr, uid, ids, vals, context=context)
    
    
    
    
    def unlink(self, cr, uid, ids, context=None):
        for contract in self.browse(cr, uid, ids):
            if contract.state != 'draft':
                raise UserError(_("Can not unlink."))
        return super(hr_contract, self).unlink(cr, uid, ids, context=context)
hr_contract()

class hr_contract_history(osv.osv):
    _name = 'hr.contract.history'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = 'date desc, create_date desc, state'
    
    @api.model
    def _default_currency_id(self):
        currency_id = self.env.user.company_id.id
        company_obj = self.env['res.company'].browse(currency_id)
        return company_obj.id  
    
    _columns = {
        'name': fields.char('Contract Reference', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date': fields.date('Date of Application', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        
        'contract_id': fields.many2one('hr.contract', 'Contract', ondelete='cascade', select=True, index=True),
        'employee_id': fields.related('contract_id', 'employee_id', type='many2one', relation='hr.employee', string='Employee', readonly=True, store=True),
        'job_id': fields.related('contract_id', 'job_id', type='many2one', relation='hr.job', string='Job', readonly=True, store=True),
        'company_id': fields.related('contract_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True),
        'currency_id': fields.related("contract_id", 'currency_id',type='many2one' ,relation='res.currency', string="Currency", store=True),

        'state': fields.selection([('draft','New'),('approve', 'Approved'),('cancel', 'Cancelled')], 'State', required=True),
        
        'wage': fields.float('NET Salary', readonly=True, states={'draft': [('readonly', False)]}, required=True, digits=(16, 0)),
        'wage_old': fields.float('Old Salary', readonly=True),
        'gross_salary_old': fields.float('Old Gross Salary', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, copy=False),
        'create_uid': fields.many2one('res.users', 'Create User', readonly=True, copy=False),
        'date_approve': fields.datetime('Approval Date', readonly=True, copy=False),
        'user_approve': fields.many2one('res.users', 'User Approve', readonly=True, copy=False),
        }
    
    _defaults = {
        'name': 'New',
        'state': 'draft',   
        'date': fields.date.context_today,
        'create_date': fields.date.context_today,
        'create_uid': lambda self, cr, uid, c: uid,
        
        }
    
    def create(self, cr, uid, vals, context=None):
        if not vals.get('name',False) or vals['name'] == 'New':
            if vals.get('contract_id', False):
                contract_id = vals.get('contract_id', False)
            elif context and context.get('default_contract_id', False):
                contract_id = context['default_contract_id']
            
            contract = self.pool.get('hr.contract').browse(cr, uid, contract_id)
            contract_history_ids = self.pool.get('hr.contract.history').search(cr, uid,[('contract_id','=',contract.id)],order='id desc',limit=1)
            if contract_history_ids:
                contract_history_obj =self.pool.get('hr.contract.history').browse(cr, uid, contract_history_ids[0])
                contract_history_obj.write({'gross_salary_old':contract.gross_salary})
            number = len(self.search(cr, uid, [('contract_id', '=', contract_id)])) + 1
            name = contract.name + '/%%0%sd' % 3 % number
            vals['name'] = name
            vals.update({'name':name ,'wage_old':contract.wage})
        return super(hr_contract_history, self).create(cr, uid, vals, context)
    
    def button_approve(self, cr, uid, ids, context=None):
        for history in self.browse(cr, uid, ids):
            wage = history.wage or 0
            contract = self.pool.get('hr.contract')
            if history.contract_id.id:
                contract_obj = contract.browse(cr, uid, history.contract_id.id)
                if contract_obj.type_salary == 'net':
                    contract.write(cr, uid, [contract_obj.id], {'wage': wage,'history_checked': True})
                if contract_obj.type_salary == 'gross':
                    contract.write(cr, uid, [contract_obj.id], {'gross_salary': wage,'history_checked': True})
        return self.write(cr, uid, ids, {'state':'approve', 'date_approve': time.strftime('%Y-%m-%d %H:%M:%S'), 'user_approve': uid})
    
    def button_cancel(self, cr, uid, ids, context=None):
        for history in self.browse(cr, uid, ids):
            wage_old = history.wage_old or 0
            contract = self.pool.get('hr.contract')
            if history.contract_id.id:
                contract.write(cr, uid, [history.contract_id.id], {'wage': wage_old})
        return self.write(cr, uid, ids, {'state':'cancel'})
        
    @api.multi
    def print_report(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_wageup_contract_history'}
    
hr_contract_history()
