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
    'name': 'General Attendances',
    'version': '1.1',
    'category': 'General 70',
    'description': """
       """,
    'author': 'Le Truong Thanh <thanh.lt1689@gmail.com>',
    'images': [],
    'depends': ['hr', 'hr_attendance', 'general_hr', 'general_user_profile', 'base', 'general_hr_contract', 'web_calendar', 'web', 'calendar'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        
        'hr_attendance_view.xml',
        'hr_attendance_import_view.xml',
        'assets/template.xml',
    ],
    'demo': [],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    
    #web
    "js": [],
    'qweb' : [],
    'css' : [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
