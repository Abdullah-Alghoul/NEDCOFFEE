# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 ISA s.r.l. (<http://www.isa.it>).
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
    "name": "General HR Timesheet",
    "version": "1.0",
    "author": "BESCO",
    "category": "HRM",
    "website": "www.besco.vn",
    "description": """General HR Timesheet""",
    'depends': ['hr_overtime', 'general_hr_overtime_attendance', 'general_hr_holidays', 'general_hr','hr_attendance_analysis'],
    'data': [
            'report/report_view.xml',
            'wizard/wizard_hr_overtime_view.xml',
            'wizard/wizard_hr_overtime_batches_view.xml',
            'general_hr_timesheet_view.xml',
            'hr_timesheets_team_view.xml',
            'security/ir.model.access.csv',
            'security/security.xml',
            'hr_overtime_view.xml',
            'resource_view.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

