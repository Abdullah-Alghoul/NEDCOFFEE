# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################


from openerp.osv import fields, osv

def _links_get(self, cr, uid, context={}):
    obj = self.pool.get('res.request.link')
    ids = obj.search(cr, uid, [])
    res = obj.read(cr, uid, ids, ['object', 'name'], context)
    return [(r['object'], r['name']) for r in res]
   
class admin_property(osv.osv):
    _name = 'admin.property'
    _description = 'Tables to handle properties specific to each admin project'
    
    _columns = {
    	'name' : fields.char('Property Name', required=True, size=128),
    	'value': fields.char('Property Value', required=True, size=600 ),
    	'ref_record':fields.reference('Record Ref', selection=_links_get, size=128),
    }
    
    _sql_constraints = [
        ('name_ref_uniq', 'unique (name)', 'The property name must be unique !'),
    ]
    
    def _get_project_property_by_name(self, cr, uid, name):
    	result = None
    	property_ids = self.search(cr, uid, [('name', '=', name)])
        if property_ids:
            property_obj = self.browse(cr, uid, property_ids[0])
            if property_obj.ref_record:
                # update the value if needed
                if property_obj.ref_record.name != property_obj.value:
                    self.write(cr, uid, [property_obj.id], {'value':property_obj.ref_record.name})
                
            result = property_obj
        return result
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('name'):
            del vals['name']
        return super(admin_property, self).write(cr, uid, ids, vals, context)
    
admin_property()