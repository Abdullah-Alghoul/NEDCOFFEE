 # -*- coding: utf-8 -*-
from openerp.exceptions import UserError, AccessError
from openerp import api, fields, models


class wizard_benefit_information(models.TransientModel):
    _name = 'wizard.benefit.information'
    
    start_date = fields.Date(string="start date" , required=True, default=fields.Datetime.now)
    end_date = fields.Date(string="end date", required=True)
    type = fields.Selection([('one', u'DANH SÁCH LAO ĐỘNG THAM GIA BHXH, BHYT, BHTN'), 
                             ('two', u'DANH SÁCH ĐỀ NGHỊ HƯỞNG CHẾ ĐỘ MỚI PHÁT SINH')], 'Report Type', required=True)
    code_type = fields.Many2one('insurance.code', string='Insurance Code')
    
    def _get_default_code_type(self, cr, uid, context=None):
        code_type_id = self.pool.get('insurance.code').search(cr, uid, [], limit=1)
        return code_type_id and code_type_id[0] 
    
    _defaults = {
        'type': 'one',
        'code_type':_get_default_code_type,
    }
    
    
#     @api.multi
#     def report_wizard_legal_leaves(self):
#         return {'type': 'ir.actions.report.xml', 'report_name': 'report_holiday_leaves'}
    def report_wizard_benefit_information(self, cr, uid, ids, context=None):
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'wizard.benefit.information'
        datas['form'] = self.read(cr, uid, ids)[0]
        if datas['form']['type'] == 'one':
            if not datas['form']['code_type']:
                raise UserError('Choose Insurance Code to export file')
            return {'type': 'ir.actions.report.xml', 'report_name': 'export_insurance_information_report' , 'datas': datas}
        else:
            if not datas['form']['code_type']:
                raise UserError('Choose Insurance Code to export file') 
            return {'type': 'ir.actions.report.xml', 'report_name': 'export_benefit_information_report' , 'datas': datas}
