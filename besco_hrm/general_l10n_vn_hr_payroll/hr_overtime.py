# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.exceptions import UserError, AccessError

class hr_overtime(osv.osv):
    _inherit = "hr.overtime"
    
    def _compute_calculated_hours(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for overtime in self.browse(cr, uid, ids, context=context):
            res[overtime.id] = round(overtime.rate * overtime.number_of_hours_temp / 100, 2)
        return res
    
    _columns = {
        'rate': fields.float('Rate (%)', digits=(16, 2), required=False, readonly=True, states={'draft':[('readonly', False)], 'confirm':[('readonly', False)]}),
        
        'calculated_hours': fields.function(_compute_calculated_hours, string='Calculated Hours', type='float', digits=(16, 2),
            store={
                'hr.overtime': (lambda self, cr, uid, ids, c={}: ids, ['rate', 'number_of_hours_temp'], 10),
            }, readonly=True),
    }

    def onchange_overtime_type_id(self, cr, uid, ids, overtime_type_id):
        result = {}
        if not overtime_type_id:
            return {'value':{}}
        result['value'] = {
            'rate': self.pool.get('hr.overtime.type').browse(cr, uid, overtime_type_id).rate,
        }
        return result
    
    def overtime_validate2(self, cr, uid, ids, context=None):
        super(hr_overtime, self).overtime_validate2(cr, uid, ids, context)
        
        payslip_pool = self.pool.get('hr.payslip')
        for line in self.browse(cr, uid, ids):
            cr.execute('''
            SELECT id, number, state
            FROM hr_payslip
            WHERE employee_id=%s AND date_to >= '%s' AND date_from <='%s' 
            ''' % (line.employee_id.id, line.date_to, line.date_from))
            res = cr.fetchall()
            for payslip in res:
                if payslip[2] == 'done':
                    raise UserError(_('Warning!'), _("Payslip number '%s' has been paid!\n You are not able to approve this Overtime Request!") % (payslip[1]))
            if res:
                payslip_pool.compute_sheet(cr, uid, [x[0] for x in res], context)
        return True

    def overtime_cancel(self, cr, uid, ids, context=None):
        super(hr_overtime, self).overtime_cancel(cr, uid, ids, context)
        
        payslip_pool = self.pool.get('hr.payslip')
        for line in self.browse(cr, uid, ids):
            cr.execute('''
            SELECT hp.id, hp.number, hp.state
            FROM hr_overtime_payslip_rel hop join hr_payslip hp on hop.payslip_id = hp.id
            WHERE hop.overtime_id = %s
            ''' % (line.id))
            res = cr.fetchall()
            for payslip in res:
                if payslip[2] == 'done':
                    raise osv.except_osv(_('Warning!'), _("Payslip number '%s' has been paid!\n You are not able to Validate this Overtime Request!") % (res[0][0]))
                elif payslip[2] != 'cancel':
                    cr.execute('''
                    DELETE FROM hr_overtime_payslip_rel WHERE payslip_id=%s
                    ''' % (line.id))
            # Thanh: Recompute Related Payslip to update Advanced Amount
            if res:
                payslip_pool.compute_sheet(cr, uid, [x[0] for x in res], context)
        return True
    
hr_overtime()
