##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################

{
    'name': 'Margins in Sales Orders',
    'version':'1.0',
    'category' : 'BESCO 90',
    'description': """
This module adds the 'Margin' on sales order.

This gives the profitability by calculating the difference between the Unit
Price and Cost Price.
    """,
    'author':'BESCO',
    'images':[],
    'depends':['general_sale'],
    'demo':[],
    'test': [],
    'data':[
#             'security/ir.model.access.csv',
#             'security/sale_security.xml',

            'wizard/change_order_mark_up_view.xml',
            'wizard/change_sales_price_view.xml',
#             'wizard/weekly_sales_report_view.xml',
#             'wizard/salesteam_sales_target_report_view.xml',
#             'report/report.xml',

            'sale_margin_view.xml',
#             'res_users_view.xml',
#             'sales_report_view.xml',

#             'menu.xml',
            ],
    'auto_install': False,
    'installable': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

