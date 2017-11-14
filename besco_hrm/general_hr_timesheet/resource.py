from openerp.osv import fields, orm

class resource_calendar_attendance(orm.Model):
    _inherit = "resource.calendar.attendance"
    _columns = {
        'rate':fields.integer('Rate %',required=True,default=100)
        }
    
class resource_calendar_overtime_range(orm.Model):
    _inherit = 'resource.calendar.overtime.type'
    _columns = {
        'overtime_type_id': fields.many2one('hr.overtime.type','Overtime Type', required=True),
        }