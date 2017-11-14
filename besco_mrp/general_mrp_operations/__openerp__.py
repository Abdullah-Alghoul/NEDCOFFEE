# -*- coding: utf-8 -*-
{
    'name': 'BESCO Manufacturing Operations',
    "version" : "9.0",
    "author" : "Le Truong Thanh <thanh.lt1689@gmail.com>",
    'category': 'General 90',
    'depends': ['general_mrp'],
    'data': [
            'security/ir.model.access.csv',
            'views/mrp_operation.xml',
            'report/report_view.xml',
            'wizard/wizard_date_report_view.xml',
            'wizard/wizard_production_plan_report_view.xml',
            'wizard/wizard_updates_number_view.xml',
            'wizard/wizard_consume_product_view.xml',
            'wizard/wizard_request_materials.xml',
            'mrp_report.xml',
            'production_picking_view.xml',
            'mrp_operations_view.xml',
            'request_view.xml',
            ],
    'qweb' : [
        "static/src/xml/mrp_operation_quick_search.xml",
        ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
