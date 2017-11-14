# coding: utf-8

from openerp.osv import osv, fields


class ResPartner(osv.Model):
    _inherit = "res.partner"

    _columns = {
        'create_date': fields.datetime('Create Date', readonly=True),
    }
