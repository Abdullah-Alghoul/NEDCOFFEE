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
    "name": "General HR Location",
    "version": "1.0",
    "author": "BESCO <info@besco.vn>",
    "category": "BESCO",
    "website": "www.besco.vn",
    "description": """General HR Location""",
    'depends': ['hr', 'base', 'general_hr'],
    'data': [
             'general_hr_location_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

