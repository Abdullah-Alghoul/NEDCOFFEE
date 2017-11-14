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
    'name': 'General Leave Request',
    'version': '1.1',
    'author': 'Le Truong Thanh <thanh.lt1689@gmail.com>',
    'category': 'General 70',
    'sequence': 21,
    'website': '',
    'summary': 'Jobs, Departments, Employees Details',
    'description': """
    """,
    'depends': ['hr_holidays','hr_contract', 'general_hr', 'general_user_profile', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/input_data.xml',
        'wizard/generate_allocation_request_view.xml',
        'hr_holiday_day_view.xml',
        'hr_holidays_view.xml',
        'hr_holidays_workflow.xml',
        'employee_view.xml',
        'hr_payment_leaves_view.xml',
        'data/email_template.xml',
        'report/report_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
