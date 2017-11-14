# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################


{
    "name" : "BESCO MRP Outsource",
    "version" : "9.0",
    'category': 'General 90',
    "depends" : ["general_base","general_mrp_operations"],
    'update_xml': ['ir_sequence.xml', 
                   'mrp_outsource_view.xml',
                   'stock_view.xml'],
    'installable': True,
    'auto_install': False,
    'certificate': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
