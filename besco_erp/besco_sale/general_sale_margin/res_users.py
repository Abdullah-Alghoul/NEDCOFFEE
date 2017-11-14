##############################################################################
#
#    OpenERP, Open Source Management Solution
#
##############################################################################

from osv import fields, osv

class crm_case_section(osv.osv):
    _inherit = "crm.case.section"
    _columns = {
        'minimum_margin': fields.float('Min Margin (%)', digits=(16,2)),
    }
    
    _defaults = {
        'minimum_margin': 0.0,
    }
    
    def _check_margin(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        check_ids = []
        for data in self.browse(cr, uid, ids, context=context):
            if data.minimum_margin < 0 or data.minimum_margin > 100:
                return False
        return True
    
    _constraints = [
        (_check_margin, 'Minimum Margin (%) must be in Range (0-100)', []),

    ]
    
    
crm_case_section()

class res_users(osv.osv):
    _inherit = "res.users"
    _columns = {
        'minimum_margin': fields.float('Minimum Margin (%)', digits=(16,2)),
    }
    
    _defaults = {
        'minimum_margin': 0.0,
    }
    
    def _check_margin(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        check_ids = []
        for data in self.browse(cr, uid, ids, context=context):
            if data.minimum_margin < 0 or data.minimum_margin > 100:
                return False
        return True
    
    _constraints = [
        (_check_margin, 'Minimum Margin (%) must be in Range (0-100)', []),

    ]
res_users()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
