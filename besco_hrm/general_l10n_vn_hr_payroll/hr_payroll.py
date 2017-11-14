#-*- coding:utf-8 -*-
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

from openerp import api, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp

from openerp.tools.safe_eval import safe_eval as eval
from openerp.exceptions import UserError

class hr_salary_rule_category(osv.osv):
    _inherit = 'hr.salary.rule.category'
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['code'], context=context)
        res = []
        for record in reads:
            name = record['code']
            res.append((record['id'], name))
        return res
    
hr_salary_rule_category()

class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'
    _columns = {
        # Thanh: add Product UoM
        'uom_id': fields.many2one('product.uom', 'UoM'),
        'contribution': fields.selection([("employee","Employee's contribution"),("company","Employer's contribution")], string="Contribution")
#         'free_pit': fields.boolean('Free PIT', help="Free Personal Income Tax"),
                }
hr_salary_rule()

class hr_payslip(osv.osv):
    _inherit = "hr.payslip"
    
    @api.onchange('date_from')
    def _onchange_date(self):
        for payslip in self:
            date_from = datetime.strptime(payslip.date_from, '%Y-%m-%d').date()
            day = float(date_from.strftime('%d'))
            if day > 25:
                start_date = str(date_from + relativedelta.relativedelta(day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(months=+1, day=25)) or False
            else:
                start_date = str(date_from + relativedelta.relativedelta(months=-1, day=26)) or False
                end_date = str(date_from + relativedelta.relativedelta(day=25)) or False
                
            payslip.update({'date_from': datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT) or False,
                               'date_to': datetime.strptime(end_date, DEFAULT_SERVER_DATE_FORMAT) or False})
            
    
    def _get_user_department(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            res[payslip.id] = payslip.employee_id.department_id and payslip.employee_id.department_id.id or False
        return res
    
    def _compute_advance_total(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        advance_payment_pool = self.pool.get('hr.advance.payment')
        for payslip in self.browse(cr, uid, ids, context=context):
            res[payslip.id] = 0.0
            for line in payslip.advance_payment_history_ids:
                advance_payment = advance_payment_pool.browse(cr, uid, line.advance_payment_id.id)
                res[payslip.id] += line.payment_amount * advance_payment.exchange_rate or 0.0
        return res
    
    def _compute_overtime_hours(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for payslip in self.browse(cr, uid, ids, context=context):
            res[payslip.id] = 0.0
            for line in payslip.overtime_ids:
                if line.state == 'validate':
                    res[payslip.id] += round(line.number_of_hours_temp * line.rate / 100, 2)
        return res
    
    def _get_attendances(self, cr, uid, ids, name, args, context=None):
        result = {}
        user_pool = self.pool.get('res.users')
        for ho in self.browse(cr, uid, ids, context=context):
            usertz_vs_utctz = user_pool.get_diff_hours_usertz_vs_utctz(cr, ho.employee_id.user_id.id or uid) or 7
            lines = []
            result.setdefault(ho.id, {
                'attendances_ids': lines,
            })
            cr.execute("""
                    SELECT a.id
                      FROM hr_attendance a
                    WHERE   a.action = 'sign_in'
                            AND %(date_to)s >= (a.name + interval '%(usertz_vs_utctz)s hour')::date
                            AND %(date_from)s <= (a.name + interval '%(usertz_vs_utctz)s hour')::date
                            AND %(employee_id)s = a.employee_id
                     GROUP BY a.id""", {'date_from': ho.date_from,
                                        'date_to': ho.date_to,
                                        'usertz_vs_utctz': usertz_vs_utctz,
                                        'employee_id': ho.employee_id.id, })
            lines.extend([row[0] for row in cr.fetchall()])
            result[ho.id]['attendances_ids'] = lines
                
        return result
    
    def get_day_nums(self, cr, uid, ids, date_from, date_to, context=None):
        timesheet_pool= self.pool.get('general.hr.timesheet')
        for payslip in self.browse(cr, uid, ids, context=context):
            day_nums = 0
            timesheet_ids = timesheet_pool.search(cr,uid,[('work_date','>=',date_from),('work_date','<=',date_to),('state','=','approve')])
            if timesheet_ids:
                for timesheet_id in timesheet_ids:
                    for item in timesheet_pool.browse(cr, uid, timesheet_id).hr_timesheet_line:
                        if item.employee_id == payslip.employee_id:
                            if item.real_worked/8 >0.5:
                                day_nums+=1
            return day_nums
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'default_work_days': fields.float('Default Work Days'),
        'advance_payment_history_ids': fields.many2many('hr.advance.payment.history', 'hr_advance_payment_history_payslip_rel','payslip_id', 'payment_history_id', 'Advance Payments', readonly=True), 
        'advance_total': fields.function(_compute_advance_total, string='Advance Total', type='float', digits_compute=dp.get_precision('Payroll'),
            store={
                'hr.payslip': (lambda self, cr, uid, ids, c={}: ids, ['advance_payment_history_ids'], 10),
            }, readonly=True),
        'attendances_ids' : fields.function(_get_attendances, type='many2many', relation='hr.attendance', method=True, string='Attendances',
#                     store={
#                         'hr.payslip': (lambda self, cr, uid, ids, c={}: ids, ['advance_payment_ids'], 10),
#                     }, 
            readonly=True, multi="_attendance"),
        
        'overtime_ids':fields.many2many('hr.overtime', 'hr_overtime_payslip_rel', 'payslip_id', 'overtime_id', 'Overtime Requests', readonly=True),
        'overtime_hours': fields.function(_compute_overtime_hours, string='Overtime Hours', type='float', digits=(16, 2),
            store={
                'hr.payslip': (lambda self, cr, uid, ids, c={}: ids, ['overtime_ids'], 10),
            }, readonly=True),
        
        'department_id': fields.function(_get_user_department, type='many2one', relation='hr.department', string='Department',
            store={
                'hr.payslip': (lambda self, cr, uid, ids, c={}: ids, ['employee_id'], 10),
            }, readonly=True),
        'timesheet_line_ids': fields.one2many('hr.payslip.timesheet', 'payslip_id', 'Payslip Payslip'),
        'day_nums': fields.float(string='Day Nums'),
        }
        
    _defaults = {
    }
    
    def get_default_worked_day(self, cr, uid, contract_ids, date_from, date_to, context=None):
        number_of_days = 0.0
        print "===="
        print contract_ids
        print date_from
        print date_to
        for contract in self.pool.get('hr.contract').browse(cr, uid, contract_ids, context=context):
            
            if not contract.working_hours:
                return 1
#             if contract.state not in ('trial','open'):
# #                 continue 


## TAG BY THINH
#             day_from = datetime.strptime(date_from, "%Y-%m-%d")
#             day_to = datetime.strptime(date_to, "%Y-%m-%d")
#             nb_of_days = (day_to - day_from).days + 1
#             for day in range(0, nb_of_days):
#                 working_hours_on_day = self.pool.get('resource.calendar').working_hours_on_day(cr, uid, contract.working_hours, day_from + timedelta(days=day), context)
#                 if working_hours_on_day:
#                     number_of_days += 1.0
##THINH
            day_from = datetime.strptime(date_from,"%Y-%m-%d")
            day_to = datetime.strptime(date_to,"%Y-%m-%d")
            wd_hours_tuple = []
            total_hours = wd_hours = stack = 0.0
            wd = [0,1,2,3,4,5,6]
            for d in wd:
                day_ids = self.pool.get('resource.calendar.attendance').search(cr,uid,[('calendar_id','=',contract.working_hours.id),('dayofweek','=',str(d))])
                if not day_ids:
                    continue
                for day_id in day_ids:
                    day_obj = self.pool.get('resource.calendar.attendance').browse(cr,uid,day_id)
                    if day_obj.rate>100:
                        continue
                    wd_hours += (day_obj.hour_to - day_obj.hour_from)
                    if wd_hours > 5.0:
                        stack = 1.0
                wd_hours_tuple.append({
                    'week_day' : d,
                    'hours' : wd_hours,
                    'break' : stack
                })
                wd_hours = stack = 0
            loop_day = day_from
            holiday_days = self.get_holiday_day(cr, uid, day_from, day_to, contract.company_id.id, context=context) or False
            while (loop_day <= day_to):
                holiday_flag  = False
                if holiday_days:
                    for line in holiday_days:
                        if loop_day == line:
                            holiday_flag= True
                if holiday_flag:
                    loop_day += timedelta(days=1)
                    continue
                for week_day in wd_hours_tuple:
                    if week_day['week_day'] == loop_day.weekday():
                        total_hours += week_day['hours']
                        if week_day['break']:
                            total_hours -= contract.working_hours.break_hours
                loop_day += timedelta(days=1)
            number_of_days = total_hours/8 
        return number_of_days
    
    def get_contract_sub(self, cr, uid, employee, date_from, date_to, context=None):
        contract_obj = self.pool.get('hr.contract')
        trial_dom1 = ['&', ('trial', '=', True), '&', ('trial_date_start', '>=', date_from),
                      ('trial_date_start', '<=', date_to)]
        trial_dom2 = ['&', ('trial', '=', True), '&', ('expire_date', '>=', date_from), ('expire_date', '<=', date_to)]
        trial_dom3 = ['&', ('trial', '=', True), '&', ('expire_date', '=', False), '&',
                      ('trial_date_end', '>=', date_from), ('trial_date_end', '<=', date_to)]
        trial_dom4 = ['&', ('trial', '=', True), '&', ('expire_date', '=', False), '&',
                      ('trial_date_start', '<=', date_from), ('trial_date_end', '>=', date_to)]
        trial_dom5 = ['&', ('trial', '=', True), '&', ('trial_date_start', '<=', date_from),
                      ('expire_date', '>=', date_to)]
        dom1 = ['&', ('trial', '=', False), '&', ('date_start', '>=', date_from), ('date_start', '<=', date_to)]
        dom2 = ['&', ('trial', '=', False), '&', ('expire_date', '>=', date_from), ('expire_date', '<=', date_to)]
        dom3 = ['&', ('trial', '=', False), '&', ('expire_date', '=', False), '&', ('date_end', '>=', date_from),
                ('date_end', '<=', date_to)]
        dom4 = ['&', ('trial', '=', False), '&', ('expire_date', '=', False), '&', ('date_start', '<=', date_from),
                ('date_end', '>=', date_to)]
        dom5 = ['&', ('trial', '=', False), '&', ('date_start', '<=', date_from), ('expire_date', '>=', date_to)]
        dom6 = ['&', ('trial', '=', False), '&', ('expire_date', '=', False), '&', ('date_start', '<=', date_from),
                ('date_end', '=', False)]
        trial_dom = [('employee_id', '=', employee.id), '|', '|', '|',
                     '|'] + trial_dom1 + trial_dom2 + trial_dom3 + trial_dom4 + trial_dom5
        dom = [('employee_id', '=', employee.id), '|', '|', '|', '|', '|'] + dom1 + dom2 + dom3 + dom4 + dom5 + dom6
        trial_contract_ids = contract_obj.search(cr, uid, trial_dom, context=context)
        official_contract_ids = contract_obj.search(cr, uid, dom, context=context)
        contract_ids = trial_contract_ids + official_contract_ids
        return contract_ids

    def get_contract(self, cr, uid, employee, date_from, date_to, context=None):
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('state','not in',['draft','close']),('employee_id','=',employee.id)], context=context)
        return contract_ids

    def create(self,cr,uid,vals,context=None):
        if not vals.get('contract_id',False):
            emp_obj = self.pool.get('hr.employee').browse(cr, uid, vals.get('employee_id', False))
            raise UserError("Employee %s has no available contract!"%emp_obj.name_related)
        sql = '''SELECT id FROM hr_payslip WHERE (date_from <= '%s' and '%s' <= date_to) 
            AND employee_id=%s AND coalesce(contract_id, %s) = %s AND state != 'cancel'
            ''' % (vals.get('date_to',False), vals.get('date_from',False), vals.get('employee_id', False),
                vals.get('contract_id',False), vals.get('contract_id',False))
        cr.execute(sql)
        if cr.fetchall():
            raise UserError('You cannot have 2 Payslips that overlap!')
        if vals.get('input_line_ids', False):
            vals.update({'input_line_ids': []})
#             vals.pop('input_line_ids')
        return super(hr_payslip, self).create(cr, uid, vals, context=context)
    
    @api.onchange('employee_id', 'date_from')
    def onchange_employee(self, d_from=None, d_to=None, emp_id=None):
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return
        if not emp_id and not d_to and not d_from:
            employee_id = self.employee_id
            date_from = self.date_from
            date_to = self.date_to
        else:
            employee_id = emp_id
            date_from = d_from
            date_to = d_to

        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        self.name = _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y')))
        self.company_id = employee_id.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            contract_ids = self.get_contract(employee_id, date_from, date_to)
            if not contract_ids:
                return
            self.contract_id = self.contract_id.browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        # computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(contract_ids,employee_id.id, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)

        input_line_ids = self.get_inputs(contract_ids, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
#         self.input_line_ids = input_lines
        
        # THANH: Compute worked days
        default_work_days = self.get_default_worked_day(contract_ids, date_from, date_to)
        self.default_work_days = default_work_days
        return
    
    def onchange_employee_id(self, cr, uid, ids, date_from, date_to, employee_id=False, contract_id=False, context=None):
        employee_obj = self.pool.get('hr.employee')
        contract_obj = self.pool.get('hr.contract')
        worked_days_obj = self.pool.get('hr.payslip.worked_days')
        input_obj = self.pool.get('hr.payslip.input')
#         res = super(hr_payslip, self).onchange_employee_id(cr, uid, ids, date_from, date_to, employee_id=employee_id, contract_id=contract_id, context=context)
#         if (not employee_id) or (not date_from) or (not date_to):
#             return res
        
        if context is None:
            context = {}
        #delete old worked days lines
        old_worked_days_ids = ids and worked_days_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_worked_days_ids:
            worked_days_obj.unlink(cr, uid, old_worked_days_ids, context=context)

        #delete old input lines
        old_input_ids = ids and input_obj.search(cr, uid, [('payslip_id', '=', ids[0])], context=context) or False
        if old_input_ids:
            input_obj.unlink(cr, uid, old_input_ids, context=context)
        
        
         # defaults
        res = {'value':{ 'line_ids':[],'input_line_ids': [], 'worked_days_line_ids': [],
                        # 'details_by_salary_head':[], TODO put me back, 
                        'name':'','contract_id': False,'struct_id': False,}}
        
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        employee_id = employee_obj.browse(cr, uid, employee_id, context=context)
        if contract_id:
            contract_ids = [contract_id]
        else:
            contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
        default_work_days = self.get_default_worked_day(cr, uid, contract_ids, date_from, date_to, context)
        res['value']['default_work_days'] = default_work_days
            
        ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from, "%Y-%m-%d")))
        
        res['value'].update({'name': _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(ttyme.strftime('%B-%Y'))),'company_id': employee_id.company_id.id})

        if not context.get('contract', False):
            # fill with the first contract of the employee
            contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
        else:
            if contract_id:
                # set the list of contract for which the input have to be filled
                contract_ids = [contract_id]
            else:
                # if we don't give the contract, then the input to fill should be for all current contracts of the employee
                contract_ids = self.get_contract(cr, uid, employee_id, date_from, date_to, context=context)
        if not contract_ids:
            return res
        contract_record = contract_obj.browse(cr, uid, contract_ids[0], context=context)
        res['value'].update({'contract_id': contract_record and contract_record.id or False})
        struct_record = contract_record and contract_record.struct_id or False
        if not struct_record:
            return res
        res['value'].update({'struct_id': struct_record.id})
        
        # THANH: Compute worked days
        default_work_days = self.get_default_worked_day(cr, uid, contract_ids, date_from, date_to, context)
        res['value']['default_work_days'] = default_work_days
        
         #computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(cr, uid, contract_ids,employee_id.id, date_from, date_to, context=context)
        input_line_ids = self.get_inputs(cr, uid, contract_ids, date_from, date_to, context=context)
        res['value'].update({
                    'worked_days_line_ids': worked_days_line_ids,
                    'input_line_ids': input_line_ids,
        })
        return res
    # Minh
    def get_inputs(self, cr, uid, contract_ids, date_from, date_to, context=None):
        res = []
        input_id_ids =[]
        contract_obj = self.pool.get('hr.contract')
        rule_obj = self.pool.get('hr.salary.rule')
        rule_input_obj = self.pool.get('rule.input')
        structure_ids = contract_obj.get_all_structures(cr, uid, contract_ids, context=context)
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(cr, uid, structure_ids, context=context)
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        for contract in contract_obj.browse(cr, uid, contract_ids, context=context):
            ##THINH FIX ALL ABOUT INPUT
            rule_input_ids = rule_input_obj.search(cr,uid,[('company_id','=',contract.company_id.id),('date_from','<=',date_from),('date_to','>=',date_to)],context=None)
            for rule in rule_obj.browse(cr, uid, sorted_rule_ids, context=context):
                if rule.input_ids:
                    for input_obj in rule.input_ids:
                        #THINH flag to mark that input was configured on rule_input_line
                        flag = 0
                        for rule_input_id in rule_input_ids:
                            rule_input_line_ids = self.pool.get('rule.input.line').search(cr,uid,[('rule_input_id','=',rule_input_id),('name','=',input_obj.id)])
                            for rule_input_line_obj in self.pool.get('rule.input.line').browse(cr,uid,rule_input_line_ids):
                                if not rule_input_line_obj.employee_id:
                                    if not rule_input_line_obj.job_id:
                                        inputs = {
                                                'name': input_obj.name,
                                                'code': input_obj.code,
                                                'amount':rule_input_line_obj.value,
                                                'contract_id': contract.id,
                                                }
                                        res += [inputs]
                                        flag = 1
                                    else:
                                        if contract.job_id.id == rule_input_line_obj.job_id.id:
                                            inputs = {
                                                    'name': input_obj.name,
                                                    'code': input_obj.code,
                                                    'amount':rule_input_line_obj.value,
                                                    'contract_id': contract.id,
                                                    }
                                            res += [inputs]
                                            flag = 1
                                elif rule_input_line_obj.employee_id.id == contract.employee_id.id:
                                    inputs = {
                                            'name': input_obj.name,
                                            'code': input_obj.code,
                                            'amount':rule_input_line_obj.value,
                                            'contract_id': contract.id,
                                            }
                                    res += [inputs]
                                    flag = 1
                                
                        if not flag:
                            inputs = {
                                    'name': input_obj.name,
                                    'code': input_obj.code,
                                    'amount':0.0,
                                    'contract_id': contract.id,
                                    }
                            res += [inputs]
                            flag = 1
        return res
    ##THINH END FIX
#      ##TAG MINH's SECTION
                    ##THINH FIX employee_id --> company_id
#                     rule_input_ids =rule_input_obj.search(cr,uid,[('company_id','=',contract.company_id.id),('date_from','>=',date_from),('date_from','<=',date_to)],context=None)
#                     if rule_input_ids:
#                         for rule_input in rule_input_obj.browse(cr, uid, rule_input_ids, context=context):
#                             #Minh edit
#                             for input in rule.input_ids:
#                                 for rule_input_line in rule_input.rule_input_line_ids:
#                                     if not rule_input_line.employee_id:
#                                         input_id_ids += [rule_input_line.name.id]
#                                         if rule_input_line.name.id == input.id:
#                                             inputs = {
#                                                  'name': input.name,
#                                                  'code': input.code,
#                                                  'amount':rule_input_line.value,
#                                                  'contract_id': contract.id,
#                                             }
#                                             res += [inputs]
#                                     else: 
#                                         if rule_input_line.employee_id == contract.employee_id.id:
#                                             inputs = {
#                                                  'name': input.name,
#                                                  'code': input.code,
#                                                  'amount':rule_input_line.value,
#                                                  'contract_id': contract.id,
#                                             }
#                                             res += [inputs]
#                                 if input.id not in input_id_ids:
#                                     inputs = {
#                                          'name': input.name,
#                                          'code': input.code,
#                                          'amount':0.0,
#                                          'contract_id': contract.id,
#                                     }
#                                     res += [inputs]
#                     else:
#                         for input in rule.input_ids:
#                             inputs = {
#                                          'name': input.name,
#                                          'code': input.code,
#                                          'amount':0.0,
#                                          'contract_id': contract.id,
#                                     }
#                             res += [inputs]
                        
#         return res



##THINH: TAG to continue batch
#     def _payslip_date(self, cr, uid, ids, forced_user_id=False, context=None):
#         for payslip in self.browse(cr, uid, ids, context=context):
#             if payslip.contract_id:
#                 sql = '''SELECT id FROM hr_payslip WHERE (date_from <= '%s' and '%s' <= date_to) 
#                     AND employee_id=%s AND coalesce(contract_id, %s) = %s AND state != 'cancel'
#                     AND id <> %s''' % (payslip.date_to, payslip.date_from or False, payslip.employee_id.id or False,
#                         payslip.contract_id.id or False, payslip.contract_id.id or False, payslip.id or False)
#                 cr.execute(sql)
#                 if cr.fetchall():
#                     return False
#         return True
# 
#     _constraints = [
#         (_payslip_date, 'You cannot have 2 Payslips that overlap!', ['date_from', 'date_to']),
#     ]
    
    
    def get_holiday_day(self, cr, uid, date_from, date_to, company_id,context=None):
        holiday_days = []
        holiday_day_pool = self.pool.get('hr.holiday.day')
        if date_from and date_to:
            holiday_day_ids = holiday_day_pool.search(cr, uid, [('date_from','>=',date_from),('date_to','<=',date_to),('company_id','=',company_id)])
            for holiday_day_obj in holiday_day_pool.browse(cr, uid, holiday_day_ids):
                for day_line in holiday_day_obj.holiday_day_ids:
                    if day_line.dayofweek != '6':
                        date = datetime.strptime(day_line.date, DEFAULT_SERVER_DATE_FORMAT)
                        holiday_days.append(date)
        return holiday_days
    
    def get_hr_timesheet_lines(self, cr, uid, employee_id, date_from, date_to, company_id,context=None):
        timesheet_lines = []
        if date_from and date_to:
            sql='''SELECT hrl.id hrl_id FROM general_hr_timesheet hr join general_hr_timesheet_lines hrl on hrl.hr_timesheet_id = hr.id  
                WHERE hr.state = 'approve'
                AND hr.work_date >= '%s' AND hr.work_date <= '%s' 
                AND hrl.employee_id = %s AND hr.company_id = %s ''' % (date_from, date_to, employee_id, company_id)
            cr.execute(sql)
            for line in cr.dictfetchall(): 
                hrl_id = line['hrl_id'] or False
                timesheet_lines.append(hrl_id)
        return timesheet_lines
    
    def get_worked_day_lines(self, cr, uid, contract_ids,employee_id, date_from, date_to, context=None):
        def was_on_leave(employee_id, datetime_day, usertz_vs_utctz, context=None):
            res = False
            day = datetime_day.strftime(DEFAULT_SERVER_DATE_FORMAT)
            # Thanh: Fix Timezone
            cr.execute("""SELECT id, to_char((date_from + interval '%(usertz_vs_utctz)s hour')::date, 'DD/MM/YYYY') date_from, 
            to_char((date_to + interval '%(usertz_vs_utctz)s hour')::date, 'DD/MM/YYYY') date_to FROM hr_holidays WHERE state = 'validate' AND type = 'remove'
            AND %(date)s >= (date_from + interval '%(usertz_vs_utctz)s hour')::date AND %(date)s <= (date_to + interval '%(usertz_vs_utctz)s hour')::date 
            AND %(employee_id)s = employee_id""",{'date': day,'usertz_vs_utctz': usertz_vs_utctz,'employee_id': employee_id})
            holiday_ids = cr.fetchall()  # [x[0] for x in cr.fetchall()]
            if holiday_ids and holiday_ids[0]:
                res = [self.pool.get('hr.holidays').browse(cr, uid, holiday_ids[0][0], context=context), holiday_ids[0][1], holiday_ids[0][2]]
            return res
        
        timesheet_lines = self.pool.get('general.hr.timesheet.lines')
        contract_pool = self.pool.get('hr.contract')
        company_pool = self.pool.get('res.company')
        calendar_pool = self.pool.get('resource.calendar')
        user_pool = self.pool.get('res.users')
        res = []
         # MINH: Add Number of date and Number of hours
#         cr.execute('''SELECT SUM(SALARY_WORKED) FROM GENERAL_HR_TIMESHEET_LINES A JOIN GENERAL_HR_TIMESHEET B ON A.HR_TIMESHEET_ID = B.ID WHERE B.STATE='approve' AND A.EMPLOYEE_ID='%s' AND A.WORK_DATE >= '%s' AND A.WORK_DATE <= '%s' ''' % (employee_id, date_from, date_to))
#         salary=cr.fetchall()
#         if str(salary[0][0]) != 'None':
#             salary_time=float(salary[0][0])
#         else:
#             salary_time=0.0
#         cr.execute('''SELECT SUM(A.salary_worked/A.standard_worked) AS WORKED_DATE FROM GENERAL_HR_TIMESHEET_LINES A JOIN GENERAL_HR_TIMESHEET B ON A.HR_TIMESHEET_ID = B.ID WHERE B.STATE='approve' AND A.EMPLOYEE_ID='%s' AND A.WORK_DATE >= '%s' AND A.WORK_DATE <= '%s' ''' % (employee_id, date_from, date_to))
#         woked=cr.fetchall()
#         if str(woked[0][0]) != 'None':
#             number_of_date = float(woked[0][0])
#         else:
#             number_of_date=0.0
        #############################
        for contract in contract_pool.browse(cr, uid, contract_ids, context=context):
            # fill only if the contract as a working schedule linked
            if not contract.working_hours:
                continue
            # Thanh: Add User Timezone Hours
            leaves = trial_leaves = holidays = trial_attendances = {}
            
            usertz_vs_utctz = user_pool.get_diff_hours_usertz_vs_utctz(cr, contract.employee_id.user_id.id or uid) or 7
            day_from = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
            day_to = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
            trial_date_start = trial_date_end = False
            if contract.trial_date_start:
                trial_date_start = datetime.strptime(contract.trial_date_start, DEFAULT_SERVER_DATE_FORMAT)
            if contract.trial_date_end:
                trial_date_end = datetime.strptime(contract.trial_date_end, DEFAULT_SERVER_DATE_FORMAT) or False
            
            holiday_days = self.get_holiday_day(cr, uid, day_from, day_to, contract.company_id.id, context=context) or False
            if holiday_days:
                number_of_hours = 0.0 
                for line in holiday_days:
                    working_hours_on_day = calendar_pool.working_hours_on_day(cr, uid, contract.working_hours, line, context)
                    if working_hours_on_day> 5:
                        working_hours_on_day-=contract.working_hours.break_hours
                    number_of_hours += working_hours_on_day 
                holidays={'name': "Holidays", 'sequence': 3, 'code': 'HOLIDAYS','contract_id': contract.id,
                          'number_of_days': len(holiday_days),'number_of_hours': number_of_hours}
                res += [holidays]
            if trial_date_start and trial_date_end and contract.state!='open':
                if trial_date_end <= day_to and trial_date_end >= day_from or trial_date_start <= day_to and trial_date_start >= day_from:
                    trial_attendances={'name': "Trial Working Days paid at 100%", 'sequence': 1, 'code': 'WORKTRIAL','contract_id': contract.id,'number_of_days': 0.0,'number_of_hours': 0.0}
                    if day_from > trial_date_start:
                        if day_to > trial_date_end:
                            nb_of_trialdays = (trial_date_end - day_from).days + 1
                        else:
                            nb_of_trialdays = (day_to - day_from).days + 1
                    else:
                        if day_to > trial_date_end:
                            nb_of_trialdays = (trial_date_end - trial_date_start).days + 1
                        else:
                            nb_of_trialdays = (day_to - trial_date_start).days + 1
                    for day in range(0, nb_of_trialdays):
                        date = day_from + timedelta(days=day)
                        if holiday_days and date in holiday_days:
                            continue
                        working_hours_on_day = calendar_pool.working_hours_on_day(cr, uid, contract.working_hours, date, context)
                        if working_hours_on_day:
                            days_num = 1
                            if working_hours_on_day> 5:
                                working_hours_on_day-=contract.working_hours.break_hours
                            else: 
                                days_num = 0.5
                            leave_type = was_on_leave(contract.employee_id.id, date, usertz_vs_utctz, context=context)
                            if leave_type and leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            if leave_type and not leave_type[0].id in trial_leaves:
                                if leave_type[0].id in trial_leaves:
                                    trial_leaves[leave_type[0].id]['number_of_days'] += 1.0
                                    trial_leaves[leave_type[0].id]['number_of_hours'] += working_hours_on_day
                                else:
                                    trial_leaves[leave_type[0].id] = {
                                    'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                    'sequence': 10,
                                    'code': paid_method,
                                    'number_of_days': leave_type[0].number_of_days_temp,
                                    'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                                    'contract_id': contract.id,
                                    'paid_method': leave_type[0].holiday_status_id.paid_method}
                            else:
                                trial_attendances['number_of_days'] += 1.0
                                trial_attendances['number_of_hours'] += working_hours_on_day
                    trial_leaves = [value for key, value in trial_leaves.items()]
                    for leave in trial_leaves:
                        if leave['paid_method'] == 'un-paid':
                            trial_attendances['number_of_days'] -= leave['number_of_days']
                            trial_attendances['number_of_hours'] -= leave['number_of_hours']
                    res += [trial_attendances] + trial_leaves
            
            attendances = {'name': "Normal Working Days paid at 100%", 'sequence': 2,'code': 'WORK100','number_of_days': 0.0,'number_of_hours': 0.0,'contract_id': contract.id}
            if trial_date_end and trial_attendances and day_to <= trial_date_end or trial_date_end and day_from  <= trial_date_end:
                continue
            elif trial_date_end and attendances and day_to > trial_date_end:
                day_from = trial_date_end
                nb_of_days = (day_to - day_from).days + 1
            else:
                nb_of_days = (day_to - day_from).days + 1
            if contract.working_hours.unskilled_worker:
                timesheet_ids = self.get_hr_timesheet_lines(cr, uid, contract.employee_id.id, day_from, day_to, contract.company_id.id, context=context)
                for timesheet_line_obj in timesheet_lines.browse(cr, uid, timesheet_ids):
                    work_date = datetime.strptime(timesheet_line_obj.work_date, DEFAULT_SERVER_DATE_FORMAT)
                    real_hours = timesheet_line_obj.salary_worked
                    standard_hours = 8
                    working_hours_on_day = real_hours / standard_hours 
                    leave_type = was_on_leave(contract.employee_id.id,work_date , usertz_vs_utctz, context=context)
                    if working_hours_on_day:
                        if leave_type and not leave_type[0].id in leaves:
                            if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            if leave_type[0].id in leaves:
                                leaves[leave_type[0].id]['number_of_days'] += working_hours_on_day
                                leaves[leave_type[0].id]['number_of_hours'] += real_hours
                            else:
                                leaves[leave_type[0].id] = {
                                'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                'sequence': 10,
                                'code': paid_method,
                                'number_of_days': leave_type[0].number_of_days_temp,
                                'number_of_hours': leave_type[0].number_of_days_temp * standard_hours,
                                'contract_id': contract.id,
                                'paid_method': leave_type[0].holiday_status_id.paid_method}
                        else:
                            attendances['number_of_days'] += real_hours / standard_hours
                            attendances['number_of_hours'] += real_hours
                    else:
                        if leave_type and not leave_type[0].id in leaves:
                            if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            if leave_type[0].id in leaves:
                                leaves[leave_type[0].id]['number_of_days'] += 0
                                leaves[leave_type[0].id]['number_of_hours'] += real_hours
                            else:
                                leaves[leave_type[0].id] = {
                                'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                'sequence': 10,
                                'code': paid_method,
                                'number_of_days': leave_type[0].number_of_days_temp,
                                'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                                'contract_id': contract.id,
                                'paid_method': leave_type[0].holiday_status_id.paid_method}
                day_temp = day_from
                while day_temp <= day_to:
                    working_hours_on_day = calendar_pool.working_hours_on_day(cr, uid, contract.working_hours, day_temp, context)
                    leave_type = was_on_leave(contract.employee_id.id, day_temp, usertz_vs_utctz, context=context)
                    if working_hours_on_day:
                        if working_hours_on_day> 5:
                            working_hours_on_day-=contract.working_hours.break_hours
                        # the employee had to work
                        if leave_type and not leave_type[0].id in leaves:
                            if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            # if he was on leave, fill the leaves dict
                            # Thanh: Fix Group by Leave Requests
                            if leave_type[0].id in leaves:
                                leaves[leave_type[0].id]['number_of_days'] += 1.0
                                leaves[leave_type[0].id]['number_of_hours'] += working_hours_on_day
                            else:
                                leaves[leave_type[0].id] = {
                                'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                'sequence': 10,
                                'code': paid_method,
                                'number_of_days': leave_type[0].number_of_days_temp,
                                'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                                'contract_id': contract.id,
                                'paid_method': leave_type[0].holiday_status_id.paid_method}
                    else:
                        if leave_type and not leave_type[0].id in leaves:
                            if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            if leave_type[0].id in leaves:
                                leaves[leave_type[0].id]['number_of_days'] += working_hours_on_day
                                leaves[leave_type[0].id]['number_of_hours'] += real_hours
                            else:
                                leaves[leave_type[0].id] = {
                                'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                'sequence': 10,
                                'code': paid_method,
                                'number_of_days': leave_type[0].number_of_days_temp,
                                'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                                'contract_id': contract.id,
                                'paid_method': leave_type[0].holiday_status_id.paid_method}
                    day_temp = day_temp+ timedelta(days=1)
                leaves = [value for key, value in leaves.items()]
            else:
                if not contract.working_hours:
                    continue
                nb_of_days = (day_to - day_from).days + 1
                for day in range(0, nb_of_days):
                    #Kim: Kiem tra bien day co thuoc ngay le khong
                    date = day_from + timedelta(days=day)
                    if holiday_days and date in holiday_days:
                        continue
                    working_hours_on_day = calendar_pool.working_hours_on_day(cr, uid, contract.working_hours, date, context)
                    leave_type = was_on_leave(contract.employee_id.id, date, usertz_vs_utctz, context=context)
                    if working_hours_on_day:
                        days_num = 1
                        if working_hours_on_day> 5:
                            working_hours_on_day-=contract.working_hours.break_hours
                        else: 
                            days_num = 0.5
                        # the employee had to work
                        if leave_type and not leave_type[0].id in leaves:
                            if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                                paid_method = 'unpaid'
                            else: 
                                paid_method = 'paid'
                            # if he was on leave, fill the leaves dict
                            # Thanh: Fix Group by Leave Requests
                            if leave_type[0].id in leaves:
                                leaves[leave_type[0].id]['number_of_days'] += days_num
                                leaves[leave_type[0].id]['number_of_hours'] += working_hours_on_day
                            else:
                                leaves[leave_type[0].id] = {
                                'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                                'sequence': 10,
                                'code': paid_method,
                                'number_of_days': leave_type[0].number_of_days_temp,
                                'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                                'contract_id': contract.id,
                                'paid_method': leave_type[0].holiday_status_id.paid_method}
                        # else:
                        # # add the input vals to tmp (increment if existing)
                        #     attendances['number_of_days'] += days_num
                        #     attendances['number_of_hours'] += working_hours_on_day
                    else:
                        continue
                        # if leave_type and not leave_type[0].id in leaves:
                        #     if leave_type[0].holiday_status_id.paid_method == 'un-paid':
                        #         paid_method = 'unpaid'
                        #     else:
                        #         paid_method = 'paid'
                        #     if leave_type[0].id in leaves:
                        #         leaves[leave_type[0].id]['number_of_days'] += (working_hours_on_day-contract.working_hours.break_hours)/8
                        #         leaves[leave_type[0].id]['number_of_hours'] += real_hours
                        #     else:
                        #         leaves[leave_type[0].id] = {
                        #         'name': '[' + leave_type[1] + ' / ' + leave_type[2] + '] ' + (leave_type[0].name or leave_type[0].holiday_status_id.name),
                        #         'sequence': 10,
                        #         'code': paid_method,
                        #         'number_of_days': leave_type[0].number_of_days_temp,
                        #         'number_of_hours': leave_type[0].number_of_days_temp * working_hours_on_day,
                        #         'contract_id': contract.id,
                        #         'paid_method': leave_type[0].holiday_status_id.paid_method}
                leaves = [value for key, value in leaves.items()]
                # THINH: RE-CALCULATE ATTENDANCE
                total_days = self.get_default_worked_day(cr, uid, contract.id, date_from, date_to)
                total_hours = total_days * 8
                for leave in leaves:
                    # Thanh: reduce Un-paid Leaved Days
                    if leave['paid_method'] == 'un-paid':
                        attendances['number_of_days'] -= leave['number_of_days']
                        attendances['number_of_hours'] -= leave['number_of_hours']
                    total_hours -= leave['number_of_hours']
                total_days = total_hours / 8
                attendances['number_of_days'] += total_days
                attendances['number_of_hours'] += total_hours
                #######
            res += [attendances] + leaves
        return res
    
    def compute_sheet(self, cr, uid, ids, context=None):
        context = context or {}
        worked_days_obj = self.pool.get('hr.payslip.worked_days')
        for payslip in self.browse(cr, uid, ids, context=context):
            date_from_payslip = payslip.date_from
            date_to_payslip = payslip.date_to
            day_nums = self.get_day_nums(cr, uid, ids, date_from_payslip, date_to_payslip, context)
            if not payslip.default_work_days:
                payslip.onchange_employee(date_from_payslip, date_to_payslip, payslip.employee_id)
            month_now_str = str(datetime.now())[5:7]
            job_id = payslip.employee_id.job_id.id
            if not job_id:
                raise UserError(_("Employee: '%s' must be set Job Title.") % (payslip.employee_id.name))
            # Kim: tìm hr_advance_payment dựa trên kế hoạch trả của nhân viên, lấy giá trị trả tương ứng theo tháng đăng ký 
            cr.execute('''SELECT pl.id advance_payment_id FROM hr_advance_payment p join hr_advance_payment_history pl 
                on pl.advance_payment_id = p.id WHERE p.employee_id=%s AND pl.date >= '%s' AND pl.date <='%s'   
                AND p.state = 'confirmed' AND pl.payment is False ''' % (payslip.employee_id.id, payslip.date_from, payslip.date_to))
            advance_payment_history_ids = [x[0] for x in cr.fetchall()]
            
            cr.execute('''SELECT id FROM hr_overtime WHERE employee_id=%s AND date_from >= '%s'
                AND date_to <= '%s' AND state = 'validate' ''' % (payslip.employee_id.id, payslip.date_from, payslip.date_to))
            overtime_ids = [x[0] for x in cr.fetchall()]
            self.write(cr, uid, [payslip.id], {'overtime_ids': [(6, 0, overtime_ids)],'advance_payment_history_ids': [(6, 0, advance_payment_history_ids)]}, context=context)
        
            # THANH: Load worked day instead of from onchange employee (due to it was removed)
            old_worked_days_ids = ids and worked_days_obj.search(cr, uid, [('payslip_id', '=', payslip.id)], context=context) or False
            if old_worked_days_ids:
                worked_days_obj.unlink(cr, uid, old_worked_days_ids, context=context)
            worked_days_line_ids = self.get_worked_day_lines(cr, uid, [payslip.contract_id.id],payslip.employee_id.id, payslip.date_from, payslip.date_to, context)
            worked_days_line_ids = [(0, 0, x) for x in worked_days_line_ids]
            if payslip.input_line_ids:
                for line in payslip.input_line_ids:
                    self.pool.get('hr.payslip.input').unlink(cr,uid,line.id,context=None)
            # THANH: Add salary lines
            input_line_ids = self.get_inputs(cr, uid, [payslip.contract_id.id], payslip.date_from, payslip.date_to, context=context)
            input_line_ids = [(0, 0, x) for x in input_line_ids]
            self.write(cr, uid, [payslip.id], {'worked_days_line_ids': worked_days_line_ids,'input_line_ids': input_line_ids, 'day_nums': day_nums}, context=context)
                                           
        result = super(hr_payslip, self).compute_sheet(cr, uid, ids, context)
        return result
    
    def get_payslip_lines(self, cr, uid, contract_ids, payslip_id, context):
        res = super(hr_payslip, self).get_payslip_lines(cr, uid, contract_ids, payslip_id, context)
        # Thanh: Add UoM into payslip line
        payslip_rule_pool = self.pool.get('hr.salary.rule')
        result = []
        for line in res:
            uom_id = line['salary_rule_id'] and payslip_rule_pool.browse(cr, uid, line['salary_rule_id']).uom_id.id or False
            line.update({'uom_id': uom_id})
            result.append(line)
        return result
    
    def hr_verify_sheet(self, cr, uid, ids, context=None):
        payment_history_pool = self.pool.get('hr.advance.payment.history')
        self.compute_sheet(cr, uid, ids, context)
        for payslip in self.browse(cr, uid, ids):
            for history in payslip.advance_payment_history_ids:
                payment_history = payment_history_pool.browse(cr, uid, history.id)
                payment_history_pool.write(cr, uid, [history.id], {'payment': True, 'payment_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return self.write(cr, uid, ids, {'state': 'verify'}, context=context)

hr_payslip()

class hr_payslip_timesheet(osv.osv):
    _name = 'hr.payslip.timesheet'
    _columns = {
        'rule_id': fields.many2one('hr.salary.rule', 'Salary Rule'),
        'support_type': fields.selection([
                                ('quantity', 'Quantity'),
                                ('fix_amount', 'Fixed Amount')], string="Support Type"),
        'value': fields.float('Value'),
        'quantity': fields.float('Quantity'),
        'result': fields.float('Result'),
        'payslip_id': fields.many2one('hr.payslip', 'Salary PaySlip'),
    }

class hr_payslip_line(osv.osv):
    _inherit = 'hr.payslip.line'

    _columns = {
        # Thanh: Prevent rouding Quantity for these cases (Hours, ...)
        'amount': fields.float('Amount',digits=(16, 2)),
        'quantity': fields.float('Quantity', digits_compute=dp.get_precision('Payroll Rate')),
        'uom_id': fields.many2one('product.uom', 'UoM'),
    }
    
