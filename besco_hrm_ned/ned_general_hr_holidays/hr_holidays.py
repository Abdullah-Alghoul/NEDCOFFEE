# -*- coding: utf-8 -*-
import datetime
from datetime import date
from openerp.exceptions import UserError, AccessError
from openerp.osv import fields, osv
from openerp import tools, api
from openerp.tools.translate import _
from lxml import etree
DATE_FORMAT = "%Y-%m-%d"

import pytz
import math

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    _columns={
              #Kim: Transfer Old Leave
              'transfer_old_leave': fields.boolean('Transfer Old Leave'),
              }
    
    _defaults={
               'transfer_old_leave': False
               }
    
#     def holidays_first_validate(self, cr, uid, ids, context=None):
#         this = self.browse(cr, uid, ids[0])
#         if self.pool['ir.model.access'].check_groups(cr, uid, "general_hr.group_employee_coach") and this.employee_id.user_id.id == uid:
#             raise UserError(_("You can not Approve this Leave request. Please contact your manager '%s'.")%(this.employee_id.coach_id.name))
#         obj_emp = self.pool.get('hr.employee')
#         ids2 = obj_emp.search(cr, uid, [('user_id', '=', uid)])
#         manager = ids2 and ids2[0] or False
#         return self.write(cr, uid, ids, {'state': 'validate1', 'manager_id': manager}, context=context)
    
#     @api.multi
#     def holidays_validate(self):
#         if self.env['ir.model.access'].check_groups("general_hr.group_employee_coach") and self.employee_id.user_id.id == self.env.user.id:
#             raise UserError(_("You can not Approve this Leave request. Please contact your manager '%s'.")%(self.employee_id.coach_id.name))
#         if self.env['ir.model.access'].check_groups("general_hr.group_employee_manager") and self.employee_id.user_id.id == self.env.user.id:
#             raise UserError(_("You can not Approve this Leave request. Please contact HR Admin."))
#         obj_emp = self.env['hr.employee']
#         ids2 = obj_emp.search([('user_id', '=', self.env.user.id)])
#         manager = ids2 and ids2[0] or False
#         resource_pool = self.env['resource.resource']
#         self.write({'state': 'validate'})
#         for record in self:
#             if record.double_validation:
#                 self.write({'manager_id2': manager.id})
#             else:
#                 self.write({'manager_id': manager.id})
#             if record.holiday_type == 'employee' and record.type == 'remove':
#                 meeting_vals = {
#                     'name': record.display_name,
#                     'categ_ids': record.holiday_status_id.categ_id and [(6,0,[record.holiday_status_id.categ_id.id])] or [],
#                     'duration': record.number_of_days_temp * 8,
#                     'description': record.notes,
#                     'user_id': record.user_id.id,
#                     'start': record.date_from,
#                     'stop': record.date_to,
#                     'allday': False,
#                     'state': 'open', # to block that meeting date in the calendar
#                     'class': 'confidential'
#                 }
#                 #Add the partner_id (if exist) as an attendee
#                 if record.user_id and record.user_id.partner_id:
#                     meeting_vals['partner_ids'] = [(4,record.user_id.partner_id.id)]
#             elif record.holiday_type == 'category':
#                 emp_ids = record.category_id.employee_ids.ids
#                 leave_ids = []
#                 for emp in obj_emp.browse(emp_ids):
#                     vals = {
#                         'name': record.name,
#                         'type': record.type,
#                         'holiday_type': 'employee',
#                         'holiday_status_id': record.holiday_status_id.id,
#                         'date_from': record.date_from,
#                         'date_to': record.date_to,
#                         'notes': record.notes,
#                         'number_of_days_temp': record.number_of_days_temp,
#                         'parent_id': record.id,
#                         'employee_id': emp.id
#                     }
#                     leave_ids.append(self.create(vals))
#                 for leave_id in leave_ids:
#                     # TODO is it necessary to interleave the calls?
#                     for sig in ('confirm', 'validate', 'second_validate'):
#                         self.signal_workflow([leave_id], sig)
#         
#         MailMessage = self.env['mail.message']
#         emails = self.env['mail.mail']
#         for record in self:
#             if record.no_send_email:
#                 #THANH: Do not send email if the request validate auto from Configuration of Leave Type (Generate Allocation Request)
#                 continue
#             
#             base_template = self.env.ref('mail.mail_template_data_notification_email_default')
#             sql = '''SELECT code, name_related FROM hr_employee where id = %s'''%record.employee_id.id
#             self.env.cr.execute(sql)
#             employee_name = self.env.cr.fetchone()
#             
#             if not employee_name:
#                 raise UserError('Employee name is not valid!')
#             
#             resource_obj = resource_pool.search([('id','=',record.employee_id.id)])
#             partner_obj = self.env['res.partner'].search([('user_id','=',resource_obj.user_id.id)])
#             
#             tz = pytz.timezone(resource_obj.user_id._get_user_tz())
#             body = False
#             #body: Time
#             body = 'From ' + str(datetime.strptime(record.date_from, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19] + ' to ' + str(datetime.strptime(record.date_to, '%Y-%m-%d %H:%M:%S').replace(tzinfo=pytz.utc).astimezone(tz))[0:19]
#             #body: Description
#             body = body + '<br><br> Description: <br>' + _(record.name)
#             #body: Reason
#             if record.reason_id:
#                 body = body + ' <br><br>' + _(employee_name[0]) + '-' + _(employee_name[1]) + ' - ' + _(record.holiday_status_id.name) + ' with ' + _(record.reason_id.name)
#             else:
#                 body = body + ' <br><br>' + _(employee_name[0]) + '-' + _(employee_name[1]) + ' - ' + _(record.holiday_status_id.name)
#             body = body + '<br><br> Status: Confirm -> Approved'
#             
#             if partner_obj:
#                 values = {
#                     'model': 'hr.holidays',
#                     'res_id': record.id,
#                     'body': body,
#                     'subject': 'Validated Request',
#                     'partner_ids': [(4, partner_obj[0].id or False), (4, record.employee_id.parent_id.partner_id.user_id.id or False)]
#                 }
#                 if record.reason_id:
#                     values['body'] = values['body'] + ' with ' + _(record.reason_id.name)
#                 # Avoid warnings about non-existing fields
#                 for x in ('from', 'to', 'cc'):
#                     values.pop(x, None)
#         
#                 # Post the message
#                 new_message = MailMessage.create(values)
#                 partner = partner_obj
#                 base_template_ctx = partner._notify_prepare_template_context(new_message)
#                 base_mail_values = partner._notify_prepare_email_values(new_message)
#                 
#                 recipients = self._message_notification_recipients(new_message, partner)
#                 for email_type, recipient_template_values in recipients.iteritems():
#                     # generate notification email content
#                     template_fol_values = dict(base_template_ctx, **recipient_template_values)  # fixme: set button_unfollow to none
#                     template_fol_values['button_follow'] = False
#                     template_fol = base_template.with_context(**template_fol_values)
#                     # generate templates for followers and not followers
#                     fol_values = template_fol.generate_email(new_message.id, fields=['body_html', 'subject'])
#                     # send email
#                     new_emails, new_recipients_nbr = partner._notify_send(fol_values['body'], fol_values['subject'], recipient_template_values['followers'], **base_mail_values)
#                     emails |= new_emails
#                 emails.send()                
#         return True
    
class hr_holidays_status(osv.osv):
    _inherit = "hr.holidays.status"
 
    _columns = {
        'leave_type_code' : fields.char('Leave Code', required=True, size=6)
    }
    
class hr_holidays_reason(osv.osv):
    _inherit = "hr.holidays.reason"
    _columns = {
        'reason_code': fields.char('Reason Code', required=True)
    }
    
    def _check_unique(self, cr, uid, ids, context=None):
        for reason in self.browse(cr, uid, ids, context=context):
            if self.search(cr, uid, [('reason_code', '=', reason.reason_code), ('id', '!=', reason.id)]):
                return False
        return True

    _constraints = [
        (_check_unique, '''Reason Code has existed''', ['reason_code']),
    ]

    