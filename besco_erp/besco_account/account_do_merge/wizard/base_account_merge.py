# coding: utf-8
import functools
import itertools
import operator
from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import UserError
from openerp.osv.orm import browse_record

def is_integer_list(ids):
    return all(isinstance(i, (int, long)) for i in ids)


class WizardAccountMergeAutomatic(models.TransientModel):
    _name = 'wizard.account.merge.automatic'
    
    state = fields.Selection([('option', 'Option'),
                               ('selection', 'Selection'),
                               ('finished', 'Finished')],
                              'State', readonly=True, required=True, default='option')
    account_from = fields.Many2one('account.account', string='Account from')
    account_to = fields.Many2one('account.account', string='Account to')
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
        
        self.get_fk_on(cr, 'account_account')
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

    def _update_reference_fields(self, cr, uid, src_accounts, dst_account, context=None):
        account_bad = []

        def update_records(model, src, field_model='model',
                           field_id='res_id', context=None):
            proxy = self.pool.get(model)
            if proxy is None:
                return
            domain = [(field_model, '=', 'account.account'), (
                field_id, '=', src.id)]
            ids = proxy.search(
                cr, SUPERUSER_ID, domain, context=context)
            return proxy.write(cr, SUPERUSER_ID, ids,
                               {field_id: dst_account.id},
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

            for account in src_accounts:
                domain = [
                    (record.name, '=', 'account.account,%d' % account.id)
                ]
                model_ids = proxy_model.search(
                    cr, SUPERUSER_ID, domain, context=context)
                values = {
                    record.name: 'account.account,%d' % dst_account.id,
                }
                proxy_model.write(
                    cr, SUPERUSER_ID, model_ids, values,
                    context=context)
        return account_bad

    def _update_values(self, cr, uid, src_accounts, dst_account, context=None):
        account_bad = []
        columns = dst_account._columns

        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item

        values = dict()
        for column, field in columns.iteritems():
            if field._type not in ('many2many', 'one2many'):
                for item in itertools.chain(src_accounts, [dst_account]):
                    if item[column]:
                        values[column] = write_serializer(column, item[column])
        return account_bad

    def close_cb(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

    def _merge(self, cr, uid, account_ids, dst_account=None, context=None):
        proxy = self.pool.get('account.account')
        account_ids = proxy.exists(
            cr, uid, list(account_ids), context=context)
        if len(account_ids) < 2:
            return True

        if len(account_ids) > 10:
            raise UserError(_('Error!'), _(
                """
                For safety reasons, you cannot merge more than 10 accounts
                together. You can re-open the wizard several
                times if needed.
                """))
        if dst_account and dst_account.id in account_ids:
            src_accounts = proxy.browse(cr, uid, [
                                        id for id in account_ids
                                        if id != dst_account.id],
                                        context=context)
        else:
            ordered_accounts = self._get_ordered_account(
                cr, uid, account_ids, context)
            dst_account = ordered_accounts[-1]
            dst_account = ordered_accounts[:-1]

        if SUPERUSER_ID != uid and \
                self._model_is_installed(cr, uid, 'account.move.line',
                                         context=context) and \
                self.pool.get('account.move.line').\
        search(cr, SUPERUSER_ID,
                    [('account_id', 'in', [account.id for account in dst_account])],
                    context=context):
            raise UserError(_('Error!'), _(
                """Only the destination account may be linked to existing
                   Journal Items. Please ask the Administrator if you need
                   to merge several accounts linked to existing Journal
                   Items."""))
        call_it = lambda function: function(
            cr, uid, src_accounts, dst_account, context=context)
        account_bad = []

        account_bad += call_it(self._update_foreign_keys)
        account_bad += call_it(self._update_reference_fields)
        account_bad += call_it(self._update_values)
        account_bad = set(account_bad)
        for account in src_accounts:
            if account.id not in account_bad:
                #THANH: Update it to inactive
                account.write({'deprecated':True})
                proxy.exists(cr, uid, account.id, context=context)
        return True

    def _get_ordered_account(self, cr, uid, account_ids, context=None):
        accounts = self.pool.get('account.account').browse(
            cr, uid, list(account_ids), context=context)
        ordered_accounts = sorted(
            sorted(accounts, key=operator.attrgetter('create_date'),
                   reverse=True),
            key=operator.attrgetter('deprecated'), reverse=True)
        return ordered_accounts

    def _model_is_installed(self, cr, uid, model, context=None):
        proxy = self.pool.get('ir.model')
        domain = [('model', '=', model)]
        return proxy.search_count(cr, uid, domain, context=context) > 0

    def merge_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)
        p_ids = [this.account_to]
        account_ids = set(map(int, this.account_from and
                              [this.account_to, this.account_from] or
                              p_ids))
        if not list(account_ids):
            raise UserError(_('Error!'), _(
                """The account from must be selected for
                    this option."""))
        else:
            self._merge(cr, uid, account_ids, this.account_to,
                        context=context)
        return True

