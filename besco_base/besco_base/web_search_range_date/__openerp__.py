# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
############################################################################

{
    'name': 'Web Search Range Date',
    'author' : 'thanh.lt@besco.vn',
    'category' : 'Web',
    'website': 'http://www.besco.vn',
    'description': """
OpenErp Web Search range date time
============================
This is module add two form search all record from date and to date in form view data.
After install this, click any form data and testing it.

Pass these option into action context to trigger search range date:
    - 'search_by_field_date': ['date_invoice','date_due']
    - 'default_filter_array': 'day'
    
    """,
    'version': '1.0',
    'depends': ['web'],
    'data': ['view/main.xml'],
    'qweb' : [
        'static/src/xml/web_search_range_date.xml',
    ],
#     'css':['static/src/web_search_range_date.css',],
#     'js': ['static/src/web_search_range_date.js',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
