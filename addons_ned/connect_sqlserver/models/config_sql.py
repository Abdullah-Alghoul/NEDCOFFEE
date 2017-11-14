# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
# import pypyodbc
import pyodbc
from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp.exceptions import UserError
from openerp.exceptions import except_orm, Warning, RedirectWarning

_logger = logging.getLogger(__name__)

class Config_sql(models.Model):
    _name = 'connect.sqlserver'
    _description = 'Connect Sql Server'
    
    #Create Name
    name = fields.Char('Name Server')
    type = fields.Char('Host Name')
    db_name = fields.Char('Database Name')
    db_user = fields.Char('Database User')
    db_password = fields.Char('Dababase Password')
    server_name = fields.Char('Server Name')
    dsn_server = fields.Char('DNS Server')
    
    #VINH Code test connect Sql server 
    @api.multi
    def test_connect_sqlserver(self):
        conn = False
        dsn = str((self.dsn_server).encode('utf-8'))
        user  = str((self.db_user).encode('utf-8'))
        password = str((self.db_password).encode('utf-8'))
        database = str((self.db_name).encode('utf-8'))
        type = str((self.type).encode('utf-8'))
        server_name = str((self.server_name).encode('utf-8'))
        try:
            con_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
            conn = pyodbc.connect(con_string)
        except Exception, e:
           raise except_orm(
                _("Connection Test Failed!"),
                _("Here is the error message: %s" % e))
        finally:
            print "ok"
        raise except_orm(
            _("Connection Test Successfull!"),
            _("Odoo can successfully Connect SQL Server "
                "Interface."))
    @api.multi
    def connect(self):
        conn = False
        dsn = str((self.dsn_server).encode('utf-8'))
        user  = str((self.db_user).encode('utf-8'))
        password = str((self.db_password).encode('utf-8'))
        database = str((self.db_name).encode('utf-8'))
        type = str((self.type).encode('utf-8'))
        server_name = str((self.server_name).encode('utf-8'))
        con_string = 'DSN=%s;UID=%s;PWD=%s;DATABASE=%s;' % (dsn, user, password, database)
        if pyodbc.connect(con_string):
            return pyodbc.connect(con_string)
        else:
            return False
        
    