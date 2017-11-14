# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "General KCS",
    "version" : "9.0",
    "author" : "Duong Thien Kim <duong.tkim@gmail.com>",
    'category': 'BESCO 90',
    "depends" : ["general_product", "general_stock","base"],
    "update_xml": [
           "module/module_data.xml",
           "security/kcs_security.xml",     
           "security/ir.model.access.csv",
           "ir_sequence.xml", 
           "kcs_view.xml"
           ],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
