{
    'name': 'NEDCOFFEE HR Employee',
    'version': '9.0',
    'category': 'NEDCOFFEE',
    'description': """
    """,
    "author" : "BESCO Consulting",
    'depends': ['base', 'hr', 'general_hr_holidays', 'general_hr','general_l10n_vn_hr_payroll', 'ned_general_hr_security'],
    "update_xml": [
            'report/report_view.xml',
            'ned_general_hr_employee_legal_leaves.xml',
            'ned_hr_employee_view.xml',
            'wizard/wizard_legal_leaves.xml',
            'wizard/export_benefit_information_view.xml',
            'wizard/wizard_export_empl.xml',
            'wizard/wizard_children_holiday.xml',
            'wizard/wizard_birthday_employee.xml',
            'wizard/wizard_taxs.xml',
            'security/ir.model.access.csv',
            'ned_general_hr_import_employee.xml'
    ]
}   
