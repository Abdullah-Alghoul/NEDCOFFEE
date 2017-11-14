# -*- coding: utf-8 -*-
{"name": "Multicurrency revaluation",
 "version" : "9.0",
'author': 'BESCO Consulting',
'category': 'BESCO Consulting',
'website': 'http://besco.vn',
 "summary": "Manage revaluation for multicurrency environment",
 "depends": [
     "base",
     "account",
     "general_account",
 ],
 "data": [
     "security/ir.model.access.csv",
     
     "views/res_company_view.xml",
     "views/account_view.xml",
     "views/account_currency_revaluation_view.xml"
 ],
 'installable': True,
 }
