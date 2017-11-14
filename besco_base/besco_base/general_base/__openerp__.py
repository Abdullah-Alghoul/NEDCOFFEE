# -*- coding: utf-8 -*-

{
    "name" : "BESCO BASE",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "description": """
    1) Modify the way generate sequence number
    2) Add new object system sequence to auto get sequence number for special objects like Product, Material, Employee ...
    3) Create Employee one time when create an User
    4) Add some personal informations for Partner (Iden number, ...)
    
    """,
    "depends" : ["base", "base_vat", "properties", 
                 "general_user_profile",
                 "hr","board"],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'board_view.xml',
        
        'menu.xml',
        
        'ir_sequence_view.xml',
        'res_partner_view.xml',
        'system_sequence_view.xml',
        'res_users_view.xml',
        'ir_ui_menu_view.xml',
        'res_currency.xml',
        
        'wizard/res_users_view.xml',
    ],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
