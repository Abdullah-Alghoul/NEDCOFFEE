# -*- coding: utf-8 -*-
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

from collections import OrderedDict

import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools import float_compare, float_is_zero
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.exceptions import UserError, AccessError

from lxml import etree
import base64
import xlrd

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _columns = {
              'purchase_contract_id': fields.many2one('purchase.contract', string='Purchase Contract',
                      readonly=True, states={'draft': [('readonly', False)]}, required=False),
              'sale_contract': fields.boolean('Sale Contract')
              }
    
    _defaults = {'sale_contract': False}
    
    def get_currency_id(self, cr, uid, picking):
        if picking and picking.purchase_contract_id and picking.purchase_contract_id:
            return picking.purchase_contract_id.currency_id.id or False
        else:
            return False
        
    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        invoice_vals = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id, context=context)
        invoice_vals.update({'purchase_contract_id':picking.purchase_contract_id.id or False})
        return invoice_vals
    
    def domain_partner_id(self, cr, uid, ids, partner_id, context=None):
        domain = {}
        if partner_id:
            purchase_contract_ids = self.pool.get('purchase.contract').search(cr, uid, [('partner_id', '=', partner_id), ('state', '=', 'approved')]) or False
            sale_contract_ids = self.pool.get('sale.contract').search(cr, uid, [('partner_id', '=', partner_id), ('state', '=', 'approved')]) or False
            
            if purchase_contract_ids or sale_contract_ids:
                domain.update({'purchase_contract_id': [('id', '=', purchase_contract_ids)],
                               'sale_contract_id': [('id', '=', sale_contract_ids)]})
            else:
                domain.update({'purchase_contract_id': [('id', '=', False)],
                              'sale_contract_id': [('id', '=', False)]})
        else:
            purchase_contract_ids = self.pool.get('purchase.contract').search(cr, uid, [('state', '=', 'approved')]) or False
            sale_contract_ids = self.pool.get('sale.contract').search(cr, uid, [('state', '=', 'approved')]) or False
            if purchase_contract_ids or sale_contract_ids:
                domain.update({'purchase_contract_id': [('id', '=', purchase_contract_ids)],
                               'sale_contract_id': [('id', '=', sale_contract_ids)]})
        return {'domain': domain}
    
    def onchange_purchase_contract_id(self, cr, uid, ids, purchase_contract_id, context=None):
        values = {}
        domain = {}
        if not purchase_contract_id:
            return {'domain': {'partner_id': []}}
        
        contract_obj = self.pool.get('purchase.contract').browse(cr, uid, purchase_contract_id)
        values = {'partner_id': contract_obj.partner_id.id or False} 
        domain = {'partner_id': [('id', '=', contract_obj.partner_id.id)]}
        
        return {'value': values, 'domain':domain}
    
    def onchange_sale_contract_id(self, cr, uid, ids, sale_contract_id, context=None):
        values = {}
        domain = {}
        if not sale_contract_id:
            values = {'sale_contract': False} 
            return {'domain': {'partner_id': []}, 'value': values}
        
        contract_obj = self.pool.get('sale.contract').browse(cr, uid, sale_contract_id)
        
        values = {'partner_id': contract_obj.partner_id.id or False, 'sale_contract': True} 
        domain = {'partner_id': [('id', '=', contract_obj.partner_id.id)]}
        
        return {'value': values, 'domain':domain}
    
    def button_load_pc(self, cr, uid, ids, context=None):
        moves = self.pool.get('stock.move')
        contract = self.pool.get('purchase.contract') 
        vals = {}
        new_id = {}
        
        for this in self.browse(cr, uid, ids):
            sql = '''
                DELETE FROM stock_move WHERE picking_id = %s
            ''' % (this.id)
            cr.execute(sql)
            if this.picking_type_id.code == 'incoming':
                if this.purchase_contract_id:
                    contract_obj = contract.browse(cr, uid, this.purchase_contract_id.id)
                    if this.picking_type_id.is_consignment_agreement:
                        if this.purchase_contract_id.type in ('purchase', 'consign'):
                            for i in contract_obj.contract_line:
                                vals = {'picking_id': this.id, 'name': i.name, 'product_id': i.product_id.id, 'product_uom': i.product_uom.id,
                                        'product_uom_qty': 0.0, 'price_unit': i.price_unit, 'tax_id': [(6, 0, [x.id for x in i.tax_id])],
                                        'picking_type_id': this.picking_type_id.id, 'location_id': this.location_id.id,
                                        'location_dest_id': this.location_dest_id.id, 'date': this.min_date,
                                        'exchange_rate':this.purchase_contract_id.exchange_rate or 1,
                                        'currency_id':this.purchase_contract_id.currency_id.id or False,
                                        'type': 'incoming', 'state': 'draft', 'scrapped': False, 'purchase_contract_id': i.contract_id.id}
                                new_id = moves.create(cr, uid, vals, context)
                        else:
                            error = "Contract Information is not Consignment Agreement."
                            raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
                    else:
                        if this.purchase_contract_id.type in ('purchase', 'consign'):
                            for i in contract_obj.contract_line:
                                vals = {'picking_id': this.id, 'name': i.name, 'product_id': i.product_id.id,
                                        'product_uom': i.product_uom.id,
                                        'product_uom_qty': 0.0, 'price_unit': i.price_unit, 'tax_id': [(6, 0, [x.id for x in i.tax_id])],
                                        'picking_type_id': this.picking_type_id.id, 'location_id': this.location_id.id,
                                        'location_dest_id': this.location_dest_id.id, 'date': this.min_date,
                                        'exchange_rate':this.purchase_contract_id.exchange_rate or 1,
                                        'currency_id':this.purchase_contract_id.currency_id.id or False,
                                        'type': 'incoming', 'state': 'draft', 'scrapped': False, 'purchase_contract_id': i.contract_id.id}
                                new_id = moves.create(cr, uid, vals, context)
                        else:
                            error = "Contract Information is not Purchase Contract."
                            raise osv.except_osv(unicode('Error!', 'utf8'), unicode(error, 'utf8'))
        return True
    
    def button_load_sc(self, cr, uid, ids, context=None):
        moves = self.pool.get('stock.move')
        contract = self.pool.get('sale.contract') 
        for this in self.browse(cr, uid, ids):
            sql = '''
                DELETE FROM stock_move WHERE picking_id = %s
            ''' % (this.id)
            cr.execute(sql)
            if this.picking_type_id.code == 'outgoing':
                if this.sale_contract_id:
                    contract_obj = contract.browse(cr, uid, this.sale_contract_id.id)
                    if contract_obj.type == 'local': 
                        product_qty = new_qty = 0.0
                        for i in contract_obj.contract_line:
                            for gdn in contract_obj.picking_ids:
                                if gdn.state != 'cancel':
                                    for gdn_line in gdn.move_lines:
                                        if gdn_line.product_id == i.product_id:
                                            product_qty += gdn_line.product_uom_qty or 0.0
                            new_qty = i.product_qty - product_qty
                            moves.create(cr, uid, {'picking_id': this.id or False, 'name': i.name, 'product_id': i.product_id.id or False,
                                'product_uom': i.product_uom.id or False, 'type': this.picking_type_id.code or False,
                                'product_uom_qty': new_qty, 'price_unit': i.price_unit or 0.0, 'tax_id': [(6, 0, [x.id for x in i.tax_id])] or False,
                                'picking_type_id': this.picking_type_id.id or False, 'location_id': this.location_id.id or False, 'state': 'draft',
                                'location_dest_id': this.location_dest_id.id or False, 'date': this.min_date or False, 'scrapped': False,
                                'exchange_rate':this.sale_contract_id.exchange_rate or 1, 'currency_id':this.sale_contract_id.currency_id.id or False,
                                'date_expected': this.min_date or False, 'partner_id': this.partner_id.id or False, 'company_id': this.company_id.id or False})
                    if contract_obj.type == 'export':
                        if this.delivery_id:
                            do_obj = self.pool.get('delivery.order').browse(cr, uid, this.delivery_id.id)
                            product_qty = 0.0
                            for i in contract_obj.contract_line:
                                for do_line in do_obj.delivery_order_ids:
                                    if do_line.product_id == i.product_id:
                                        product_qty = do_line.product_qty
                                moves.create(cr, uid, {'picking_id': this.id or False, 'name': i.name, 'product_id': i.product_id.id or False,
                                'product_uom': i.product_uom.id or False, 'type': this.picking_type_id.code or False,
                                'product_uom_qty': product_qty, 'price_unit': i.price_unit or 0.0, 'tax_id': [(6, 0, [x.id for x in i.tax_id])] or False,
                                'picking_type_id': this.picking_type_id.id or False, 'location_id': this.location_id.id or False, 'state': 'draft',
                                'location_dest_id': this.location_dest_id.id or False, 'date': this.min_date or False, 'scrapped': False,
                                'exchange_rate':this.sale_contract_id.exchange_rate or 1, 'currency_id':this.sale_contract_id.currency_id.id or False,
                                'date_expected': this.min_date or False, 'partner_id': this.partner_id.id or False, 'company_id': this.company_id.id or False})
                        
        return True
    
stock_picking()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    _columns = {
              'tax_id': fields.many2many('account.tax', 'stock_move_tax', 'move_id', 'tax_id', 'Taxes', readonly=True, states={'draft': [('readonly', False)]}),
              'purchase_contract_id': fields.related('picking_id', 'purchase_contract_id', type='many2one', relation='purchase.contract', string='Purchase Contract', readonly=True),
              #'sale_contract_id': fields.related('picking_id', 'sale_contract_id', type='many2one', relation='sale.contract', string='Sale Contract', readonly=True) 
              }
stock_move()
