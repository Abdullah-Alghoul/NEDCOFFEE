from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
        

class create_stock_stack(osv.osv):
    _name = 'create.stock.stack'
    _columns = {
        'zone_id': fields.many2one('stock.zone', string='Zone',),
        'name' : fields.char('Stack name'),
        'date':fields.date('Date'),
        'province_id':fields.many2one('res.country.state', 'Province',),
        'districts_id':fields.many2one('res.district', 'Source', ondelete='restrict'),
        'hopper':fields.boolean(string="hopper")
    }
    
    _defaults = {
        'date': time.strftime('%Y-%m-%d')
    }
    
    def create_stack(self, cr, uid, ids, context):
        for this in self.browse(cr, uid, ids):
            var = {
                    'zone_id':this.zone_id.id,
                    'hopper':this.hopper or False,
                    'date':this.date,
                    'name':this.name,
                    'districts_id':this.districts_id.id or False,
                  }
            stack_id = self.pool.get('stock.stack').create(cr, uid, var)
            self.pool.get('stock.move').write(cr, uid, context['active_ids'], {'stack_id':stack_id, 'zone_id':this.zone_id.id})
        return 1
