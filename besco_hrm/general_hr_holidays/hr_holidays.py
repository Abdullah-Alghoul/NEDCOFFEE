# -*- coding: utf-8 -*-
import datetime
from datetime import datetime
from datetime import datetime, timedelta
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
from openerp import tools, SUPERUSER_ID, api
from openerp.tools.translate import _
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from lxml import etree

DATE_FORMAT = "%Y-%m-%d"

import pytz
import math

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    
    _columns={
        'admin_hr': fields.boolean('Is Admin HR'),
    }
    
class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    _order = 'number_state asc'
    
    @api.one
    @api.depends('state')
    def _get_number_state(self):
        switcher = {
            'confirm': 0,        
            'draft': 1,
            'cancel': 2,
            'refuse': 4,
            'validate1': 5,
            'validate2': 6,
            'validate': 7,
        }
        self.number_state = switcher.get(self.state, 1) 
    
    def _check_date(self, cr, uid, ids, context=None):
        for holiday in self.browse(cr, uid, ids, context=context):
            if holiday.check_payment_leaves == False:
                domain = [
                    ('date_from', '<=', holiday.date_to),
                    ('date_to', '>=', holiday.date_from),
                    ('employee_id', '=', holiday.employee_id.id),
                    ('id', '!=', holiday.id),
                    ('state', 'not in', ['cancel', 'refuse']),
                ]
                nholidays = self.search_count(cr, uid, domain, context=context)
                if nholidays:
                    return False
        return True
    
    _columns = {
        #TOAN: number state used to order holiday by state
        #Add state validate2 (Triple validation) into Leave
        'number_state': fields.integer('Number State', compute="_get_number_state", store=True),
        'state': fields.selection([('draft', 'To Submit'), ('cancel', 'Cancelled'),('confirm', 'To Approve'), ('validate1', 'Second Approval'), ('validate2', 'Third Approval'), ('validate', 'Approved'), ('refuse', 'Refused')],
            'Status', readonly=True, track_visibility='onchange', copy=False,
            help='The status is set to \'To Submit\', when a holiday request is created.\
            \nThe status is \'To Approve\', when holiday request is confirmed by user.\
            \nThe status is \'Refused\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.'),
        'triple_validation': fields.related('holiday_status_id', 'triple_validation', type='boolean', relation='hr.holidays.status', string='Apply Triple Validation'),
        'manager_id3': fields.many2one('hr.employee', 'Third Approval', readonly=True, copy=False,
                                       help='This area is automatically filled by the user who validate the leave with third level (If Leave type need third validation)'),
        
        
        'reason_id': fields.many2one('hr.holidays.reason', 'Reason', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        'reason': fields.boolean('Has Reason'),
        'hours': fields.float('Hours'),
        'regulations': fields.text('Regulations', readonly=True, states={'draft':[('readonly',False)], 'confirm':[('readonly',False)]}),
        
        #THANH: do not send email when automatically creating allocation
        'no_send_email': fields.boolean('No send email'),
        
        #THANH: Allow edit date from, date to at any state (except cancel) and record them into holiday history
        'date_from': fields.datetime('Start Date', readonly=False, states={'validate':[('readonly',True)], 'refuse':[('readonly',True)]}, select=True, copy=False),
        'date_to': fields.datetime('End Date', readonly=False, states={'validate':[('readonly',True)], 'refuse':[('readonly',True)]}, select=True, copy=False),
        'history_ids': fields.one2many('hr.holidays.history', 'hr_holidays_id', 'History', readonly=True),
        
        #Kim: Transfer Old Leave 
        'transfer_old_leave': fields.boolean('Transfer Old Leave'),
        'check_payment_leaves': fields.boolean('Check Payment Leaves'),
    }
    
    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from', 'date_to']),
    ]
    _defaults = {
        'no_send_email': False,
        'transfer_old_leave': False,
        'check_payment_leaves':False,
    }
    
    @api.model
    def create(self, vals):
        results = super(hr_holidays, self).create(vals)
        
        #KIM: Create History
        date_from = vals.get('date_from', False)
        date_to = vals.get('date_to', False)
        days = vals.get('number_of_days_temp', False)
        hours = vals.get('hours', False)
        self.env['hr.holidays.history'].create({'hr_holidays_id': results.id , 'date_from': date_from, 'date_to': date_to, 
                                                'days': days, 'hours': hours,
                                                'user_id': self.env.uid,'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return results
    
    @api.multi
    def write(self, vals):
        if vals.get('state', False) in ('validate1', 'validate2','validate'):
            date_from = vals.get('date_from', self.date_from)
            date_to = vals.get('date_to', self.date_to)
            days = vals.get('number_of_days_temp', self.number_of_days_temp)
            hours = vals.get('hours', self.hours)
            self.env['hr.holidays.history'].create({'hr_holidays_id': self.id,'date_from': date_from, 'date_to': date_to, 
                                                    'days': days, 'hours': hours,
                                                    'user_id': self.env.uid, 'date_approve': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
        return super(hr_holidays, self).write(vals)
    
    def add_follower(self, cr, uid, ids, employee_id, context=None):
        return True
    
    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'state' in init_values and record.state == 'validate':
            return 'hr_holidays.mt_holidays_approved'
        elif 'state' in init_values and record.state == 'validate1':
            return 'hr_holidays.mt_holidays_first_validated'
        elif 'state' in init_values and record.state == 'validate2':
            #TOAN: track triple validation
            return 'general_hr_holidays.mt_holidays_second_validated'
        elif 'state' in init_values and record.state == 'confirm':
            return 'hr_holidays.mt_holidays_confirmed'
        elif 'state' in init_values and record.state == 'refuse':
            return 'hr_holidays.mt_holidays_refused'
        return super(hr_holidays, self)._track_subtype(cr, uid, ids, init_values, context=context)
    
    #THANH: Add onchange status to check contraint type
    def onchange_holiday_status(self, cr, uid, ids, holiday_status_id, date_from, context=None):
        holiday_status_obj = self.pool.get('hr.holidays.status')
        domain = warning = None
        value_content = {}
        result = {'value': {}}
        
        if holiday_status_id:
            holiday_status = holiday_status_obj.browse(cr, uid, holiday_status_id)
            args=[]
            #Toan: Regulation of Leave
            if holiday_status.regulations:
                value_content['regulations'] = holiday_status.regulations
            else:
                value_content['regulations'] = holiday_status.regulations
            #Toan: Reason when create Leave
            if holiday_status.reason:
                for line in holiday_status.reason_ids:
                    args.append(line.id)
                domain = {'reason_id': [('id', 'in', args)], 'reason': True}
                value_content['reason'] = True
            else:
                domain = {'reason_id': [('id', 'in', args)], 'reason': False}
                value_content['reason'] = False
            if date_from and holiday_status.valid_from_date and date_from < holiday_status.valid_from_date:
                warning = {
                    'title': _('Warning!'),
                    'message': _("Leave Type '%s' valid from '%s'."%(holiday_status.name, holiday_status.valid_from_date))
                }
            
            if date_from and holiday_status.valid_to_date and date_from > holiday_status.valid_to_date:
                warning = {
                    'title': _('Warning!'),
                    'message': _("Leave Type '%s' valid until '%s'."%(holiday_status.name, holiday_status.valid_to_date))
                }
        if domain:
            result['domain'] = domain
        if warning:
            result['warning'] = warning
            value_content['holiday_status_id'] = False
        result['value'] = value_content
        
        return result

#     @api.model
#     def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
#         context = self._context
#         res = super(hr_holidays, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
#                                                                 submenu=submenu)
#         if view_type in ['form']:
#             doc = etree.XML(res['arch'])
# 
#             for node in doc.xpath("//field[@name='employee_id']"):
#                 if self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id,
#                                                                  "general_hr.group_employee_manager"):
#                     employee_ids = [employee.id for employee in self.env.user.employee_id.search([('coach_id','=',self.env.user.employee_id.id)])]
#                     employee_ids_string = "["
#                     for index, employee_id in enumerate(employee_ids):
#                         if index + 1 < len(employee_ids):
#                             employee_ids_string = employee_ids_string + str(employee_id) + ","
#                         else:
#                             employee_ids_string = employee_ids_string + str(employee_id)
#                     employee_ids_string = employee_ids_string + "]"
#                     node.set('domain', "[('id','in'," + employee_ids_string + ")]")
#                     break
#                 elif self.pool.get('ir.model.access').check_groups(self.env.cr, self.env.user.id,
#                                                                  "general_hr.group_employee_coach"):
#                     employee_ids = [employee.id for employee in self.env.user.employee_id.hr_team_id.member_ids] if self.env.user.employee_id and self.env.user.employee_id.hr_team_id and self.env.user.employee_id.hr_team_id.member_ids else []
#                     employee_ids_string = "["
#                     for index, employee_id in enumerate(employee_ids):
#                         if index+ 1 < len(employee_ids):
#                             employee_ids_string = employee_ids_string + str(employee_id)+ ","
#                         else:
#                             employee_ids_string = employee_ids_string + str(employee_id)
#                     employee_ids_string = employee_ids_string + "]"
#                     node.set('domain', "[('id','in'," + employee_ids_string + ")]")
#             xarch, xfields = self._view_look_dom_arch(doc, view_id, context=context)
#             res['arch'] = xarch
#             res['fields'] = xfields
#         return res

    def onchange_date_to(self, cr, uid, ids, date_to, date_from):
        """
        Update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        result = {'value': {}}

        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(math.floor(diff_day))+1
            date_format = "%Y-%m-%d %H:%M:%S"
#             result['value']['hours'] = ((datetime.strptime(date_to, date_format) - datetime.strptime(date_from, date_format)).days) * 24.0 + (datetime.strptime(date_to, date_format) - datetime.strptime(date_from, date_format)).seconds / 60.0 / 60.0
            result['value']['hours'] = (round(math.floor(diff_day))+1) * 8  
        else:
            result['value']['number_of_days_temp'] = 0
            result['value']['hours'] = 0
        return result
    
    def onchange_date_from(self, cr, uid, ids, date_to, date_from, holiday_status_id=None):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise UserError(_('The start date must be anterior to the end date.'))

        result = {'value': {}}
        
        #THANH: Check date from with holiday status rule (Valid From and Valid To)
        result = self.onchange_holiday_status(cr, uid, ids, holiday_status_id, date_from)
        
        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            diff_day = self._get_number_of_days(date_from, date_to)
            result['value']['number_of_days_temp'] = round(math.floor(diff_day))+1
            date_format = "%Y-%m-%d %H:%M:%S"
#             result['value']['hours'] = ((datetime.strptime(date_to, date_format) - datetime.strptime(date_from, date_format)).days) * 24.0 + (datetime.strptime(date_to, date_format) - datetime.strptime(date_from, date_format)).seconds / 60.0 / 60.0
            result['value']['hours'] = (round(math.floor(diff_day))+1) * 8
        else:
            result['value']['number_of_days_temp'] = 0
            result['value']['hours'] = 0
        return result
     
    def onchange_employee(self, cr, uid, ids, employee_id):
        result = {'value': {'department_id': False,
                            #THANH: Set type is False to re-check type rule when chosen
                            'holiday_status_id': False}}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            result['value'] = {'department_id': employee.department_id.id}
        return result
    
    def get_recipient(self, cr, uid, ids, context=None):
        recipients = self.pool.get('res.partner')
        temp = []
        this = self.browse(cr, uid, ids[0])
        employee = self.pool.get('hr.employee').browse(cr, uid, this.employee_id.id, context=context)
        if employee and employee.user_id:
            temp.append(employee.name)
            manager = self.pool.get('hr.employee').browse(cr, uid, employee.parent_id.id, context=context)
            if manager and manager.user_id:
                temp.append(manager.name)
            coach = self.pool.get('hr.employee').browse(cr, uid, employee.coach_id.id, context=context)
            if coach and coach.user_id:
                temp.append(coach.name)
        
        reciept_ids = recipients.search(cr, uid, [('name','in',temp)])
        return recipients.browse(cr,uid, reciept_ids)
    
        #TOAN: Check Coach or Manager Approve our Leave
    def _check_state_access_right(self, cr, uid, vals, context=None):
#         if vals.get('state') and vals['state'] not in ['draft', 'confirm', 'cancel'] and not self.pool['res.users'].has_group(cr, uid, 'base.group_hr_user'):
#             return False
        return True
    
    def holidays_reset(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
            'manager_id': False,
            'manager_id2': False,
            #TOAN: reset field manager_id3
            'manager_id3': False,
        })
        to_unlink = []
        for record in self.browse(cr, uid, ids, context=context):
            for record2 in record.linked_request_ids:
                self.holidays_reset(cr, uid, [record2.id], context=context)
                to_unlink.append(record2.id)
        if to_unlink:
            self.unlink(cr, uid, to_unlink, context=context)
        return True
    
    @api.multi
    def holidays_confirm(self):
        self.write({'state': 'confirm'})
        
        MailMessage = self.env['mail.message']
        emails = self.env['mail.mail']
        for record in self:
            if record.no_send_email:
                #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
                continue
            
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')
            if record.employee_id.coach_id and record.employee_id.coach_id.user_id:
                tz = pytz.timezone(record.employee_id.coach_id.user_id._get_user_tz())
                body = False
                #body: Time
                date_from = date_to = ''
                if record.date_from:
                    date_from = str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
                if record.date_to:
                    date_to = str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
                body = 'From ' + date_from + ' to ' + date_to
                #body: Description
                body = body + '<br><br> Description: <br>' + _(record.name)
                #body: Reason
                if record.reason_id:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name) + ' with ' + _(record.reason_id.name)
                else:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name)
                #body: Regulations
                if record.regulations:
                    body = body + '<br><br> Regulations: <br>' + _(record.regulations)
                values = {
                    'model': 'hr.holidays',
                    'res_id': record.id,
                    'body': body,
                    'subject': 'New Leave Request',
                    'partner_ids': [(4, record.employee_id.coach_id.user_id.partner_id.id)]
                }
                partner = record.employee_id.coach_id.user_id.partner_id
                # Avoid warnings about non-existing fields
                for x in ('from', 'to', 'cc'):
                    values.pop(x, None)
        
                # Post the message
                new_message = MailMessage.create(values)
                
                base_template_ctx = partner._notify_prepare_template_context(new_message)
                base_mail_values = partner._notify_prepare_email_values(new_message)
                
                recipients = self._message_notification_recipients(new_message, partner)
                for email_type, recipient_template_values in recipients.iteritems():
                    # generate notification email content
                    template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                    template_fol_values['button_follow'] = True
                    template_fol = base_template.with_context(**template_fol_values)
                    
                    # generate templates for followers and not followers
                    fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
                    
                    # send email
                    new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                    emails |= new_emails
                emails.send()
        return True
    
    @api.multi
    def holidays_first_validate(self):
        if self.env['ir.model.access'].check_groups("general_hr.group_employee_coach") and self.employee_id.user_id.id == self.env.user.id:
            raise UserError(_("You can not Approve this Leave request. Please contact your manager '%s'.")%(self.employee_id.coach_id.name))
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self.env.user.id)])
        manager = ids2 and ids2[0] or False
        if not manager:
            raise UserError('You are not created as an Employee in menu Employees / Employees. Please contact administrator!')
        
        self.write({'state': 'validate1', 'manager_id': manager.id})
        
        #TOAN: check send_email
        MailMessage = self.env['mail.message']
        emails = self.env['mail.mail']
        for record in self:
            if record.no_send_email:
                #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
                continue
        
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')
            if record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                tz = pytz.timezone(record.employee_id.parent_id.user_id._get_user_tz())
                body = False
                #body: Time
                body = 'From ' + str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19] + ' to ' + str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
                #body: Description
                body = body + '<br><br> Description: <br>' + _(record.name)
                #body: Reason
                if record.reason_id:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name) + ' with ' + _(record.reason_id.name)
                else:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name)
                #body: Regulations
                if record.regulations:
                    body = body + '<br><br> Regulations: <br>' + _(record.regulations)
                values = {
                    'model': 'hr.holidays',
                    'res_id': record.id,
                    'body': body,
                    'subject': 'First Approved',
                    'partner_ids': [(4, record.employee_id.parent_id.user_id.partner_id.id)]
                }
                
                # Avoid warnings about non-existing fields
                for x in ('from', 'to', 'cc'):
                    values.pop(x, None)
        
                # Post the message
                new_message = MailMessage.create(values)
                
                partner = record.employee_id.parent_id.user_id.partner_id
                base_template_ctx = partner._notify_prepare_template_context(new_message)
                base_mail_values = partner._notify_prepare_email_values(new_message)
                
                recipients = self._message_notification_recipients(new_message, partner)
                for email_type, recipient_template_values in recipients.iteritems():
                    # generate notification email content
                    template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                    template_fol_values['button_follow'] = False
                    template_fol = base_template.with_context(**template_fol_values)
                    # generate templates for followers and not followers
                    fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
                    # send email
                    new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                    emails |= new_emails
                emails.send()
        return True
    
    @api.multi
    def holidays_second_validate(self):
        obj_emp = self.env['hr.employee']
        ids3 = obj_emp.search([('user_id', '=',self.env.user.id)])
        manager = ids3 and ids3[0] or False
        if not manager:
            raise UserError('You are not created as an Employee in menu Employees / Employees. Please contact administrator!')
        
        self.write({'state': 'validate2', 'manager_id2': manager.id})
        
        #TOAN: check send_email
        MailMessage = self.env['mail.message']
        emails = self.env['mail.mail']
        for record in self:
            if record.no_send_email:
                #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
                continue
        
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')
            admin_ids = self.env['hr.employee'].search([('admin_hr','=',True)])
            if len(admin_ids) > 1:
                raise UserError(_('Must be set one Admin-HR. Now, set %s Admin-HR')%len(admin_ids))
            elif len(admin_ids) == 0:
                raise UserError(_('Must be set one Admin-HR'))
            else:
                admin = self.env['hr.employee'].browse(admin_ids.id)
            if admin.user_id.partner_id:
                tz = pytz.timezone(admin.user_id._get_user_tz())
                body = False
                #body: Time
                body = 'From ' + str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19] + ' to ' + str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
                #body: Description
                body = body + '<br><br> Description: <br>' + _(record.name)
                #body: Reason
                if record.reason_id:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name) + ' with ' + _(record.reason_id.name)
                else:
                    body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name)
                #body: Regulations
                if record.regulations:
                    body = body + '<br><br> Regulations: <br>' + _(record.regulations)
                values = {
                    'model': 'hr.holidays',
                    'res_id': record.id,
                    'body': body,
                    'subject': 'Second Approved',
                    'partner_ids': [(4, admin.user_id.partner_id.id)]
                }
                # Avoid warnings about non-existing fields
                for x in ('from', 'to', 'cc'):
                    values.pop(x, None)
        
                # Post the message
                new_message = MailMessage.create(values)
                
                partner = admin.user_id.partner_id
                base_template_ctx = partner._notify_prepare_template_context(new_message)
                base_mail_values = partner._notify_prepare_email_values(new_message)
                
                recipients = self._message_notification_recipients(new_message, partner)
                for email_type, recipient_template_values in recipients.iteritems():
                    # generate notification email content
                    template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                    template_fol_values['button_follow'] = False
                    template_fol = base_template.with_context(**template_fol_values)
                    
                    # generate templates for followers and not followers
                    fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
                    
                    # send email
                    new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                    emails |= new_emails
                emails.send()
        return True
    
    @api.multi
    def holidays_validate(self):
#         if self.pool['ir.model.access'].check_groups(cr, uid, "general_hr.group_employee_coach") and this.employee_id.user_id.id == uid:
#             raise UserError(_("You can not Approve this Leave request. Please contact your manager '%s'.")%(this.employee_id.coach_id.name))
#         if self.pool['ir.model.access'].check_groups(cr, uid, "general_hr.group_employee_manager") and this.employee_id.user_id.id == uid:
#             raise UserError(_("You can not Approve this Leave request. Please contact HR Admin."))
        
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self.env.user.id)])
        manager = ids2 and ids2[0] or False
        resource_pool = self.env['resource.resource']
        if not manager:
            raise UserError('You are not created as an Employee in menu Employees / Employees. Please contact administrator!')
        if self.no_send_email:
            self.write({'state': 'validate'})
            return True
        self.write({'state': 'validate'})
        
        partner_ids = False
        for record in self:
            partner_ids = record.employee_id.user_id.partner_id.id
            #TOAN: Check double validation
            if record.double_validation:
                self.write({'manager_id2': manager.id})
                manager_obj = obj_emp.browse(manager.id)
                emp_obj = obj_emp.browse(record.employee_id.id)
                if emp_obj.parent_id.id == manager_obj.id or self.env['ir.model.access'].check_groups("general_hr.group_employee_manager") or self.env['ir.model.access'].check_groups("base.group_hr_user"):
                    self.write({'manager_id2': manager.id})
                else: 
                    raise UserError(_('You have not permission. Please contact HR Manager or your Division Head.'))
            #TOAN: Check triple validation
            elif record.triple_validation:
                manager_obj = obj_emp.browse(manager.id) 
                is_hr_manager =  self.env['ir.model.access'].check_groups("base.group_hr_manager")
                is_hr_manager2 = self.env['ir.model.access'].check_groups("base.group_hr_user")
                if is_hr_manager or is_hr_manager2 or manager_obj.admin_hr :
                    self.write({'manager_id3': manager.id})
                else:
                    raise UserError(_('You have not permission. Please contact HR Manager or Admin HR.'))
            else:
                self.write({'manager_id': manager.id})
                
            if record.holiday_type == 'employee' and record.type == 'remove':
                meeting_vals = {
                    'name': record.display_name,
                    'categ_ids': record.holiday_status_id.categ_id and [(6,0,[record.holiday_status_id.categ_id.id])] or [],
                    'duration': record.number_of_days_temp * 8,
                    'description': record.notes,
                    'user_id': record.user_id.id,
                    'start': record.date_from,
                    'stop': record.date_to,
                    'allday': False,
                    'state': 'open', # to block that meeting date in the calendar
                    'class': 'confidential'
                }
                #Add the partner_id (if exist) as an attendee
                if record.user_id and record.user_id.partner_id:
                    meeting_vals['partner_ids'] = [(4,record.user_id.partner_id.id)]

                #Toan: return Attendance
                if record.reason_id:
                    emp_obj = obj_emp.browse(record.employee_id)
                    date_from = str(record.date_from)[0:10]
                    date_to = str(record.date_to)[0:10]
                    sql = """SELECT id FROM hr_attendance WHERE available_late = True OR leave_soon = True AND action = 'sign_in' OR action = 'action' AND to_char(name,'yyyy-mm-dd') BETWEEN '%s' AND '%s'"""%(date_from, date_to)
            elif record.holiday_type == 'category':
                emp_ids = record.category_id.employee_ids.ids
                leave_ids = []
                for emp in obj_emp.browse(emp_ids):
                    vals = {
                        'name': record.name,
                        'type': record.type,
                        'holiday_type': 'employee',
                        'holiday_status_id': record.holiday_status_id.id,
                        'date_from': record.date_from,
                        'date_to': record.date_to,
                        'notes': record.notes,
                        'number_of_days_temp': record.number_of_days_temp,
                        'parent_id': record.id,
                        'employee_id': emp.id
                    }
                    leave_ids.append(self.create(vals))
                for leave_id in leave_ids:
                    # TODO is it necessary to interleave the calls?
                    for sig in ('confirm', 'validate', 'second_validate', 'third_validate'):
                        self.signal_workflow([leave_id], sig)
                    
        #TOAN: check send_email
        for record in self:
            if record.no_send_email or not record.employee_id.user_id or record.type == 'add':
                #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
                continue
            MailMessage = self.env['mail.message']
            emails = self.env['mail.mail']
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')
            sql = '''SELECT code, name_related FROM hr_employee where id = %s'''%record.employee_id.id
            self.env.cr.execute(sql)
            employee_name = self.env.cr.fetchone()
            
            if not employee_name:
                raise UserError('Employee name is not valid!')
            
            resource_obj = resource_pool.search([('id','=',record.employee_id.id)])
            partner_obj = self.env['res.partner'].search([('user_id','=',resource_obj.user_id.id)])
            
            tz = pytz.timezone(resource_obj.user_id._get_user_tz())
            body = False
            #body: Time
            body = 'From ' + str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19] + ' to ' + str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
            #body: Reason
            if record.reason_id:
                body = _(body) + u' <br><br>' + _(employee_name[0]) + u'-' + _(employee_name[1]) + u' - ' + _(record.holiday_status_id.name) + _(' (') + _(record.reason_id.name) + _(')')
            else:
                body = _(body) + _(' <br><br>') + _(employee_name[0]) + _('-') + _(employee_name[1]) + _(' - ') + _(record.holiday_status_id.name)
            #body: Description
            body = body + '<br><br> Description: <br>' + record.name
            body = body + '<br><br> Status: Confirm -> Approved'
                
            if partner_ids:
                values = {
                    'model': 'hr.holidays',
                    'res_id': record.id,
                    'body': body,
                    'subject': 'Validated Request',
                    'partner_ids': [(4, partner_ids)]
                }
                # Avoid warnings about non-existing fields
                for x in ('from', 'to', 'cc'):
                    values.pop(x, None)
        
                # Post the message
                new_message = MailMessage.create(values)
                partner = partner_obj
                base_template_ctx = partner._notify_prepare_template_context(new_message)
                base_mail_values = partner._notify_prepare_email_values(new_message)
                
                recipients = self._message_notification_recipients(new_message, partner)
                for email_type, recipient_template_values in recipients.iteritems():
                    # generate notification email content
                    template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
                    template_fol_values['button_follow'] = False
                    template_fol = base_template.with_context(**template_fol_values)
                    # generate templates for followers and not followers
                    fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
                    # send email
                    new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
                    emails |= new_emails
                emails.send() 
                                
                                
        return True
    
    @api.multi
    def holidays_refuse(self):
        obj_emp = self.env['hr.employee']
        ids2 = obj_emp.search([('user_id', '=', self.env.user.id)])
        manager = ids2 and ids2[0] or False
        if not manager:
            manager = SUPERUSER_ID
        for holiday in self:
            if holiday.state == 'validate1':
                self.write({'state': 'refuse', 'manager_id': manager.id})
            elif holiday.state == 'validate2':
                self.write({'state': 'refuse', 'manager_id2': manager.id})
            else: 
                self.write({'state': 'refuse', 'manager_id3': manager.id})
        self.holidays_cancel()
        
        #TOAN: check send_email
        MailMessage = self.env['mail.message']
        emails = self.env['mail.mail']
        for record in self:
            if record.no_send_email:
                #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
                continue
            
            tz = pytz.timezone(record.employee_id.coach_id.user_id._get_user_tz())
            base_template = self.env.ref('mail.mail_template_data_notification_email_default')
            
            body = False
            #body: Time
            body = 'From ' + str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19] + ' to ' + str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
            #body: Description
            body = body + '<br><br> Description: <br>' + _(record.name)
            #body: Reason
            if record.reason_id:
                body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name) + ' with ' + _(record.reason_id.name)
            else:
                body = body + ' <br><br>' + record.employee_id.code + '-' + _(record.employee_id.name) + ' - ' + _(record.holiday_status_id.name)
            body = body + '<br><br> Status: Confirm -> Refuse'
                
#             if record.employee_id.coach_id and record.employee_id.coach_id.user_id:
            partner = False
            if record.employee_id.parent_id :
                partner = [(4,record.employee_id.parent_id.user_id.partner_id.id)]
            elif record.employee_id.user_id:
                partner = [(4, record.employee_id.user_id.partner_id.id)]
            values = {
                'model': 'hr.holidays',
                'res_id': record.id,
                'body': body,
                'subject': 'Refused Request',
                'partner_ids': partner,
#                     'partner_ids': [(4, record.employee_id.user_id.partner_id.id)],
            }
            if record.reason_id:
                values['body'] = values['body'] + ' with ' + _(record.reason_id.name)
            # Avoid warnings about non-existing fields
            for x in ('from', 'to', 'cc'):
                values.pop(x, None)
    
            # Post the message
            new_message = MailMessage.create(values)
            
#             partner = record.employee_id.user_id.partner_id
#             base_template_ctx = partner._notify_prepare_template_context(new_message)
#             base_mail_values = partner._notify_prepare_email_values(new_message)
#             
#             recipients = self._message_notification_recipients(new_message, partner)
#             for email_type, recipient_template_values in recipients.iteritems():
#                 # generate notification email content
#                 template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
#                 template_fol_values['button_follow'] = False
#                 template_fol = base_template.with_context(**template_fol_values)
#                 
#                 # generate templates for followers and not followers
#                 fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
#                 
#                 # send email
#                 new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
#                 emails |= new_emails
#             emails.send()
#             send = True
        return True
    
hr_holidays()

class hr_holidays_history(osv.osv):
    _name = "hr.holidays.history"
    _columns = {
        'user_id': fields.many2one('res.users', 'Approved By', copy=False),
        'date_approve': fields.datetime('Approved Date', copy=False),
        'date_from': fields.datetime('Start Date'),
        'date_to': fields.datetime('End Date'),
        'days': fields.float('Days'),
        'hours': fields.float('Hours'),
        'state': fields.selection([('draft','To Submit'),('cancel','Cancelled'),('confirm','To Approve'),
            ('validate1','Second Approval'),('validate2', 'Third Approval'), ('validate','Approved'),('refuse','Refused')],
            'Status', readonly=True, track_visibility='onchange', copy=False),
        'hr_holidays_id': fields.many2one('hr.holidays', string="Hr Holidays", ondelete='cascade'),
        }
hr_holidays_history()

class hr_holidays_status(osv.osv):
    _inherit = "hr.holidays.status"
    _columns = {
                'triple_validation': fields.boolean('Apply Triple Validation', help="When selected, the Allocation/Leave Requests for this type require a third validation to be approved."),
                
                'paid_method' : fields.selection([('paid','Paid'),('un-paid','Un-paid')], 'Paid/Un-Paid', required=False),
                'valid_from_date': fields.date('Valid From'),
                'valid_to_date': fields.date('Valid To'),
                'reason': fields.boolean('Has Reason'),
                'reason_ids': fields.one2many('hr.holidays.reason', 'hr_holidays_status_id', 'Reasons'),
                'regulations': fields.text('Regulations'),
                
                #THANH: Bonus by worked years (Only for annual leave)
                'legal_leaves': fields.boolean('Is Annual Leave', help="When selected, Auto add more leaves for the employee based on the worked years."),
                'from_worked_years': fields.integer('From Worked Years'),
                'number_of_year': fields.integer('Number of Years'),
                'rounding_worked_years': fields.boolean('Rounding Worked Years'),
                'bonus_days': fields.float('Bonus Days'),
                'allocation_ids': fields.many2many('hr.holidays', 'allocation_hr_holidays_status_rel','hr_holidays_status_id', 'hr_holidays_id', 'Allocations', readonly=True), 
            }
    
class hr_holidays_reason(osv.osv):
    _name = "hr.holidays.reason"
    _columns = {
        'name': fields.char('Name', required=False),
        'hr_holidays_status_id': fields.many2one('hr.holidays.status')
    }
    
hr_holidays_status()
    