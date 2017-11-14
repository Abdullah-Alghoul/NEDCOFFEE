# -*- encoding: utf-8 -*-
{
    "name" : "General Assets Management",
    "version" : "9.0",
    'author': 'BESCO Consulting',
    'category': 'BESCO Consulting',
    'website': 'http://besco.vn',
    "depends" : ["general_account", "account_asset","general_base"],
    "description": """Financial and accounting asset management.
    This Module manages the assets owned by a company or an individual. It will keep track of depreciation's occurred on
    those assets. And it allows to create Move's of the depreciation lines.
    """,
    "update_xml" : [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        
        "wizard/account_asset_change_duration_view.xml",
        "wizard/account_asset_sell_dispose_view.xml",
        "wizard/print_report.xml",

        "report/report_view.xml",
        
        "menu.xml",
        "account_asset_view.xml",
        "hr_asset_view.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

