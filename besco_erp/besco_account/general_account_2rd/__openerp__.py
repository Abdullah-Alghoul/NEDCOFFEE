# -*- coding: utf-8 -*-
{
    "name" : "BESCO - Show 2rd currency",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "description": """
    - Add 2rd Dr, Cr fields into Journal Items Views
    - Add 2rd Dr, Cr fields in to any Accounting Report (Partner Aged Reports, Financial Reports) Views
    
    **Credits:** BESCO Consulting.
    """,
    "depends" : ["general_account",
                 "general_aged_partner_balance",
                 "general_report_account"],
    "data" : [
            "account_report_view.xml",
            "partner_balance_report_view.xml",
            "account_view.xml",
            ],
    "demo" : [],
    "installable": True,
    "overwrite": True,
}