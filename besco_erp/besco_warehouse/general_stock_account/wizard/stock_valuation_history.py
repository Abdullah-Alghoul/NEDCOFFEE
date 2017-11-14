
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _


class stock_history(osv.osv):
    _inherit = 'stock.history'

    def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
        if context is None:
            context = {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.quantity * line.price_unit_on_quant
        return res

    _columns = {
        'inventory_value': fields.function(_get_inventory_value, string="Inventory Value", type='float', readonly=True),
    }

