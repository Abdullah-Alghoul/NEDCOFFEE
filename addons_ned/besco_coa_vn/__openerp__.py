# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# This module is Copyright (c) 2009-2013 General Solutions (http://gscom.vn) All Rights Reserved.

{
    "name" : "BESCO - Default VAS Configuration Data",
    "version" : "1.0",
    "author" : "BESCO",
    'website': 'http://besco.vn',
    "category" : "Localization/Account Charts",
    "description": """
This is the module to manage the accounting chart for Vietnam in OpenERP. Extend original module l10n_vn\n
- Add some Export and Import tax data
- Translate some accounting terms: Account Types, ... (If after installed not worked, you can get filter vi_VN.po in folder i18n to import manually)

**Credits:** BESCO Consulting.
""",
    "depends" : ["base_vat"],
    "data" : [
            "account_tax.xml",
            ],
    "demo" : [],
    "installable": True,
    "overwrite": True,
}