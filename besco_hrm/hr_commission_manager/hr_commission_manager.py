# -*- coding: utf-8 -*-
from openerp import models, fields, api

from openerp.osv import osv
from openerp.tools.translate import _

import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta

class hr_commission_manager(models.Model):
    _name = 'hr.commission.manager'
    _description = 'BESCO HR Commission Manager'
    
    name = fields.Char('Name', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approve'),
        ('done', 'Done')
        ], string='Status', readonly=True, select=True, copy=False, default='draft')
    import_date = fields.Date('Import Date', readonly=True)
    start_date = fields.Date('Date From', default=lambda *a: time.strftime('%Y-%m-01'), required=True)
    end_date = fields.Date('Date To', default=lambda *a: str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10], required=True)
    job_id = fields.Many2one('hr.job', 'Job', required=True)
    user_import_id = fields.Many2one('res.users', 'User Import', readonly=True)
    user_approve_id = fields.Many2one('hr.employee', 'User Approve')
    commission_manager_lines_ids = fields.One2many('hr.commission.manager.lines', 'commission_manager_id', string='HR Commission Manager Lines')
    
    def unlink(self, cr, uid, ids, context=None):
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.state not in ['draft', 'refuse']:
                raise osv.except_osv(_('Warning!'), _('You cannot delete this timesheet which is not in draft state !'))
        return super(hr_commission_manager, self).unlink(cr, uid, ids, context)
    
    @api.one 
    def button_approve(self):
        self.write({'state': 'done'})
        return {}
    
    @api.one
    def button_set_to_draft(self):
        self.write({'state': 'draft'})
        return {}

    @api.one
    def button_confirm(self):
        self.write({'state': 'approve'})
        return {}
        
    
class hr_commission_manager_lines(models.Model):
    _name = 'hr.commission.manager.lines'
    _description = 'HR Commission Manager Lines'
    
    name = fields.Many2one('hr.employee', 'Employee', required=True)
    product_id = fields.Many2one('product.product', 'Product', required=True)
    uom = fields.Many2one('product.uom', 'UoM', required=True)
    quantity = fields.Integer('Real Quantity')
    commission_manager_id = fields.Many2one('hr.commission.manager', 'Commission Manager')
    
    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM for changed product.
        @param product_id: Changed id of product.
        @return: Dictionary of values.
        """
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            d = {'uom': [('category_id', '=', prod.uom_id.category_id.id)]}
            v = {'uom': prod.uom_id.id}
            return {'value': v, 'domain': d}
        return {'domain': {'uom': []}}
