# -*- coding: utf-8 -*-
{
    'name': 'Account Reversal',
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    'depends': ['account', 'general_account'],
    'data': [
        'wizard/account_move_reverse_view.xml',
        'account_view.xml',
        'cron.xml'
        ],
    'installable': True,
    'active': True,
}
