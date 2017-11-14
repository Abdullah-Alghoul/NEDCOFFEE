# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'General Hr Contract',
    'version': '1.1',
    'category': 'General 70',
    'description': """
    1) Add Changed Histories into Contract when User update Wage, Trial Duration, Duration
       """,
    'author': 'Le Truong Thanh <thanh.lt1689@gmail.com>',
    'images': [],
    'depends': ['general_hr', 'hr_contract', 'general_base','report_aeroo'],
    'data': [
        'wizard/wizard_hr_contract_expire_view.xml',
        'security/ir.model.access.csv',
        'report/report_view.xml',
        'hr_contract_view.xml',
#         'hr_contract_data.xml',
        'hr_res_partner_view.xml',
        'general_hr_view.xml'
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    
    # web
    "js": [],
    'qweb' : [],
    'css' : [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
