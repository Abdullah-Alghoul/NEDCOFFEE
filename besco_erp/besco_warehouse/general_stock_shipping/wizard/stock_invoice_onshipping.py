# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError, RedirectWarning
from lxml import etree

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}


class stock_invoice_onshipping(osv.osv_memory):

    def _get_journal(self, cr, uid, context=None):
        res = self._get_journal_id(cr, uid, context=context)
        if res:
            return res[0][0]
        return False

    def _get_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}

        model = context.get('active_model')
        if not model or 'stock.picking' not in model:
            return []

        model_pool = self.pool.get(model)
        journal_obj = self.pool.get('account.journal')
        res_ids = context and context.get('active_ids', [])
        vals = []
        browse_picking = model_pool.browse(cr, uid, res_ids, context=context)

        for pick in browse_picking:
            domain = [('type', 'in', ['sale', 'sale_refund', 'purchase', 'purchase_refund'])]
            if pick.move_lines:
                src_usage = pick.move_lines[0].location_id.usage
                dest_usage = pick.move_lines[0].location_dest_id.usage
                type = pick.picking_type_id.code
                if type == 'outgoing' and dest_usage == 'supplier':
                    journal_type = 'purchase_refund'
                elif type == 'outgoing' and dest_usage == 'customer':
                    journal_type = 'sale'
                elif type == 'incoming' and src_usage == 'supplier':
                    journal_type = 'purchase'
                elif type == 'incoming' and src_usage == 'customer':
                    journal_type = 'sale_refund'
                else:
                    journal_type = 'sale'
                domain = [('type', '=', journal_type)]

            value = journal_obj.search(cr, uid, domain)
            for jr_type in journal_obj.browse(cr, uid, value, context=context):
                t1 = jr_type.id,jr_type.name
                if t1 not in vals:
                    vals.append(t1)
        return vals
    
    def _default_payment_method(self, cr, uid, context=None):
        if context is None:
            context = {}

        journal_obj = self.pool.get('account.journal')
        domain = [('type', 'in', ['cash'])]
        value = journal_obj.search(cr, uid, domain)
        return value and value[0] or False
    
    _name = "stock.invoice.onshipping"
    _description = "Stock Invoice Onshipping"

    _columns = {
        'partner_id': fields.many2one('res.partner', string='Partner', required=True),
        'journal_id': fields.selection(_get_journal_id, 'Destination Journal',required=True),
        'group': fields.boolean("Group by partner"),
        'invoice_date': fields.date('Invoiced Date'),
        
        #KIET: Auto pay
        'auto_pay':fields.boolean("Auto Payment"),
        'sup_date': fields.date('Vendor Invoice Date'),
        'payment_method':fields.many2one('account.journal', string='Payment Method', domain="[('type','in',('cash','bank'))]"),
        'payment_date':fields.date('Payment Date'),
        'invoice_number':fields.char('Invoice Number'),
    }

    _defaults = {
        'journal_id' : _get_journal,
        'payment_method': _default_payment_method,
    }
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(stock_invoice_onshipping, self).default_get(cr, uid, fields, context=context)
        if context.get('active_id',False):
            active_obj = self.pool.get('stock.picking').browse(cr,uid,context['active_id'])
            res.update({'partner_id': active_obj.partner_id and active_obj.partner_id.id or False,
                        'invoice_date': active_obj.date_done,
                        'sup_date': active_obj.date_done,
                        'payment_date': active_obj.date_done,}) 
        return res
    
    def fields_view_get(self, cr, uid, view_id=None, view_type=False, context=None, toolbar=False, submenu=False):
        if context is None:
            context = {}
        res = super(stock_invoice_onshipping,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        
        if view_type == 'form' and context.get('active_id',False):
            doc = etree.XML(res['arch'])
            #Thanh: Filter partner_id in Picking Form
            active_obj = self.pool.get('stock.picking').browse(cr,uid,context['active_id'])
            if active_obj.picking_type_id:
                picking_type = active_obj.picking_type_id
                if picking_type.code == 'incoming':
                    for node in doc.xpath("//field[@name='partner_id']"):
                        node.set('string', "Vendor")
                        node.set('domain', "[('supplier', '=', True)]")
                        node.set('context', "{'default_company_type': 'company', 'default_supplier': True, 'default_customer': False}")
                    for node in doc.xpath("//field[@name='sup_date']"):
                        node.set('invisible', "False")
                        node.set('required', "True")
                elif picking_type.code == 'outgoing':
                    for node in doc.xpath("//field[@name='partner_id']"):
                        node.set('string', "Customer")
                        node.set('domain', "[('customer', '=', True)]")
                        node.set('context', "{'default_company_type': 'company', 'default_supplier': False, 'default_customer': True}")
            #THANH: 
            xarch, xfields = self._view_look_dom_arch(cr, uid, doc, view_id, context=context)
            res['arch'] = xarch
            res['fields'] = xfields
        return res
    
    def _pay_invoice(self,cr,uid,invoice_id,journal_id,context=None):
        journal_id = self.pool.get('account.journal').browse(cr,uid,journal_id)
        payment = self.pool.get('account.payment')
            
        fields_list = ['communication', 'currency_id', 'invoice_ids', 'payment_difference', 'partner_id', 
                         'payment_method_id', 'payment_difference_handling', 'journal_id', 'state', 'writeoff_account_id', 
                         'payment_date', 'partner_type', 'hide_payment_method', 'payment_method_code', 'amount', 
                         'payment_type']
        
#         inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        vals = payment.default_get(cr,uid,fields_list)
        vals.update({'invoice_ids': [(5,), (4, invoice_id)]})   
        invoice_defaults = payment.resolve_2many_commands(cr,uid,'invoice_ids', vals.get('invoice_ids'))
        

        if invoice_defaults and len(invoice_defaults) == 1:
            mod_obj = self.pool.get('ir.model.data')
            
            invoice = invoice_defaults[0]
            payment_type = invoice['type'] in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            if payment_type == 'inbound':
                dummy, payment_method = tuple(mod_obj.get_object_reference(cr, uid, 'account', "account_payment_method_manual_in"))
                journal_payment_methods = journal_id.inbound_payment_method_ids
            else:
                dummy, payment_method = tuple(mod_obj.get_object_reference(cr, uid, 'account', "account_payment_method_manual_out"))
                journal_payment_methods = journal_id.outbound_payment_method_ids
#             if journal_payment_methods and payment_method != journal_payment_methods.id:
#                 raise UserError(_('No appropriate payment method enabled on journal %s') % journal_id.name)
            if context.get('payment_date',False):
                vals['payment_date'] = context.get('payment_date',False)
            vals['communication'] = invoice['reference']
            vals['currency_id'] = invoice['currency_id'][0]
            vals['payment_type'] = invoice['type'] in ('out_invoice', 'in_refund') and 'inbound' or 'outbound'
            vals['partner_type'] = MAP_INVOICE_TYPE_PARTNER_TYPE[invoice['type']]
            vals['partner_id'] = invoice['partner_id'][0]
            vals['amount'] = invoice['residual']
            vals['journal_id'] = journal_id.id
            vals['payment_method_id'] = payment_method
            
        new_payment_id = payment.create(cr,uid,vals)
        payment.browse(cr,uid,new_payment_id).post()

    def open_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        this = self.browse(cr,uid,ids[0])
        
        context.update({
            'invoice_number':this.invoice_number,
            'sup_date':this.sup_date,
            'payment_date':this.payment_date,
        })
        
        invoice_ids = []
        res = self.create_invoice(cr, uid, ids, context=context)
        invoice_ids += res.values()
        if not invoice_ids:
            raise osv.except_osv(_('Error!'), _('Please create Invoices.'))
        if invoice_ids:
            if this.auto_pay == True:
                for invoice in self.pool.get('account.invoice').browse(cr,uid,invoice_ids):
                    invoice.signal_workflow('invoice_open')
                    self._pay_invoice(cr, uid, invoice.id, this.payment_method.id, context)
                    
        return {'type': 'ir.actions.act_window_close'}
    
    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        picking_pool = self.pool.get('stock.picking')
        onshipdata_obj = self.read(cr, uid, ids, ['partner_id', 'journal_id', 'group', 'invoice_date'])
        if context.get('new_picking', False):
            onshipdata_obj['id'] = onshipdata_obj.new_picking
            onshipdata_obj[ids] = onshipdata_obj.new_picking
        context['date_inv'] = onshipdata_obj[0]['invoice_date']
        active_ids = context.get('active_ids', [])
        res = {}
        if context.get('active_id',False):
            cr.execute('UPDATE stock_picking SET partner_id=%s WHERE id=%s'%(onshipdata_obj[0]['partner_id'][0], context['active_id']))
            active_picking = picking_pool.browse(cr, uid, context.get('active_id',False), context=context)
            inv_type = picking_pool._get_invoice_type(active_picking)
            context['inv_type'] = inv_type
            if isinstance(onshipdata_obj[0]['journal_id'], tuple):
                onshipdata_obj[0]['journal_id'] = onshipdata_obj[0]['journal_id'][0]
            res = picking_pool.action_invoice_create(cr, uid, active_ids,
                  journal_id = onshipdata_obj[0]['journal_id'],
                  group = onshipdata_obj[0]['group'],
                  type = inv_type,
                  context=context)
        return res

stock_invoice_onshipping()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
