{
    'name': 'HR Employee Input',
    'version': '1.1',
    'category': 'General 70',
    'description': """
       """,
    'author': 'BESCO Group',
    'images': [],
    'depends': ["base", "general_base", 'hr','general_hr','general_hr_contract','general_l10n_vn_hr_payroll'],
    'data': [
            'rule_input.xml',
#              'hr_contract_view.xml'
            'data/hr_employee_input_data.xml',
            'security/ir.model.access.csv',
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