# coding: utf-8
from __future__ import absolute_import
import functools
import itertools
import logging
import operator
import openerp
from openerp.osv import osv, orm
from openerp.osv import fields
from openerp.osv.orm import browse_record
from openerp.tools.translate import _

_logger = logging.getLogger('base.partner.merge')


def is_integer_list(ids):
    return all(isinstance(i, (int, long)) for i in ids)


class MergePartnerAutomatic(osv.TransientModel):
    _name = 'base.partner.merge.automatic.wizard'

    _columns = {
        'state': fields.selection([('option', 'Option'),
                                   ('selection', 'Selection'),
                                   ('finished', 'Finished')],
                                  'State',
                                  readonly=True,
                                  required=True),
        'partner_from': fields.many2one('res.partner',
                                        string='Partner from'),
        'partner_to': fields.many2one('res.partner',
                                      string='Partner to'),
        'maximum_group': fields.integer("Maximum of Group of Contacts"),
    }

    _defaults = {
        'state': 'option'
    }

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

    def _update_foreign_keys(self, cr, uid, src_partners, dst_partner,
                             model=None, context=None):
        # find the many2one relation to a partner
        partner_bad = []
        
        self.get_fk_on(cr, 'res_partner')
        for table, column in cr.fetchall():
            if 'base_partner_merge_' in table:
                continue
            
            partner_ids = tuple(map(int, src_partners))

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
            for partner_id in partner_ids:
                cr.execute(query, (
                    dst_partner.id, partner_id, dst_partner.id))
        return partner_bad

    def _update_reference_fields(self, cr, uid, src_partners,
                                 dst_partner, context=None):
        partner_bad = []

        def update_records(model, src, field_model='model',
                           field_id='res_id', context=None):
            proxy = self.pool.get(model)
            if proxy is None:
                return
            domain = [(field_model, '=', 'res.partner'), (
                field_id, '=', src.id)]
            ids = proxy.search(
                cr, openerp.SUPERUSER_ID, domain, context=context)
            return proxy.write(cr, openerp.SUPERUSER_ID, ids,
                               {field_id: dst_partner.id},
                               context=context)

        update_records = functools.partial(update_records,
                                           context=context)

        proxy = self.pool['ir.model.fields']
        domain = [('ttype', '=', 'reference')]
        record_ids = proxy.search(
            cr, openerp.SUPERUSER_ID, domain, context=context)

        for record in proxy.browse(cr, openerp.SUPERUSER_ID, record_ids,
                                   context=context):
            proxy_model = self.pool[record.model]

            field_type = proxy_model._columns.get(record.name).__class__._type

            if field_type == 'function':
                continue

            for partner in src_partners:
                domain = [
                    (record.name, '=', 'res.partner,%d' % partner.id)
                ]
                model_ids = proxy_model.search(
                    cr, openerp.SUPERUSER_ID, domain, context=context)
                values = {
                    record.name: 'res.partner,%d' % dst_partner.id,
                }
                proxy_model.write(
                    cr, openerp.SUPERUSER_ID, model_ids, values,
                    context=context)
        return partner_bad

    def _update_values(self, cr, uid, src_partners,
                       dst_partner, context=None):
        partner_bad = []
        columns = dst_partner._columns

        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item

        values = dict()
        for column, field in columns.iteritems():
            if field._type not in ('many2many', 'one2many') and not \
                    isinstance(field, fields.function):
                for item in itertools.chain(src_partners, [dst_partner]):
                    if item[column]:
                        values[column] = write_serializer(column, item[column])
        return partner_bad

    def close_cb(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

    def _merge(self, cr, uid, partner_ids, dst_partner=None, context=None):
        proxy = self.pool.get('res.partner')
        partner_ids = proxy.exists(
            cr, uid, list(partner_ids), context=context)
        if len(partner_ids) < 2:
            return True

        if len(partner_ids) > 10:
            raise osv.except_osv(_('Error!'), _(
                """
                For safety reasons, you cannot merge more than 10 partners
                together. You can re-open the wizard several
                times if needed.
                """))
        if dst_partner and dst_partner.id in partner_ids:
            src_partners = proxy.browse(cr, uid, [
                                        id for id in partner_ids
                                        if id != dst_partner.id],
                                        context=context)
        else:
            ordered_partners = self._get_ordered_partner(
                cr, uid, partner_ids, context)
            dst_partner = ordered_partners[-1]
            dst_partner = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)

        if openerp.SUPERUSER_ID != uid and \
                self._model_is_installed(cr, uid, 'account.move.line',
                                         context=context) and \
                self.pool.get('account.move.line').\
        search(cr, openerp.SUPERUSER_ID,
                    [('partner_id', 'in', [partner.id for partner in
                                           dst_partner])],
                    context=context):
            raise osv.except_osv(_('Error!'), _(
                """Only the destination partner may be linked to existing
                   Journal Items. Please ask the Administrator if you need
                   to merge several partners linked to existing Journal
                   Items."""))
        call_it = lambda function: function(
            cr, uid, src_partners, dst_partner, context=context)
        partner_bad = []

        partner_bad += call_it(self._update_foreign_keys)
        partner_bad += call_it(self._update_reference_fields)
        partner_bad += call_it(self._update_values)
        partner_bad = set(partner_bad)
        for partner in src_partners:
            if partner.id not in partner_bad:
                #THANH: Update it to inactive
                partner.write({'active':False})
                proxy.exists(cr, uid, partner.id, context=context)
        return True

    def _get_ordered_partner(self, cr, uid, partner_ids, context=None):
        partners = self.pool.get('res.partner').browse(
            cr, uid, list(partner_ids), context=context)
        ordered_partners = sorted(
            sorted(partners, key=operator.attrgetter('create_date'),
                   reverse=True),
            key=operator.attrgetter(
                'active'),
            reverse=True)
        return ordered_partners

    def _model_is_installed(self, cr, uid, model, context=None):
        proxy = self.pool.get('ir.model')
        domain = [('model', '=', model)]
        return proxy.search_count(cr, uid, domain, context=context) > 0

    def merge_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)
        p_ids = [this.partner_to]
        partner_ids = set(map(int, this.partner_from and
                              [this.partner_to, this.partner_from] or
                              p_ids))
        if not list(partner_ids):
            raise osv.except_osv(_('Error!'), _(
                """The partner from must be selected for
                    this option."""))
        else:
            self._merge(cr, uid, partner_ids, this.partner_to,
                        context=context)
        return True

