# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.exceptions import UserError, AccessError

class hr_holidays(osv.osv):
    _inherit = "hr.holidays"
    _columns = {
    }
    
    def recomputing_payslip(self, cr, uid, ids, context=None):
        context = context or {}
        payslip_pool = self.pool.get('hr.payslip')
        
        for line in self.browse(cr, uid, ids):
            if line.type == 'remove':
                cr.execute('''
                SELECT id, number, state
                FROM hr_payslip
                WHERE employee_id=%s AND date_to >= '%s' AND date_from <='%s' 
                ''' % (line.employee_id.id, line.date_to, line.date_from))
                res = cr.fetchall()
                for payslip in res:
                    if payslip[2] == 'done':
                        raise UserError(_('Warning!'), _("Payslip number '%s' has been paid!\n You are not able to approve this Leave Request!") % (payslip[1]))
                if res:
                    context['reload_worked_lines'] = True
                    payslip_pool.compute_sheet(cr, uid, [x[0] for x in res], context)
        return True
    
    def holidays_validate(self, cr, uid, ids, context=None):
        super(hr_holidays, self).holidays_validate(cr, uid, ids, context)
        self.recomputing_payslip(cr, uid, ids, context)
        return True

    def holidays_cancel(self, cr, uid, ids, context=None):
        super(hr_holidays, self).holidays_cancel(cr, uid, ids, context)
        self.recomputing_payslip(cr, uid, ids, context)
        return True
    
hr_holidays()
    
