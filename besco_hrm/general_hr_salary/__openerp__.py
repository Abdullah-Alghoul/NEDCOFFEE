# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'General HRM Salary',
    'version': '9.0',
    'category': 'General 90',
    "author" : "BESCO Consulting",
    'depends': ['general_hr_contract','hr_payroll'],
    'data': [
             'insurance_pit_structures_view.xml',
             'hr_contract_view.xml',
             'security/ir.model.access.csv'
             ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
