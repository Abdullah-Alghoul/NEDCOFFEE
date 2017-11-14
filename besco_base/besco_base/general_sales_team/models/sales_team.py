# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import tools, api

class crm_team(osv.Model):
    _inherit = 'crm.team'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'
    
    def _complete_name(self, cr, uid, ids, name, args, context=None):
        """ Forms complete name of location from parent location to child location.
        @return: Dictionary of values
        """
        res = {}
        for m in self.browse(cr, uid, ids, context=context):
            res[m.id] = m.name
            parent = m.parent_id
            while parent:
                res[m.id] = parent.name + ' / ' + res[m.id]
                parent = parent.parent_id
        return res

    def _get_sublocations(self, cr, uid, ids, context=None):
        """ return all sublocations of the given stock locations (included) """
        if context is None:
            context = {}
        return self.search(cr, uid, [('id', 'child_of', ids)])

    def _name_get(self, cr, uid, team, context=None):
        name = team.name
        while team.parent_id:
            team = team.parent_id
            name = team.name + '/' + name
        return name

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for team in self.browse(cr, uid, ids, context=context):
            res.append((team.id, team.name))
        return res
    
    _columns = {
        'parent_id': fields.many2one('crm.team', 'Parent'),
        'complete_name': fields.function(_complete_name, type='char', string="Full Name",
                            store={'crm.team': (_get_sublocations, ['name', 'parent_id'], 10)}),
        'parent_left': fields.integer('Left Parent', select=1),
        'parent_right': fields.integer('Right Parent', select=1),
        'partner_ids':fields.one2many('res.partner','crm_sale_team','Sale Team')
    }
class res_partner(osv.Model):
    _inherit = 'res.partner'
    _columns = {
        'crm_sale_team': fields.many2one('crm.team', 'Sales Team'),
    }

class res_users(osv.Model):
    _inherit = 'res.users'
    
    def _load_child_partner_ids(self, cr, uid, ids, name, args, context=None):
        result = {}
        team_ids = self.pool.get('crm.team').search(cr, uid, [('user_id','in',ids)], context=context)
        if len(team_ids):
            partner_ids = self.pool.get('res.partner').search(cr, uid, [('crm_sale_team','in',team_ids)], context=context)
            for user in self.browse(cr, uid, ids, context=context):
                result[user.id] = partner_ids
        return  result
    def _get_partner(self, cr, uid, ids, args, context=None):
        result = {}
        team_ids = self.pool.get('crm.team').search(cr, uid, [('user_id','in',ids)], context=context)
        if len(team_ids):
            partner_ids = self.pool.get('res.partner').search(cr, uid, [('crm_sale_team','in',team_ids)], context=context)
            for user in self.browse(cr, uid, ids, context=context):
                result = partner_ids
        return  result
    def _load_child_user_reference(self, cr, uid, ids, name, args, context=None):
        result = {}
        print ids
        for id in ids:
            team_ids = self.pool.get('crm.team').search(cr, uid, [('user_id','=',id)], context=context)
            if len(team_ids):
                user_ids = self.pool.get('res.users').search(cr, uid, [('sale_team_id','in',team_ids)], context=context)
                
                for user in self.browse(cr, uid, id, context=context):
                    result[user.id] = []
                    sql = '''
                        SELECT R.ID
                        FROM RES_PARTNER R
                        WHERE CRM_SALE_TEAM IN(
                        SELECT ID
                        FROM CRM_TEAM C
                        WHERE USER_ID IN (
                        SELECT ID
                        FROM RES_USERS U
                        WHERE sale_team_id = '%s') 
                        )
                    '''%(team_ids[0])
                    cr.execute(sql)
                    partner = self._get_partner(cr,uid,user_ids,args,context=context)
                    result[user.id] = partner
        #hack code id =1 
        result[1]=[0]            
        return  result
    
    def _get_leader_team_name(self, cr, uid, ids, name, args, context=None):
        res = {}
        for u in self.browse(cr, uid, ids, context=context):
            res[u.id] = ''
            for team in u.leader_team_ids:
                res[u.id] += team.name + ','
            if len(res[u.id]):
                res[u.id] = res[u.id][:-1]
        return res
    
    _columns = {
        'leader_team_name': fields.function(_get_leader_team_name, type='char', string="Leader of Teams"),
        'leader_team_ids': fields.one2many('crm.team', 'user_id', 'Leader of Teams'),
        
        'child_partner_ids': fields.function(_load_child_partner_ids, type="many2many", relation='res.partner', 
                                             string='Child Partners'),
        
        'child_user_ids': fields.function(_load_child_user_reference, type="many2many", relation='res.partner',
                                             string='Child Users')
    }
