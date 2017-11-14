# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.osv import expression
from datetime import datetime, timedelta

from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import float_compare, float_round
from openerp.tools.misc import formatLang
from openerp.exceptions import UserError, ValidationError

class BrokenStandard(models.Model):
    _name = "broken.standard"
    _oder = "range_end desc,id desc"
    
    name = fields.Char(string="Range", default="New")
    range_start = fields.Float(string="From (%)", default=5, digits=(12, 2))
    range_end = fields.Float(string="To (%)", default=7, digits=(12, 2))
    
    percent = fields.Float(string="Percent (%)", default=0.5, digits=(12, 2))
    criterion_id = fields.Many2one("kcs.criterions",string="KCS Criterion", ondelete='cascade', index=True, copy=False)
    subtract = fields.Boolean(string="Subtract", default=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New'):
            if vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range ' + str(vals.get('range_start', False)) + ' - ' + str(vals.get('range_end', False))
            elif not vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range 0' + '-' + str(vals.get('range_end', False))
            vals['name'] = name
        result = super(BrokenStandard, self).create(vals)
        return result
    
    @api.constrains('percent')
    def _check_percent(self):
        if self.percent < 0:
            raise UserError(_("Broken Standard: Percent do  not smaller 0."))
        elif self.percent > 100:
            raise UserError(_("Broken Standard: Percent do  not bigger 100."))
    
    @api.constrains('range_start')
    def _check_range_from(self):
        if self.range_start < 0:
            raise UserError(_("Broken Standard: Range start do not smaller 0."))
        if self.range_start > self.range_end:
            raise UserError(_("Broken Standard: Range start do not bigger the range ended."))
        
    @api.constrains('range_end')
    def _check_range_end(self):
        if self.range_end < self.range_start:
            raise UserError(_("Broken Standard: Range end do not bigger the range started."))
        if self.range_start > 100:
            raise UserError(_("Broken Standard: Range end do  not bigger 100."))
        
class BrownStandard(models.Model):
    _name = "brown.standard"
    _oder = "range_end desc,id desc"
    
    name = fields.Char(string="Range", default="New")
    range_start = fields.Float(string="From (%)", default=5, digits=(12, 2))
    range_end = fields.Float(string="To (%)", default=7, digits=(12, 2))
    
    percent = fields.Float(string="Percent (%)", default=50, digits=(12, 2))
    values = fields.Float(string="Values Other", default=1, digits=(12, 2))
    criterion_id = fields.Many2one("kcs.criterions",string="KCS Criterion", ondelete='cascade', index=True, copy=False)
    subtract = fields.Boolean(string="Subtract", default=True, copy=False)
    check_values = fields.Boolean(string="Enter Values Other", default=True, copy=False)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New'):
            if vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range ' + str(vals.get('range_start', False)) + ' - ' + str(vals.get('range_end', False))
            elif not vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range 0' + ' - ' + str(vals.get('range_end', False))
            vals['name'] = name
        result = super(BrownStandard, self).create(vals)
        return result
    
    @api.constrains('percent')
    def _check_percent(self):
        if self.percent < 0:
            raise UserError(_("Brown Standard: Percent do  not smaller 0."))
        elif self.percent > 100:
            raise UserError(_("Brown Standard: Percent do  not bigger 100."))
    
    @api.constrains('range_start')
    def _check_range_from(self):
        if self.range_start < 0:
            raise UserError(_("Brown Standard: Range start do not smaller 0."))
        if self.range_start > self.range_end:
            raise UserError(_("Brown Standard: Range start do not bigger the range ended."))
        
    @api.constrains('range_end')
    def _check_range_end(self):
        if self.range_end < self.range_start:
            raise UserError(_("Brown Standard: Range end do not bigger the range started."))
        if self.range_start > 100:
            raise UserError(_("Brown Standard: Range end do  not bigger 100."))
        
class MoldStandard(models.Model):
    _name = "mold.standard"
    _oder = "range_end desc,id desc"
    
    name = fields.Char(string="Range", default="New")
    range_start = fields.Float(string="From (%)", default=3, digits=(12, 2))
    range_end = fields.Float(string="To (%)", default=6, digits=(12, 2))
    
    subtract = fields.Boolean(string="Subtract", default=True, copy=False)
    percent = fields.Float(string="Percent (%)", default=5, digits=(12, 2))
    criterion_id = fields.Many2one("kcs.criterions",string="KCS Criterion", ondelete='cascade', index=True, copy=False)
    compares = fields.Selection([('<','Smaller values'),('<=','Smaller or equal values')], string="Type Compares", default="<", required=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New'):
            if vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range ' + str(vals.get('range_start', False)) + ' - ' + str(vals.get('range_end', False))
            elif not vals.get('range_start', False) and vals.get('range_end', False):
                name = 'Range 0' + ' - ' + str(vals.get('range_end', False))
            vals['name'] = name
        result = super(MoldStandard, self).create(vals)
        return result
    
    @api.constrains('percent')
    def _check_percent(self):
        if self.percent < 0:
            raise UserError(_("Mold Standard: Percent do  not smaller 0."))
        elif self.percent > 100:
            raise UserError(_("Mold Standard: Percent do  not bigger 100."))
    
    @api.constrains('range_start')
    def _check_range_from(self):
        if self.range_start < 0:
            raise UserError(_("Mold Standard: Range start do not smaller 0."))
        if self.range_start > self.range_end:
            raise UserError(_("Mold Standard: Range start do not bigger the range ended."))
        
    @api.constrains('range_end')
    def _check_range_end(self):
        if self.range_end < self.range_start:
            raise UserError(_("Mold Standard: Range end do not bigger the range started."))
        if self.range_start > 100:
            raise UserError(_("Mold Standard: Range end do  not bigger 100."))

    


class DegreeMc(models.Model):
    _name = 'degree.mc'
    _order = 'id desc'
    
    
    mconkett = fields.Float(digits=(12, 2),string="MConKett")
    deduction = fields.Float(digits=(12, 2),string="Deduction")
    
    
        