# -*- coding: utf-8 -*-

{
    'name': 'NEDCOFFEE HR Attendance',
    'version': '9.0',
    'category': 'NEDCOFFEE',
    'description': """
    """,
    "author" : "BESCO Consulting",
    'depends': ['general_hr_attendance','general_hr_holidays', 'general_base'],
    "update_xml": [
            'report/report_view.xml',
            'wizard/wizard_employee_leaves.xml'
    ],
    "installable": True,
    "auto_instal": False,
    "certificate": False,
}