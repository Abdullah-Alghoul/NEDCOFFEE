# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Purchase landed costs - Accounting',
    'version': '1.0',
    "author": "BESCO CO",
    'category': 'General 90',
    'website': 'http://www.besco.vn',
    'summary': 'Purchase cost distribution',
    'depends': [
        'stock',
#         'purchase',
        'general_stock_account',
    ],
    'data': [
        'wizard/picking_import_wizard_view.xml',
        'wizard/import_invoice_line_wizard_view.xml',
        'views/purchase_cost_distribution_view.xml',
        'views/purchase_expense_type_view.xml',
        'views/account_invoice.xml',
        
        #'views/purchase_order_view.xml',
        'views/stock_picking_view.xml',
        
        'security/purchase_landed_cost_security.xml',
        'security/ir.model.access.csv',
        'data/purchase_cost_distribution_sequence.xml',
    ],
    'installable': True,
    'images': [
        '/static/description/images/purchase_order_expense_main.png',
        '/static/description/images/purchase_order_expense_line.png',
        '/static/description/images/expenses_types.png',
    ],
}
