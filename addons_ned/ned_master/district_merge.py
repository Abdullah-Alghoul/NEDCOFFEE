# coding: utf-8
import functools
import itertools
import operator
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.osv.orm import browse_record

def is_integer_list(ids):
    return all(isinstance(i, (int, long)) for i in ids)


class WizardDistrictMergeAutomatic(models.TransientModel):
    _name = 'wizard.district.merge.automatic'
    
    state = fields.Selection([('option', 'Option'),
                               ('selection', 'Selection'),
                               ('finished', 'Finished')],
                              'State', readonly=True, required=True, default='option')
    district_from = fields.Many2one('res.district', string='Account from')
    district_to = fields.Many2one('res.district', string='Account to')
    maximum_group = fields.Integer("Maximum of Group of Contacts")

    def get_fk_on(self, cr, table, tables=None):
        tables = tables and tuple(tables) or []
        where = tables and 'AND cli.relname in %s' % (str(tables))
        q = """  SELECT cl1.relname as table,
                        att1.attname as column
                   FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
                        pg_attribute as att1, pg_attribute as att2
                  WHERE con.conrelid = cl1.oid
                    AND con.confrelid = cl2.oid
                    AND array_lower(con.conkey, 1) = 1
                    AND con.conkey[1] = att1.attnum
                    AND att1.attrelid = cl1.oid
                    AND cl2.relname = %s
                    AND att2.attname = 'id'
                    AND array_lower(con.confkey, 1) = 1
                    AND con.confkey[1] = att2.attnum
                    AND att2.attrelid = cl2.oid
                    AND con.contype = 'f'
                    %s
        """
        return cr.execute(q, (table, tables and where or '',))

    def _update_foreign_keys(self, cr, uid, src_accounts, dst_account,
                             model=None, context=None):
        # find the many2one relation to a account
        account_bad = []
        
        self.get_fk_on(cr, 'res_district')
        for table, column in cr.fetchall():
            if 'wizard_account_merge_automatic' in table:
                continue
            
            account_ids = tuple(map(int, src_accounts))

            query = """SELECT column_name FROM information_schema.columns
                       WHERE table_name LIKE '%s'""" % (
                table)
            cr.execute(query, ())
            columns = []
            for data in cr.fetchall():
                if data[0] != column:
                    columns.append(data[0])

            query_dic = {
                'table': table,
                'column': column,
                'value': columns[0],
            }
            
            #THANH: Value can be id or a field in many2many relation table
            query = """
                UPDATE "%(table)s" as ___tu
                SET %(column)s = %%s
                WHERE
                    %(column)s = %%s AND
                    NOT EXISTS (
                        SELECT 1
                        FROM "%(table)s" as ___tw
                        WHERE
                            %(column)s = %%s AND
                            ___tu.%(value)s = ___tw.%(value)s
                    )""" % query_dic
            for account_id in account_ids:
                cr.execute(query, (
                    dst_account.id, account_id, dst_account.id))
        return account_bad

    def _update_reference_fields(self, cr, uid, src_district, dst_district, context=None):
        account_bad = []

        def update_records(model, src, field_model='model',
                           field_id='res_id', context=None):
            proxy = self.pool.get(model)
            if proxy is None:
                return
            domain = [(field_model, '=', 'res.district'), (
                field_id, '=', src.id)]
            ids = proxy.search(
                cr, SUPERUSER_ID, domain, context=context)
            return proxy.write(cr, SUPERUSER_ID, ids,
                               {field_id: dst_district.id},
                               context=context)

        update_records = functools.partial(update_records,
                                           context=context)

        proxy = self.pool['ir.model.fields']
        domain = [('ttype', '=', 'reference')]
        record_ids = proxy.search(
            cr, SUPERUSER_ID, domain, context=context)

        for record in proxy.browse(cr, SUPERUSER_ID, record_ids,
                                   context=context):
            proxy_model = self.pool[record.model]

            field_type = proxy_model._columns.get(record.name).__class__._type

            if field_type == 'function':
                continue

            for district in src_district:
                domain = [
                    (record.name, '=', 'res.district,%d' % district.id)
                ]
                model_ids = proxy_model.search(
                    cr, SUPERUSER_ID, domain, context=context)
                values = {
                    record.name: 'res.district,%d' % dst_district.id,
                }
                proxy_model.write(
                    cr, SUPERUSER_ID, model_ids, values,
                    context=context)
        return account_bad

    def _update_values(self, cr, uid, src_district, dst_district, context=None):
        account_bad = []
        columns = dst_district._columns

        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item

        values = dict()
        for column, field in columns.iteritems():
            if field._type not in ('many2many', 'one2many'):
                for item in itertools.chain(src_district, [dst_district]):
                    if item[column]:
                        values[column] = write_serializer(column, item[column])
        return account_bad

    def close_cb(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

    def _merge(self, cr, uid, district_ids, dst_district=None, context=None):
        proxy = self.pool.get('res.district')
        district_ids = proxy.exists(
            cr, uid, list(district_ids), context=context)
        if len(district_ids) < 2:
            return True

        if len(district_ids) > 10:
            raise UserError(_('Error!'), _(
                """
                For safety reasons, you cannot merge more than 10 accounts
                together. You can re-open the wizard several
                times if needed.
                """))
        if dst_district and dst_district.id in district_ids:
            src_district = proxy.browse(cr, uid, [
                                        id for id in district_ids
                                        if id != dst_district.id],
                                        context=context)
        else:
            ordered_accounts = self._get_ordered_district(
                cr, uid, district_ids, context)
            dst_district = ordered_accounts[-1]
            dst_district = ordered_accounts[:-1]

        if SUPERUSER_ID != uid and \
                self._model_is_installed(cr, uid, 'account.move.line',
                                         context=context) and \
                self.pool.get('account.move.line').\
        search(cr, SUPERUSER_ID,
                    [('account_id', 'in', [district.id for district in dst_district])],
                    context=context):
            raise UserError(_('Error!'), _(
                """Only the destination account may be linked to existing
                   Journal Items. Please ask the Administrator if you need
                   to merge several accounts linked to existing Journal
                   Items."""))
        call_it = lambda function: function(
            cr, uid, src_district, dst_district, context=context)
        district_bad = []

        district_bad += call_it(self._update_foreign_keys)
        district_bad += call_it(self._update_reference_fields)
        district_bad += call_it(self._update_values)
        district_bad = set(district_bad)
        for district in src_district:
            if district.id not in district_bad:
                #Kiet: DELETE it to inactive
                sql = '''
                    DELETE FROM res_district where id = %s
                '''%(district.id)
                cr.execute(sql)
                proxy.exists(cr, uid, district.id, context=context)
        return True

    def _get_ordered_district(self, cr, uid, account_ids, context=None):
        districts = self.pool.get('res.district').browse(
            cr, uid, list(account_ids), context=context)
        ordered_districts = sorted(
            sorted(districts, key=operator.attrgetter('create_date'),
                   reverse=True),
            key=operator.attrgetter('active'), reverse=True)
        return ordered_districts

    def _model_is_installed(self, cr, uid, model, context=None):
        proxy = self.pool.get('ir.model')
        domain = [('model', '=', model)]
        return proxy.search_count(cr, uid, domain, context=context) > 0

    def merge_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

#         context = dict(context or {}, active_test=False)
#         this = self.browse(cr, uid, ids[0], context=context)
#         sql ='''
#             SELECT count(id), name 
#             FROM res_district 
#             group by name
#             having count(id)>1
#         '''
#         cr.execute(sql)
#         for i in cr.dictfetchall():
#             sql ='''
#                 SELECT id from res_district where name = '%s'
#                 order by id
#             '''%(i['name'])
#             cr.execute(sql)
#             i = 1
#             district_to = district_from = False
#             for j in cr.dictfetchall():
#                 if i == 1:
#                     district_from = j['id']
#                     i +=1
#                     continue
#                 if i == 2:
#                     district_to = self.pool.get('res.district').browse(cr,uid,j['id'])
#                     i +=1
#                     continue
#                 
#             p_ids = [district_to]
#             district_ids = set(map(int, district_from and
#                                   [district_to, district_from] or
#                                   p_ids))
#             
#             self._merge(cr, uid, district_ids, district_to,
#                     context=context)
        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)
        p_ids = [this.district_to]
        district_ids = set(map(int, this.district_from and
                              [this.district_to, this.district_from] or
                              p_ids))
        if not list(district_ids):
            raise UserError(_('Error!'), _(
                """The account from must be selected for
                    this option."""))
        else:
            self._merge(cr, uid, district_ids, this.district_to,
                        context=context)
        return True
