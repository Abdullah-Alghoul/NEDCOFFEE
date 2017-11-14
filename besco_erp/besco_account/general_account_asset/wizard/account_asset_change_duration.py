# -*- coding: utf-8 -*-
from openerp import api, fields, models
from openerp.osv.orm import setup_modifiers
from openerp.tools.translate import _

import time
from openerp.exceptions import UserError, ValidationError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
DATETIME_FORMAT = "%Y-%m-%d"
DATE_FORMAT = "%Y-%m-%d"

class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'
    
    #THANH: add new fields
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    value = fields.Float(string='Gross Value', digits=0, readonly=True)
    
    @api.model
    def default_get(self, fields):
        res = super(AssetModify, self).default_get(fields)
        asset_id = self.env.context.get('active_id')
        asset = self.env['account.asset.asset'].browse(asset_id)
        res.update({'account_analytic_id': asset.account_analytic_id.id,
                    'value': asset.value})
        return res
    
    @api.multi
    def modify(self):
        """ Modifies the duration of asset for calculating depreciation
        and maintains the history of old values, in the chatter.
        """
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        
        old_values = {
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
        }
        asset_vals = {
            'method_number': self.method_number,
            'method_period': self.method_period,
            'method_end': self.method_end,
        }
        #THANH: add context to bypass check change method_number
        asset.with_context(pass_method_number=True).write(asset_vals)
        asset.with_context(pass_method_number=True).compute_depreciation_board()
        tracked_fields = self.env['account.asset.asset'].fields_get(['method_number', 'method_period', 'method_end'])
        changes, tracking_value_ids = asset._message_track(tracked_fields, old_values)
        if changes:
            asset.message_post(subject=_('Depreciation board modified'), body=self.name, tracking_value_ids=tracking_value_ids)
        
        #THANH: Log changed values
        history_vals = {
            'asset_id': asset_id,
            'name': self.name,
            'value': asset.value,
            'method_time': asset.method_time,
            'method_number': asset.method_number,
            'method_period': asset.method_period,
            'method_end': asset.method_end,
            'user_id': self.env.user.id,
            'date': time.strftime('%Y-%m-%d'),
#             'note': self.note,
        }
        self.env['account.asset.history'].create(history_vals)
        return {'type': 'ir.actions.act_window_close'}
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
