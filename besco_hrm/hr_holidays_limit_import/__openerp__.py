{
    'name': 'HR Holidays Limit Import',
    'version': '9.0',
    'category': 'RINGIER',
    'description': """
    """,
    "author" : "BESCO Consulting",
    'depends': ['general_hr_holidays', 'hr_holidays' , 'calendar'],
    'data': [
        "hr_holidays_limit_import_view.xml",
        'security/ir.model.access.csv',
    ]
}