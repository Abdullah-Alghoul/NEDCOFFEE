# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
# import pypyodbc
# import pyodbc
from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp.exceptions import UserError
from openerp.exceptions import except_orm, Warning, RedirectWarning

_logger = logging.getLogger(__name__)

class res_users(models.Model):
    _inherit = 'res.users'
    
    sql_server_id = fields.Many2one('connect.sqlserver',string='Sql Server ID')