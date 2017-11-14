# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import _, api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import UserError

class Job(models.Model):
    _inherit = "hr.job"
    
    name_vn = fields.Char('Job Name VN')
    
    @api.multi
    def name_get(self):
        res = []
        for job in self:
            if job.name_vn:
                name = job['name'] + " / " + job['name_vn']
            else:
                name = job['name']
            res.append((job['id'], name))
        return res

class Applicant(models.Model):
    _inherit = "hr.applicant"
    
    identification_id = fields.Char('Identification No')
    insurance_number = fields.Char('Insurance Number')
    tin = fields.Char('TIN')
    notes = fields.Text('Notes')
    dup_employee_id = fields.Many2one('hr.employee', 'Duplicate Employee')
    
    @api.multi
    def check_duplicate_employee(self):
        check = {'identification_id' :False, 
                 'insurance_number': False, 
                 'tin': False}
        notes = ''
        if self.identification_id:
            check['identification_id'] = True
        if self.insurance_number:
            check['insurance_number'] = True
        if self.tin:
            check['tin'] = True
            
        sql = """SELECT id FROM hr_employee WHERE"""
        if check['identification_id']:
            notes += 'Identification No, '
            sql += """ identification_id = '%s' OR"""%self.identification_id
        if check['insurance_number']:
            notes += 'Insurance Number, '
            sql += """ insurance_number = '%s' OR"""%self.insurance_number
        if check['tin']:
            notes += 'TIN, '
            sql += """ tin = '%s' OR"""%self.tin
        sql = sql.rstrip(' OR')
        notes = notes.rstrip(', ')
        active_employee_ids = False
        if len(notes) > 0:
            self.env.cr.execute(sql)
            active_employee_ids = self.env.cr.fetchone()
        
        if active_employee_ids:
            if len(active_employee_ids) > 1:
                raise UserError(_('Your data was duplicated.'))
            else:
                self.dup_employee_id = active_employee_ids[0]
                employee_obj = self.env['hr.employee'].browse(active_employee_ids[0])
                self.notes = notes
                raise UserError(_("Your data was duplicated.\n Employee: '%s-%s' with: %s")%(employee_obj.code, employee_obj.name_related, notes))
            return True
        else:
            return False
        
    @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        check_dup = self.check_duplicate_employee()
        if not check_dup:
            employee = False
            for applicant in self:
                address_id = contact_name = False
                if applicant.partner_id:
                    address_id = applicant.partner_id.address_get(['contact'])['contact']
                    contact_name = applicant.partner_id.name_get()[0][1]
                if applicant.job_id and (applicant.partner_name or contact_name):
                    applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                    employee = self.env['hr.employee'].create({'name': applicant.partner_name or contact_name,
                                                   'job_id': applicant.job_id.id,
                                                   'address_home_id': address_id,
                                                   'department_id': applicant.department_id.id or False,
                                                   'address_id': applicant.company_id and applicant.company_id.partner_id and applicant.company_id.partner_id.id or False,
                                                   'work_email': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.email or False,
                                                   'work_phone': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.phone or False,
                                                   'identification_id': applicant.identification_id or False,
                                                   'insurance_number': applicant.insurance_number or False,
                                                   'tin': applicant.tin or False,
                                                   })
                    applicant.write({'emp_id': employee.id})
                    applicant.job_id.message_post(
                        body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                        subtype="hr_recruitment.mt_job_applicant_hired")
                    employee._broadcast_welcome()
                else:
                    raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))
    
            employee_action = self.env.ref('hr.open_view_employee_list')
            dict_act_window = employee_action.read([])[0]
            if employee:
                dict_act_window['res_id'] = employee.id
            dict_act_window['view_mode'] = 'form,tree'
            return dict_act_window