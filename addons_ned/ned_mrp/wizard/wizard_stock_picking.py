# -*- coding: utf-8 -*-

import time
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api, fields, models
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning

from lxml import etree
import base64
import xlrd
import base64
import os
from openerp import modules
from openerp.tools.translate import _
DATE_FORMAT = "%Y-%m-%d"
import string
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

class AccountPaymentInvoice(models.Model):
    _inherit = "account.payment.invoice"
    
    origin = fields.Char('Origin')

class wizard_import_production_result(models.TransientModel):
    _name = "wizard.import.production.result"
    
    file =  fields.Binary('File', help='Choose file Excel', copy=False)
    file_name =  fields.Char('Filename', size=100, readonly=True)
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    result_id = fields.Many2one('mrp.operation.result')
    production_shift =fields.Selection([
                        ('1','Ca 1'),
                        ('2','Ca 2'),
                        ('3','Ca 3'),], 'Ca', required=True, default="1" )
    
    production_id = fields.Many2one('mrp.production')
    
    @api.multi
    def payment_post(self):
        pay_ids = self.env['account.payment'].search([('state','=','draft')])
        for line in pay_ids:
            try:
                line.responsible = False
                line.post()
            except Exception, e:
                continue
    
    def remove_entries(self):
#         sql ='''
#             select am.ref, count(am.ref) from account_move am join account_move_line aml on am.id = aml.move_id
#             where am.ref like 'GDN-16%' and aml.account_id = 1768
#             group by am.ref having count(am.ref) >1 
#         '''
#         self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             move = self.env['account.move'].search([('ref','=',i['ref'])])
#             for j in move:
#                 stock_move = self.env['stock.move'].search([('entries_id','=',j.id)])
#                 if not stock_move:
#                     j.button_cancel()
#                     j.unlink()
        
        sql ='''
            SELECT id from stock_move 
                where location_id = 12 and location_dest_id = 9
                and entries_id is not null
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            stock_move = self.env['stock.move'].browse(i['id'])
            invoice = self.env['account.invoice'].search([('stock_move_id','=',stock_move.id)])
            if invoice:
                stock_move.partner_id = invoice.partner_id.id
                stock_move.origin = invoice.number
                stock_move.origin = invoice.number +'-' + invoice.sale_contract_id.name
                stock_move.entries_id.partner_id = invoice.partner_id.id
                stock_move.entries_id.ref = invoice.number + '-' + invoice.sale_contract_id.name
                for move_line in stock_move.entries_id.line_ids:
                    move_line.partner_id = invoice.partner_id.id
            else:
                stock_move.remove_fifo()
                stock_move.action_cancel()
                stock_move.unlink()
                
                
    
    @api.multi
    def remove_entries_inv_post(self):
#         invoice_ids = self.env['account.invoice'].search([('type','=','out_invoice')])
#         for line in invoice_ids:
#             if line.stock_move_id and line.stock_move_id.entries_id:
#                 line.stock_move_id.entries_id.button_cancel()
#                 line.stock_move_id.entries_id.unlink()
        
        
#         sql ='''
#             SELECT id 
#             FROM stock_move where picking_id in (
#                 SELECT id from stock_picking where picking_type_id in(2,6)
#             )
#             and entries_id is not null
#         ''' 
#         self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             move = self.env['stock.move'].browse(i['id'])
#             move.entries_id.button_cancel()
#             move.entries_id.unlink()
        
        move_ids = self.env['stock.move'].search([('location_id','=',73),('location_dest_id','=',12),('entries_id','!=',False)])
        for move in move_ids:
            move.entries_id.button_cancel()
            move.entries_id.unlink()
            
        
#         sql ='''
#             select id from account_move where ref like 'GDN-%'
#         ''' 
#         self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             move = self.env['account.move'].browse(i['id'])
#             move.button_cancel()
#             move.unlink()
        
                
            
            
    @api.multi
    def import_payment(self):
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                partner_code = False
                acc_id = False
                acc_code = False
                bcode =False
                for row in range(sh.nrows):
                    
                    
                    vals ={ 'payment_date': '2016-12-13', 'partner_bank_id': False, 'has_fee': False, 'show_invoice': True, 
                     'currency_id': 3, 'state': 'draft', 'payment_type': 'outbound', 'extend_payment': 'payment', 
                     'name': 'Draft Payment','communication':False,'partner_type':'supplier',
                     'invoice_journal_id':False,'amount':0,
                     'payment_method_id':2}
                    row_values = sh.row_values(row)
                    
                    exit = self.env['account.payment'].search([('responsible', '=' ,row_values[0])])
                    if exit:
                        continue
                    
                    vals['responsible']= row_values[0]
                    vals['source_document'] = row_values[0]
                    vals['name'] = row_values[2]
                    vals['payment_date']= row_values[3]
                    acc_code = row_values[4]
                    currency_id = False
                    
#                     if row_values[5] == 'USD' and acc_code in (112206,112209):
#                         print str(row_values[2])
#                         continue
                    if row_values[5] == 'USD':
                        currency_id = 3
                    else:
                        currency_id = 24
                    vals['currency_id'] = currency_id
                    vals['invoice_journal_id'] = 59
                    
                    vals['payment_reference'] = str(row_values[1]) + ' - ' + str(row_values[2])
                    
                    if bcode != acc_code:
                        bcode = acc_code
                        if bcode == 112213:
                            bcode = 112211
                        try:
                            acc_id = self.env['account.account'].search([('code', '=' ,int(bcode))])
                        except Exception, e:
                            print row_values[1]
                            continue
                    if not acc_id:
                        print bcode
                        raise
                    
                    if acc_code == 1111:
                        journal_id = self.env['account.journal'].search([('default_debit_account_id','=',acc_id.id)])
                    else:
                        journal_id = self.env['account.journal'].search([('default_debit_account_id','=',acc_id.id)])
                    if not journal_id:
                        raise
                    try:
                        vals['journal_id'] = journal_id.id
                    except Exception, e:
                        print journal_id
                    partner_code = row_values[8] or False
                    if partner_code =='NULL':
                        partner_code = False
                    partner_name = row_values[9] or False
                    partner = False
                    if partner_code:
                        partner = self.env['res.partner'].search([('partner_code', '=', partner_code)]) or False
                    else:
                        partner = self.env['res.partner'].search([('name', '=', partner_name)]) or False
                        
                    if not partner:
                        partner_vals={'partner_code':partner_code,
                             'name': partner_name or False, 'supplier': True,
                            'company_type': 'company', 
                            'active': True,
                            'property_account_payable_id':1621,
                            'property_account_receivable_id':1509,
                            'property_vendor_advance_acc_id':1621,
                            'property_customer_advance_acc_id':1509}
                        partner = self.env['res.partner'].create(partner_vals)
#                         print partner_name, partner_code
                    vals['partner_id'] = partner.id
                    communication = row_values[10]
                    vals['communication'] = communication
                    
                    res_bank_id = self.env['res.partner.bank'].search([('partner_id','=',partner.id)],limit = 1)
                    if res_bank_id:
                        vals['partner_bank_id'] = res_bank_id.id
                    try:
                        new_id = self.env['account.payment'].create(vals)
                    except Exception, e:
                        print '-------------'+ str(row_values[2]) + '--' + + str(row_values[7]) 
            count = 1
            loi= 1
            for i in [1]:
                try:
                    sh = excel.sheet_by_index(i)
                except Exception, e:
                    raise UserError(('Please select File'))
                if sh:
                    partner_code = False
                     
                    for row in range(sh.nrows):
                        row_values = sh.row_values(row)
                        acc_code = False
                        vals = {u'currency_id': False, u'date': False, u'partner_id': False, u'journal_id': False, u'company_id': 1}
                         
                        id = row_values[24]
                        note = row_values[23]
                        acc_code = row_values[1]
                        vat_in = row_values[3] or False
                        price = row_values[4] or 0
                        if not price:
                            price = row_values[7] or 0
                             
                        reference = row_values[11]
                        number = row_values[12]
                        date = row_values[13]
                        narration = row_values[23]
                        
                        if vat_in == '10TV1':
                            vals['tax_ids']= [[6, False,  [12]]]
                        elif vat_in == '05TV1':
                            vals['tax_ids']= [[6, False,  [13]]]
                        elif vat_in =='00TV0':
                            vals['tax_ids']= [[6, False,  [14]]]
                        else:
                            vals['tax_ids']= [[6, False,  []]]
                        
                        try:
                            self.env.cr.commit()
                            payment_id = False
                            sql ='''
                                SELECT ID from account_payment where source_document = '%s'
                            '''%(id)
                            
                            self.env.cr.execute(sql)
                            for i in self.env.cr.dictfetchall():
                                payment_id = self.env['account.payment'].browse(i['id'])
                            if not payment_id:
                                print 'Tim khong thay - '+ str(id) + '-------------' 
                                continue
                        except Exception, e:
                            loi +=1
                            print 'AAAA',e
                            continue
                         
                         
                        ex_payment_id = self.env['account.payment.invoice'].search([('origin','=',row_values[0])],limit = 1)
                        if ex_payment_id:
                            continue
                              
                        acc_id = self.env['account.account'].search([('code', '=' ,int(acc_code))])
                        if not acc_id:
                            print acc_code
                            raise
                         
                        partner_code = row_values[14]
                        partner = False
                        if partner_code and partner_code !='NULL':
                            partner = self.env['res.partner'].search([('name', '=', partner_code)],limit =1) or False
                             
                        if not partner:
                            if partner_code != 'NULL':
                                partner_vals={
                                    'street':row_values[15],
                                    'vat':row_values[16],
                                    'name': partner_code or False, 
                                    'supplier': True,
                                    'company_type': 'company', 
                                    'active': True,
                                    'property_account_payable_id':1621,
                                    'property_account_receivable_id':1509,
                                    'property_vendor_advance_acc_id':1621,
                                    'property_customer_advance_acc_id':1509}
                                partner = self.env['res.partner'].create(partner_vals)
    #                         print partner_name, partner_code
                                vals['partner_id'] = partner.id
                            else:
                                vals['partner_id'] =payment_id.partner_id.id
                        else:
                            vals['partner_id'] = partner.id
                                 
                        vals['currency_id'] =payment_id.currency_id.id
                        vals['journal_id'] =payment_id.journal_id.id
                        vals['origin'] = row_values[0]
                        if reference == 'NULL':
                            vals['reference']= False
                        else:
                            vals['reference']=reference
                             
                        if number == 'NULL':
                            vals['number']=False
                        else:
                            vals['number']=number
                             
                        if date == 'NULL':
                            vals['date']= payment_id.payment_date
                        else:
                            vals['date']= date
                        vals['narration']= note
                         
                        if ex_payment_id:
                            continue
                         
                        val_line ={
                                   'name':note,
                                   'account_id':acc_id.id,
                                   'price_unit':price,
                                   'quantity':1,
                                   'price_subtotal':price
                        }
                        vals['invoice_lines']= [[0, False, val_line]]
                        vals['tax_correction'] = row_values[5] or 0.0
                        vals['line_id'] = payment_id.id
                        if row_values[1] == 13311:
                            vals['sub_total'] =  0.0
                            vals['tax_correction'] =  0.0
                            val_line['price_unit'] =  row_values[7]
                            val_line['price_subtotal'] =  row_values[7]
                            vals['tax_ids']= False
                         
                        try:
#                             if vals['number']:
#                                 ser_id = self.env['account.payment.invoice'].search([('number','=',vals['number'])])
#                                 if ser_id:
#                                     vals['tax_correction'] += ser_id.tax_correction or 0.0
#                                     val_line['invoice_id'] = ser_id.id
#                                     self.env['account.payment.invoice.line'].create(val_line)
#                                     ser_id.tax_correction = vals['tax_correction']
#                                     ser_id._compute_total()
#                                     print row_values[0]
#                                 else:
#                                     id_new = self.env['account.payment.invoice'].create(vals)
#                                     id_new._compute_total()
#                             else:
                            id_new = self.env['account.payment.invoice'].create(vals)
                            id_new._compute_total()
                            payment_id._onchange_payment_lines()
                            #new_id.name =row_values[2]
                        except Exception, e:
                            print '-------------'+ str(row_values[0]) + '--' + str(id)
            
            
#         payment_ids = self.env['account.payment'].search([('state','=','draft'),('payment_reference','!=',False)])         
#         for line in payment_ids:
#             line.post()
#         return 
    
    def import__MarketPrice(self):
        count =0
        distirct = False
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                
                partner_code = False
                for row in range(sh.nrows):
                    row_values = sh.row_values(row)
                    
                    vals ={
                    'mdate' : row_values[0],
                    'interbankrate' : row_values[1],
                    'price' : row_values[2],
                    'bankceiling' : row_values[3],
                    'note' : row_values[4],
                    'bank_floor' : row_values[5],
                    'eximbank' : row_values[6],
                    'techcombank' : row_values[7],
                    'acb_or_vietinbank' : row_values[8],
                    'commercialrate' : row_values[9],
                    'exporter_faq_price' : row_values[10],
                    'privateDealer_faq_price' : row_values[11],
                    'liffe_month' : row_values[12],
                    'liffe' : row_values[13],
                    'g2difflocal' : row_values[14],
                    'g2difffob' : row_values[15]
                    }
                    try:
                        self.env['market.price'].create(vals)
                    except Exception, e:
                        print row_values[0], row_values[1]
                    
                    
                    
                    
                    ## update district
                    
    
    @api.multi
    def report_kqsx(self):
#         self.remove_ens()
#         self.import_partner()
#         self.update_partner_account()
#         self.import__masterpartner()
#         self.import__MarketPrice()
        #self.update_picking()
        #self.update_delivery_picking()
        #self.update_movesa()
#         self.grn_dienchinh()
        self.update_product()
#         self.update_entr()
#         self.update_itr()
#         self.compute_taxes()
#         self.update_mrp()
#         data = {}
#         data['ids'] = self.env.context.get('active_ids', [])
#         data['model'] = 'wizard.import.production.result'
#         data['form'] = self.read([])[0]
#         return {'type': 'ir.actions.report.xml', 'report_name': 'report_caketquasanxuat' , 'datas': data}
    
#         self.import_centir()
#         self.import_payment()
        #self.payment_post()
        #self.remove_entries_inv_post()
        #self.remove_entries()
        
    
    def update_product(self):
        sql ='''
            select id from res_partner where phone like ('0500%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.phone = string.replace(partner.phone, '0500', '0262')
        
        sql ='''
            select id from res_partner where phone like ('059%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.phone = string.replace(partner.phone, '059', '0269')
        
        sql ='''
            select id from res_partner where fax like ('0500%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.fax= string.replace(partner.fax, '0500', '0262')
        
        sql ='''
            select id from res_partner where fax like ('059%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.fax = string.replace(partner.fax, '059', '0269')
        sql ='''
            select id from res_partner where mobile like ('0500%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.mobile= string.replace(partner.mobile, '0500', '0262')
        
        sql ='''
            select id from res_partner where fax like ('059%') and active =true
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            partner = self.env['res.partner'].browse(i['id'])
            partner.mobile = string.replace(partner.mobile, '059', '0269')
        
        
        
                
#         for this in self:
#             sql ='''
#                     select id from stock_picking where production_id= 4021 and state='cancel' and picking_type_id = 7
#                 '''
#                 
#             self.env.cr.execute(sql)
#             for i in self.env.cr.dictfetchall():
#                 it =self.env['stock.picking'].browse(i['id'])
#                 sql = '''
#                     Update stock_picking set state = 'done' where id = %s;
#                     update stock_move set state = 'done' where picking_id = %s;
#                 '''%(it.id,it.id)
#                 self.env.cr.execute(sql)
#                 for move in it.move_lines:
#                     move.stack_id._get_remaining_qty()
                    
#             try:
#                 recordlist = base64.decodestring(this.file)
#                 excel = xlrd.open_workbook(file_contents = recordlist)
#                 sh = excel.sheet_by_index(0)
#             except Exception, e:
#                 raise UserError(('Please select File'))
#             if sh:
#                 for row in range(sh.nrows):
#                     row_values = sh.row_values(row)
#                     default_code = row_values[0]
#                     product = self.env['product.product'].search([('default_code', '=', default_code)]) or False
#                     if not product:
#                         print default_code
#                         continue
#                     
#                     product.mc = row_values[1] or False
#                     product.fm = row_values[2] or False
#                     product.bb = row_values[3] or False
#                     product.black = row_values[4] or False
#                     product.broken = row_values[5] or False
#                     product.brown = row_values[6] or False
#                     product.eaten = row_values[7] or False
#                     product.immature = row_values[8] or False
#                     product.cherry = row_values[9] or False
#                     product.burned = row_values[10] or False
#                     product.mold = row_values[11] or False
#                     product.sc18 = row_values[12] or False
#                     product.sc16 = row_values[13] or False
#                     product.sc13 = row_values[14] or False
#                     product.sc12 = row_values[15] or False
#                     product.uscr12 = row_values[16] or False
#                     product.defects = row_values[17] or False
#                     product.triage = row_values[18] or False
#                     product.cup_taste = row_values[19] or False
                    
    
    def grn_dienchinh(self):
#         sql ='''
#             SELECT id from stock_picking where picking_type_id = 110
#         '''
#         self.env.cr.execute(sql)
#         for k in self.env.cr.dictfetchall():
#             grn_pick = self.env['stock.picking'].browse(k['id'])
#             grn_pick.stack_id._get_remaining_qty()
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                for row in range(sh.nrows):
                    row_values = sh.row_values(row)
                    origin = row_values[0] + '-'+ row_values[1]
                     
                    exit = self.env['stock.picking'].search([('origin', '=', origin)]) or False
                    if exit:
                        continue
                    
                    date_done = time.strftime(DATETIME_FORMAT)
                    picking_type_id = self.env['stock.picking.type'].browse(110)
                    location_id = picking_type_id.default_location_src_id.id
                    location_dest_id = picking_type_id.default_location_dest_id.id
                    product_id = self.env['product.product'].search([('default_code', '=', row_values[4])]) or False
                    if not product_id:
                        print 'loi' + origin + '------'
                        continue
                    
                    if not row_values[7]:
                        print 'Khong thay stack',row_values[7]
                        continue
                    
                    stack_float = row_values[7]
                    
                    if isinstance(stack_float, float):
                        stack_float = float(stack_float)
                        stack_float = round(stack_float,0)
                        stack_float = int(stack_float)
                        stack_float = str(stack_float)
                    stack = self.env['stock.stack'].search([('name', '=', stack_float),('init_qty','=',row_values[10])]) or False
                    if not stack:
                        print 'Lổi Stack ',origin 
                        continue
                    
                    picking_val = {
                        'date_done':date_done,
                        'name':'/' or False,
                        'origin':origin,
                        'picking_type_id': picking_type_id.id,
                        'date': date_done,
                        'location_dest_id': location_dest_id,
                        'location_id': location_id,
                        'state':'draft',
                    }
                    picking_id = self.env['stock.picking'].create(picking_val)
                    packing = self.env['ned.packing'].search([('name', '=', row_values[8])]) or False
                    NetWeight = BasicWeight = row_values[10]
                    move_val = {
                        'picking_id': picking_id.id, 
                        'name': product_id.name or '',
                        'product_id': product_id.id,
                        'product_uom': 3, 
                        'init_qty':NetWeight or 0.0,
                        'product_uom_qty': BasicWeight or 0.0, 
                        'price_unit': 0.0,
                        'picking_type_id': picking_type_id.id, 
                        'location_id': location_id, 
                        'location_dest_id': location_dest_id or False, 
                        'date': date_done, 
                        'type': 'incoming' or False, 
                        'zone_id':stack.zone_id.id,
                        'stack_id':stack.id,
                        'packing_id':packing and packing.id or False,
                        'company_id': 1, 
                        'state':'done', 'scrapped': False,
                        'warehouse_id': 1}
                     
                    picking_id = self.env['stock.move'].create(move_val)
        
    def update_itr(self):
        sql ='''
            SELECT id from stock_picking 
                where picking_type_id in (123)
                and state ='done'
        '''
        self.env.cr.execute(sql)
        for k in self.env.cr.dictfetchall():
            for grn_pick in self.env['stock.picking'].browse(k['id']):
                
                grn_pick.to_picking_type_id = grn_pick.picking_type_id.transfer_picking_type_id.id
                chuoi =  grn_pick.name + '%' 
                sql ='''
                    SELECT id from stock_picking where origin like '%s' and picking_type_id in (%s)
                '''%(chuoi,grn_pick.picking_type_id.transfer_picking_type_id.id)
                
                self.env.cr.execute(sql)
                for i in self.env.cr.dictfetchall():
                    it =self.env['stock.picking'].browse(i['id'])
                    it.backorder_id = k['id']
                
                allocation = self.env['lot.stack.allocation'].search([('gdn_id','=',grn_pick.id)], limit = 1)
                if allocation:
                    manager = allocation.lot_id
                    line = it.kcs_line[0]
                    line.mc = manager.mc
                    line.fm = manager.fm
                    line.black = manager.black
                    line.broken = manager.broken or 0.0
                    line.brown = manager.brown or 0.0
                    line.mold = manager.mold or 0.0
                    line.cherry = manager.cherry or 0.0
                    line.excelsa = manager.excelsa or 0.0
                    line.screen18 = manager.screen18 or 0.0
                    line.screen16 = manager.screen16 or 0.0
                    line.screen13 = manager.screen13 or 0.0
                    line.Belowsc12 = manager.screen12 or 0.0
                      
                    line.burned = manager.burn or 0.0
                    line.eaten = manager.eaten or 0.0
                    line.immature = manager.immature or 0.0
                    line.stick_count = manager.stick
                    line.stone_count = manager.stone
                    line.maize = manager.maize
                    
#                 sql ='''
#                     SELECT picking_id from transfer_internal_res 
#                         where transfer_id = %s
#                 '''%(grn_pick.id)
#                 self.env.cr.execute(sql)
#                 for i in self.env.cr.dictfetchall():
#                     itn_pick =self.env['stock.picking'].browse(i['picking_id'])
#                     itn_pick.backorder_id = grn_pick.id
#                     sql='''
#                         SELECT picking_id from transfer_internal_res 
#                             where transfer_id = %s
#                     '''%(i['picking_id'])
#                     self.env.cr.execute(sql)
#                     for j in self.env.cr.dictfetchall():
#                         itr_pick =self.env['stock.picking'].browse(j['picking_id'])
#                         itr_pick.backorder_id = grn_pick.id
                
    def update_mrp(self):
        mrp = self.env['mrp.production'].browse(3984) #3984 3975
        for move in mrp.move_lines2:
            move.state= 'draft'
            move.unlink()
        mrp.state ='in_production'
    
    def compute_taxes(self):
        
        invoce = self.env['account.invoice'].search([('type','=','out_invoice')])
        for inv in invoce:
            inv.compute_taxes()
        
    
    def import_centir(self):
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                for row in range(sh.nrows):
                    row_values = sh.row_values(row)
                    
                    if not row_values[0] or not row_values[1]:
                        continue
                    contract = self.env['purchase.contract'].search([('name', '=', row_values[0])]) or False
                    if not contract:
                        print row_values[0]
                        continue
                    ces = self.env['ned.certificate'].search([('code', '=', row_values[1])]) or False
                    if not ces:
                        print row_values[1]
                        continue
                    contract.certificate_id = ces.id
                    
    
    def import__masterpartner(self):
        count =0
        distirct = False
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                partner_code = False
                for row in range(sh.nrows):
                    row_values = sh.row_values(row)
                    
                    if not row_values[0] and not row_values[2]:
                        continue
                    
                    ## update district
#                     district = self.env['res.district'].search([('name', '=', row_values[2])],limit =1) or False
#                     partner =  self.env['res.partner'].search([('partner_code', '=', row_values[0])],limit =1) or False
#                     if not district:
#                         print row_values[2]
#                         continue
#                     if not partner:
#                         print row_values[0]
#                         continue
#                     partner.district_id = district.id
                    
                    partner_code = row_values[0] or False
                    if not partner_code:
                        continue
                    partner = self.env['res.partner'].search([('partner_code', '=', partner_code)]) or False
                    if not partner:
#                         print partner_code
                        continue
                     
#                     partner.district_id =  district and district.id or False
#                     
                    val ={
                          'goods':row_values[2],
                          'repperson1':row_values[4],
                          'repperson2':row_values[5],
                          'partnert_id':partner.id,
                          'estimated_annual_volume':row_values[7],
                          'purchase_undelivered_limit':row_values[17],
                          'negative_m2m_loss_limit':row_values[18],
                          'property_evaluation':row_values[19],
                          'delivery_at':row_values[3],
                          'ppkg':row_values[8],
                          'date':time.strftime(DATE_FORMAT)
                    }
                     
                    self.env['supplier.mgt'].create(val)
                    count +=1
                    print count

    def remove_ens(self):
        
#         stack = self.env['stock.stack'].search([])
#         for line in stack:
#             if line.move_ids:
#                 line._compute_qc()
        
        for inv in self.env['account.invoice'].browse([337,338]):
            inv.create_stock_move()
        
        
        
        
        
#         sql ='''
#             select aml.move_id,sm.entries_id, aml.debit , sm.price_unit * sm.product_qty
#             from account_move_line aml join  stock_move sm on aml.move_id = sm.entries_id
#             where aml.date between  '2016-12-01' and '2016-12-31' and account_id = 1534 and aml.partner_id is not null
#         '''
#         self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             price_unit = self.env.user.company_id.second_currency_id.with_context(date=i['date']).compute(i['price_currency'], 
#                                                                                      self.env.user.company_id.currency_id,
#                                                                                      round=False)
#             sql ='''
#                 update stock_move set price_unit = %s where id = %s
#             ''' %(price_unit,i['id'])
#             self.env.cr.execute(sql)
        
        
#         payment = self.env['account.payment'].search([('state','=','posted'),('move_line_ids','=',False),('payment_date','>','2016-10-01')])
#         for line in payment:
#             print line.name
        
#         location_id = self.env['stock.location'].search([('code','=','NVP - BMT')])
#         location_dest_id = self.env['stock.location'].search([('code','=','HCM')]) 
#         
#         outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
#                                                       ('state','=','done'),('location_dest_id','=',location_dest_id.id)], order ="date")
#         
#         for out in outgoing_ids:
#             out.compute_fifo()
#         
#         location_id = self.env['stock.location'].search([('code','=','HCM')])
#         location_dest_id = self.env['stock.location'].search([('usage','=','customer')]) 
#         
#         
#         outgoing_ids = self.env['stock.move'].search([('location_id','=',location_id.id),
#                                                       ('state','=','done'),('location_dest_id','=',location_dest_id.id)], order ="date")
#         
#         for out in outgoing_ids:
#             out.compute_fifo()
    
    def get_datetime(self, date):
        if not date:
            date = time.strftime(DATETIME_FORMAT)
        date = datetime.strptime(date, DATETIME_FORMAT)
        return date.strftime('%Y-%m-%d')
    def update_entr(self):
        sql ='''
            select  id  from stock_picking where id in (
            select gdn_id from lot_stack_allocation where stack_id in (
            select id from stock_stack where warehouse_id = 7)) and picking_type_id =2
        '''
        
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            pick = self.env['stock.picking'].browse(i['id'])
            picking_type = self.env['stock.picking.type'].browse(143)
            pick.picking_type_id = picking_type.id
            pick.location_id = picking_type.default_location_src_id.id
            pick.location_dest_id = picking_type.default_location_dest_id.id
            
            
            pick.name = picking_type.sequence_id.with_context(ir_sequence_date=self.get_datetime(pick.min_date)).next_by_id()
            
            for move in pick.move_lines:
                move.location_id = picking_type.default_location_src_id.id
                move.location_dest_id = picking_type.default_location_dest_id.id
            
                    
    def update_movesa(self):
         
#         company = self.env['res.company'].browse(1)
#         currency_id = company.currency_id
#         second_currency = company.second_currency_id
#         sql ='''
#             SELECT id, warehouse_id
#                 FROM stock_picking_type
#         '''
#         self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             sql ='''
#                 Update stock_picking set  warehouse_id = %s
#                 WHERE picking_type_id = %s;
#                 
#                 Update stock_move set warehouse_id = %s
#                 WHERE picking_id in (select id from stock_picking WHERE picking_type_id = %s);
#                 
#                 Update account_move set warehouse_id = %s
#                 WHERE id in (SELECT entries_id FROM stock_move where picking_type_id = %s and entries_id is null);
#                 
#                 Update account_move_line set warehouse_id = %s
#                 WHERE move_id in (SELECT entries_id FROM stock_move where picking_type_id = %s and entries_id is null);
#                 
#             '''%(i['warehouse_id'],i['id'],i['warehouse_id'],i['id'],i['warehouse_id'],i['id'],i['warehouse_id'],i['id'])
#             self.env.cr.execute(sql)

            
            sql ='''
                select id from stock_move where date between '2017-03-01' and '2017-04-01' and picking_id is not null
                and location_id = 93 and location_dest_id = 12
                   
            '''
            self.env.cr.execute(sql)
            for i in self.env.cr.dictfetchall():
                move = self.env['stock.move'].browse(i['id'])
                move.warehouse_id = move.picking_id.picking_type_id.warehouse_id.id
                move.picking_id.warehouse_id = move.picking_id.picking_type_id.warehouse_id.id
#                 sql = '''
#                     update account_move set debit = %s where move_id = %s and debit != 0;
#                     update account_move set credit = %s where move_id = %s and credit != 0;
#                 '''%(move.price_uint * move.product_uom_qty ,i['id'],move.price_uint * move.product_uom_qty ,i['id'])
#                 self.env.cr.execute(sql)
#         for i in self.env.cr.dictfetchall():
#             price_unit = self.env.user.company_id.second_currency_id.with_context(date=i['date']).compute(i['price_currency'], 
#                                                                                                  self.env.user.company_id.currency_id,
#                                                                                                      round=False)
#             line ='''
#                 Update stock_move
#                     set price_unit = %s 
#                     where id = %s
#             '''%(price_unit,i['id'])
#             self.env.cr.execute(line)
            
            
#         invoice = self.env['account.invoice'].search([('stock_move_id','!=',False)])
#         for inv in invoice:
#             sql='''
#                 update stock_move set origin = '%s' , partner_id = %s
#                 where id = %s
#             '''%(inv.reference,inv.partner_id.id,inv.stock_move_id.id)
#             self.env.cr.execute(sql)
#              
#             if not inv.stock_move_id.entries_id:
#                 continue
#              
#             sql ='''
#                 Update account_move set partner_id = %s , ref = '%s' where id = %s
#             '''%(inv.partner_id.id,inv.reference,inv.stock_move_id.entries_id.id)
#             self.env.cr.execute(sql)
#              
#             sql ='''
#                 Update account_move_line set partner_id = %s , name = '%s' where move_id = %s
#             '''%(inv.partner_id.id,inv.reference,inv.stock_move_id.entries_id.id)
#             self.env.cr.execute(sql)
            
    
    def update_partner_account(self):
        res =[]
        sql ='''
            select id from res_partner
        '''
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            res.append(i['id'])
        for partner in self.env['res.partner'].browse(res):
            if not partner.partner_code:
                continue
            if 'SU' in partner.partner_code:
                partner.property_account_payable_id =1621
                partner.property_account_receivable_id =1509
                partner.property_vendor_advance_acc_id =1621
                partner.property_customer_advance_acc_id =1509
            elif 'NED' in partner.partner_code:
                partner.property_account_payable_id =1621
                partner.property_account_receivable_id =1509
                partner.property_vendor_advance_acc_id =1621
                partner.property_customer_advance_acc_id =1509
            else:
                partner.property_account_payable_id =1622
                partner.property_account_receivable_id =1514
                partner.property_vendor_advance_acc_id =1623
                partner.property_customer_advance_acc_id =1512
                
                
                
                
    def import_partner(self):
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(1)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                vals ={}
                partner_code = False
                for row in range(sh.nrows):
                    try:
                        row_values = sh.row_values(row)
                        
                        if row_values[0]:
                            partner_code = row_values[0] or False
#                         name = row_values[1] or False
#                         vat = row_values[3] or False
#                         street = row_values[4] or False
                        acc_number = row_values[2] or False
                        bank_name = row_values[3] or False
                        bic = row_values[4] or False
                        if not acc_number:
                            continue
                        partner = self.env['res.partner'].search([('partner_code', '=', partner_code)]) or False
                        if not partner:
#                             print partner_code
                            continue
#                         vals ={
#                                'partner_code':partner_code,
#                                 'name': name or False, 
#                                 'supplier': True, 
#                                 'customer': True, 
#                                 'street':street,
#                                 'vat':vat,
#                                 'company_type': 'company', 
#                                 'active': True,
#                                 'property_account_payable_id':1621,
#                                 'property_account_receivable_id':1509,
#                                 'property_vendor_advance_acc_id':1621,
#                                 'property_customer_advance_acc_id':1509}
#                         new_id = self.env['res.partner'].create(vals)
                        res_bank_id = self.env['res.partner.bank'].search([('acc_number','=',acc_number)])
                        if res_bank_id:
                            continue
                        bank_id = self.env['res.bank'].search([('name','=',bank_name),('bic','=',bic)], limit =1)
                        if not bank_id:
                            bank_id = self.env['res.bank'].create({'name':bank_name,'bic':bic})
                         
                        val = {
                               'acc_number':acc_number,
                               'partner_id':partner.id,
                               'bank_id':bank_id.id
                               }
                        self.env['res.partner.bank'].create(val)
                
                    except Exception, e:
                        print '-------------'+ str(partner_code) + '----------------'
        print 'Done'
    
    @api.multi
    def report_summary_production(self):
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = 'wizard.import.production.result'
        data['form'] = self.read([])[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'report_summary_production' , 'datas': data}
    
    @api.multi
    def import_filessss(self):
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
                move_id = self.env['account.move'].browse(9880)
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                for row in range(sh.nrows):
                    try:
                        row_values = sh.row_values(row)
                        debit = credit =0
                        code1 = row_values[0] or False
                        code2 = row_values[1] or False
                        code3 = row_values[2] or False
                        debit = row_values[5] or False
                        credit = row_values[6] or False
                        loi = False
                        if not debit and not credit:
                            continue
                        if code1:
                            account = self.env['account.account'].search([('code', '=', int(code1))]) or False
                            loi = code1
                        elif code2:
                            account = self.env['account.account'].search([('code', '=', int(code2))]) or False
                            loi = code2
                        elif code3:
                            account = self.env['account.account'].search([('code', '=', int(code3))]) or False
                            loi = code3
                        else:
                            continue
                        if account.type == 'view':
                            continue
                        if debit:
                            acc_debit = account.id
                            acc_creidt = 1902
                            credit = debit 
                        else:
                            acc_creidt = account.id
                            acc_debit = 1902 
                            debit = credit
                            
                        debit_line_vals = {
                            'name': account.code,
                            'quantity': 1,
                            'debit': debit or 0.0,
                            'credit':  0.0,
                            #'second_ex_rate':second_ex_rate or 0.0,
                            #'amount_currency':amount_currency,
                            'account_id': acc_debit,
                            #'currency_id': line.second_currency_id.id
                        }
                        credit_line_vals = {
                            'name': account.code,
                            'quantity': 1,
                            'debit': 0.0,  
                            'credit': credit or 0.0,
                            #'second_ex_rate':second_ex_rate or 0.0,
                            #'amount_currency': (-1) * amount_currency,
                            'account_id': acc_creidt,
                            #'currency_id': line.second_currency_id.id
                        }
                        
                        move_id.write({'line_ids': [(0, 0, debit_line_vals), (0, 0, credit_line_vals)]})
                    
                
                    except Exception, e:
                        print '-------------'+ str(loi) + '----------------'
        move_id.post()
        print 'Done'
                      
    @api.multi
    def import_file(self):
        flag = flag_finish = False
#         supplierinfo = self.env['product.supplierinfo']
#         pricelist_ids = []
#         success = failure = 0
#         warning = False
        mrp_pro_temp = []
        for this in self:
            try:
                recordlist = base64.decodestring(this.file)
                excel = xlrd.open_workbook(file_contents = recordlist)
                sh = excel.sheet_by_index(0)
                  
            except Exception, e:
                raise UserError(('Please select File'))
            if sh:
                empl_ids = []
                finish_ids = {}
                for row in range(sh.nrows):
                    if sh.cell(row,0).value == 'CODE':
                        flag = True
                        continue
                    if flag:
                        emp_obj = self.env['hr.employee'].search([('code','=', sh.cell(row,0).value)])
                        if emp_obj:
                            empl_ids.append({'emp_id': emp_obj.id,
                                             'job_id': emp_obj.job_id.id or False,
                                             'department_id': emp_obj.department_id.id or False,
                                             'hour_nbr': sh.cell(row,5).value,
                                             'ot_hour': sh.cell(row,6).value
                                            })
                        else:
#                             raise UserError(_("Employee %s do not exist")%sh.cell(row,0).value)
                            flag = False
                      
                    if sh.cell(row,0).value == u'BT Code Mẻ Sản Xuất':
                        flag_finish = True
                        continue
                    if flag_finish:
                        product_code = sh.cell(row,2).value
                        packing = sh.cell(row,6).value
                        pending_grp = sh.cell(row,1).value
                        packing = packing.strip()
                        production_name = sh.cell(row,0).value
                        production_name = production_name.strip()
                        product_obj = self.env['product.product'].search([('default_code','=', product_code.strip())])
                        zone = self.env['stock.zone'].search([('name','=', sh.cell(row,5).value)])
                        packing = self.env['ned.packing'].search([('name','=', packing)])
                        contract_no = self.env['shipping.instruction'].search([('name','=', sh.cell(row,8).value)])
                        production_id = self.env['mrp.production'].search([('name','=', production_name)])
                        qty_bag = sh.cell(row,7).value
                        lot = sh.cell(row,9).value or False
                        if product_obj:
                            if production_id.id in finish_ids:
                                finish_ids[production_id.id].append({'product_id': product_obj.id,
                                                                     'zone_id': zone.id,
                                                                     'packing_id': packing.id,
                                                                     'qty_bags': qty_bag,
                                                                     'product_uom': product_obj.uom_id.id,
                                                                     'product_qty': sh.cell(row,4).value,
                                                                     'si_id': contract_no.id,
                                                                     'notes':lot,
                                                                     'pending_grn':pending_grp
                                                                    })
                            else:
                                finish_ids[production_id.id] = []
                                finish_ids[production_id.id].append({'product_id': product_obj.id,
                                                                     'zone_id': zone.id,
                                                                     'packing_id': packing.id,
                                                                     'qty_bags': qty_bag,
                                                                     'product_uom': product_obj.uom_id.id,
                                                                     'product_qty': sh.cell(row,4).value,
                                                                     'si_id': contract_no.id,
                                                                     'notes':lot,
                                                                     'pending_grn':pending_grp
                                                                    })
                        else:
#                             raise UserError(_("Product %s do not exist")%(product_code))
                            flag_finish = False
                      
                temp = []
                for row in range(sh.nrows):
                    mrp_pro_obj = self.env['mrp.production'].search([('name','=', sh.cell(row,0).value)])
                    for workcenter_line in mrp_pro_obj.workcenter_lines:
                        if mrp_pro_obj.id in mrp_pro_temp:
                            continue
                        else:
                            mrp_pro_temp.append(mrp_pro_obj.id)
                        list =  ['message_follower_ids', 'create_date', 'resource_id', 'write_uid', 'create_uid', 
                                 'direct_labour', 'message_ids', 'note', 'state', 'start_date', 'produced_products', 'end_date', 'hours', 
                                 'write_date', 'calendar_id', 'name', 'consumed_products', 'operation_id'
                                ]
                        vals = self.env['mrp.operation.result'].default_get(list)
                        vals['operation_id'] = workcenter_line.id
                        vals['resource_id'] = workcenter_line.workcenter_id.id
                        vals['end_date'] = vals['start_date']
                        vals['production_shift']= self.production_shift
                        result_id = self.env['mrp.operation.result'].create(vals)
                        temp.append(result_id.id)
                          
                        for i in empl_ids:
                            i.update({'result_id': result_id.id})
                            self.env['direct.labour'].create(i)
                              
                        production_id = self.env['mrp.production'].search([('name','=', sh.cell(row,0).value)])
                        for i in finish_ids[production_id.id]:
                            i.update({'operation_result_id': result_id.id})
                            self.env['mrp.operation.result.produced.product'].create(i)
          
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('general_mrp_operations.action_mrp_operation_result')
        list_view_id = imd.xmlid_to_res_id('general_mrp_operations.view_mrp_operation_result_tree')
        form_view_id = imd.xmlid_to_res_id('general_mrp_operations.view_mrp_operation_result_form')
  
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form'], [False, 'graph'], [False, 'kanban'], [False, 'calendar'], [False, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }
        if len(temp) > 1:
            result['domain'] = "[('id','in',%s)]" % temp
        elif len(temp) == 1:
            result['views'] = [(form_view_id, 'form')]
            result['res_id'] = temp[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
                            
class wizard_stock_picking(models.TransientModel):
    _name = "wizard.stock.picking"
    
    def create_pick_scale(self,active_id):
        for this in self:
            result_obj = self.env['request.materials.line'].browse(active_id)
#             if this.state =='cancel':
#                 raise UserError(u'Request Have been Canceled')
            if this.product_qty > result_obj.product_qty -result_obj.basis_qty:
                raise UserError(u'Request Qty is over')
            result_obj = self.env['request.materials.line'].browse(active_id)
            company = self.env.user.company_id.id or False
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            var = {
                   'name': '/', 
                   'picking_type_id': self.picking_type_id.id, 
                   'min_date': self.date or False, 
                   'date_done':self.date, 
                   'partner_id': False, 
                   'picking_type_code': self.picking_type_id.code or False,
                   'location_id': self.location_id.id or False, 
                   'production_id': self.production_id.id or False, 
                   'location_dest_id': self.location_dest_id.id or False,
                   'request_materials_id':this.request_materials_id.id,
                   'state':'draft',
               }  
            
            new_id = self.env['stock.picking'].create(var)
            product_uom_qty =0.0
            if this.stack_id:
                product_uom_qty = round(this.product_qty - (this.product_qty * abs(this.stack_id.avg_deduction/100)),0)
            else:
                product_uom_qty = this.product_qty
                
            name = '[' + this.product_id.default_code + '] ' + this.product_id.name or '' 
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': this.product_id.uom_id.id or False,
                'product_uom_qty': product_uom_qty or 0.0, 
                'init_qty': this.product_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': self.picking_type_id.id or False,
                'location_id': self.location_id.id or False,
                'date_expected': self.date or False, 'partner_id': False,
                'location_dest_id': self.location_dest_id.id or False,
                'type': self.picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': this.stack_id.zone_id.id or False, 
                'product_id': this.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'state':'draft', 
                'warehouse_id': warehouse_id.id or False,
                'stack_id':this.stack_id.id,
                })
            result_obj.write({'picking_ids': [(4, new_id.id)]})
            #new_id.action_done()

            
        return True
    
    date = fields.Date(string="Scheduled Date")
    production_id = fields.Many2one("mrp.production", "Production")
    picking_type_id = fields.Many2one("stock.picking.type", "Picking Type")
    location_id = fields.Many2one("stock.location", "Source Location Zone")
    location_dest_id = fields.Many2one("stock.location", "Destination Location Zone")
    move_lines = fields.One2many("wizard.stock.move", "wizard_id", "Move Lines")
    product_id = fields.Many2one("product.product", "Product")
    product_qty = fields.Float(string="Product Qty",digits=(12, 0))
    basis_qty = fields.Float(string="basis_qty",digits=(12, 0))
    stack_id = fields.Many2one("stock.stack", "Stack")
    request_materials_id = fields.Many2one("request.materials", "Request Materials")
    
    @api.model
    def default_get(self, fields):
        res = {}
        active_ids = self._context.get('active_ids')
        if active_ids:
            warehouse_id = self.env['stock.warehouse'].search([('name', '=', 'Factory - BMT')], limit=1)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id.id)
            picking_type_id = warehouse.production_out_type_id.id or False
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            for active in active_ids:
                result_obj = self.env['request.materials.line'].browse(active)
                if result_obj.request_id.type == '':
                    picking_type_id = warehouse.production_out_type_id.id or False
                    picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                else:
                    picking_type_id = warehouse.production_out_type_consu_id.id or False
                    picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                if result_obj.state =='cancel':
                    raise UserError(u'Request Have been Canceled')
                
                res = {
                    'picking_type_id': picking_type_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    'production_id': result_obj.request_id.production_id.id or False,
                    'location_id': picking_type.default_location_src_id.id or False, 
                    'product_qty':result_obj.product_qty -result_obj.basis_qty,
                    'basis_qty':result_obj.basis_qty,
                    'product_id':result_obj.product_id.id,
                    'stack_id':result_obj.stack_id.id,
                    'request_materials_id':result_obj.request_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id or False
                    }
                 
        return res
    
    @api.multi
    def button_create_picking(self):
        for this in self:
            active_id = self._context.get('active_ids')
            result_obj = self.env['request.materials.line'].browse(active_id)
#             if this.state =='cancel':
#                 raise UserError(u'Request Have been Canceled')
            if this.product_qty > result_obj.product_qty -result_obj.basis_qty:
                raise UserError(u'Request Qty is over')
            result_obj = self.env['request.materials.line'].browse(active_id)
            company = self.env.user.company_id.id or False
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            var = {
                   'name': '/', 
                   'picking_type_id': self.picking_type_id.id, 
                   'min_date': self.date or False, 
                   'date_done':self.date, 
                   'partner_id': False, 
                   'picking_type_code': self.picking_type_id.code or False,
                   'location_id': self.location_id.id or False, 
                   'production_id': self.production_id.id or False, 
                   'location_dest_id': self.location_dest_id.id or False,
                   'request_materials_id':this.request_materials_id.id,
                   'state':'draft',
               }  
            
            new_id = self.env['stock.picking'].create(var)
            product_uom_qty =0.0
            if this.stack_id.avg_deduction < 0:
                product_uom_qty = this.product_qty - (this.product_qty * abs(this.stack_id.avg_deduction/100))
            else:
                product_uom_qty = this.product_qty - (this.product_qty * abs(this.stack_id.avg_deduction/100))
                
            name = '[' + this.product_id.default_code + '] ' + this.product_id.name or '' 
            move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                'name': name, 
                'product_uom': this.product_id.uom_id.id or False,
                'product_uom_qty': product_uom_qty or 0.0, 
                'init_qty': this.product_qty or 0.0, 
                'price_unit': 0.0,
                'picking_type_id': self.picking_type_id.id or False,
                'location_id': self.location_id.id or False,
                'date_expected': self.date or False, 'partner_id': False,
                'location_dest_id': self.location_dest_id.id or False,
                'type': self.picking_type_id.code or False, 'scrapped': False, 
                'company_id': company, 
                'zone_id': this.stack_id.zone_id.id or False, 
                'product_id': this.product_id.id or False,
                'date': self.date or False, 'currency_id': False,
                'state':'draft', 
                'warehouse_id': warehouse_id.id or False,
                'stack_id':this.stack_id.id,
                'production_id': self.production_id.id or False,                
                })
            result_obj.write({'picking_ids': [(4, new_id.id)]})
            self.production_id.move_lines = [(4, move_id.id)]
            new_id.action_done()
            result_obj = self.env['request.materials.line'].browse(active_id)
            if result_obj.product_qty == result_obj.basis_qty:
                result_obj.request_id.state = 'done'
            
        return True

class wizard_stock_move(models.TransientModel):
    _name = "wizard.stock.move"
    
    wizard_id = fields.Many2one('wizard.stock.picking', 'Wizard Stock Picking', ondelete='cascade')
    result_id = fields.Many2one("mrp.operation.result", "Result")
    product_id = fields.Many2one("product.product", "Product")
    product_qty = fields.Float("Qty")
    product_uom = fields.Many2one("product.uom","UoM")

class wizard_request_materials(models.TransientModel):
    _inherit = "wizard.request.materials"
    
    @api.model
    def default_get(self, fields):
        res = {}
        vars=[]
        active_id = self._context.get('active_id')
        if active_id:
            production_obj = self.env['mrp.production'].browse(active_id)
            res = {'production_id': active_id, 'request_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   'warehouse_id':production_obj.warehouse_id.id}
            for line in production_obj.product_lines:
                vars.append((0, 0, {'product_id':line.product_id.id, 'product_uom':line.product_uom.id,
                                    'product_qty' :line.product_qty}))
            res.update({'request_line':vars})
        return res
    
    @api.multi
    def button_request(self):
        for production in self:
            if not production.request_line:
                raise UserError(_("Materials is not Null"))
            for line in production.request_line:
                if line.product_qty == 0:
                    raise UserError(_("Request Qty is not Null"))
            val ={
                  'production_id':production.production_id.id,
                  'request_user_id':self.env.uid,
                  'state':'draft'
                }
            request_id = self.env['request.materials'].create(val)
            
            for line in production.request_line:
                vals ={
                    'product_id':line.product_id.id,
                    'product_uom':line.product_uom.id,
                    'product_qty':line.product_qty or 0.0,
                    'request_id':request_id.id,
                    'stack_id':line.stack_id.id
                    }
                self.env['request.materials.line'].create(vals)
            request_id.state = 'approved'

class wizard_request_materials_line(models.TransientModel):
    _inherit = "wizard.request.materials.line"
    
    @api.multi
    @api.onchange('stack_id')
    def onchange_stack_id(self):
        if not self.stack_id:
            self.update({'product_qty': 0.0})
        else:
            self.update({'product_qty': self.stack_id.init_qty or 0.0})
        
    stack_id = fields.Many2one('stock.stack',string ='Stack')
    

class RequestMaterialsLine(models.Model):
    _inherit = "request.materials.line"
    
    @api.multi
    def btt_cancel(self):
        self.state = 'cancel'
    
    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return {'domain': {'product_uom': []}}

        vals = {}
        domain = {'product_uom': [('category_id', '=', self.product_id.uom_id.category_id.id)]}

        vals['product_uom'] = self.product_id.uom_id

        self.update(vals)
        return {'domain': domain}
        
        
class RequestMaterials(models.Model):
    _inherit = "request.materials"
    
    def update_scale(self):
        for line in self.request_line:
            qty =0
            for this in self.scale_ids:     
                if this.state == 'approved':
                    continue    
                if line.stack_id.id == this.stack_id.id:
                    qty += this.product_qty
                    this.state ='approved'
                
            if qty !=0:
                warehouse_id = self.env['stock.warehouse'].search([('name', '=', 'Factory - BMT')], limit=1)
                warehouse = self.env['stock.warehouse'].browse(warehouse_id.id)
                
                result_obj = self.env['request.materials.line'].browse(line.id)
                if result_obj.request_id.type == 'consu':
                    picking_type_id = warehouse.production_out_type_consu_id.id or False
                else:
                    picking_type_id = warehouse.production_out_type_id.id or False
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                
                
                if result_obj.state =='cancel':
                    raise UserError(u'Request Have been Canceled')
                res = {
                    'picking_type_id': picking_type_id, 'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                   'production_id': result_obj.request_id.production_id.id or False,
                   'location_id': picking_type.default_location_src_id.id or False, 
                   'product_qty': qty,
                   'basis_qty':result_obj.basis_qty,
                   'product_id':result_obj.product_id.id,
                   'stack_id':result_obj.stack_id.id,
                   'request_materials_id':result_obj.request_id.id,
                   'location_dest_id': picking_type.default_location_dest_id.id or False}
                wizard_obj = self.env['wizard.stock.picking'].create(res)
                wizard_obj.create_pick_scale(line.id)
    
    @api.multi
    def write(self, vals):
            #kiet: goi ham
        if vals.get('state') == 'scale':
            self.update_scale()
            vals['state'] = 'approved'
            result = super(RequestMaterials, self).write(vals)
        else:
            result = super(RequestMaterials, self).write(vals)
        return result
    
    @api.multi
    def button_approve_consum(self):
        self.state = 'approved'
    
    @api.multi
    def button_done(self):
        for this in self:
            if not this.production_id:
                continue
            company = self.env.user.company_id.id
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id.id)
            picking_type_id = warehouse.production_out_type_id.id or False
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            for line in this.request_line:
                if line.state =='cancel':
                    continue
                if line.product_qty <= line.basis_qty:
                    continue
                var = {
                   'name': '/', 
                   'picking_type_id': picking_type_id, 
                   'min_date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False, 
                   'date_done':datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), 
                   'partner_id': False, 
                   'picking_type_code': picking_type.code or False,
                   'location_id': picking_type.default_location_src_id.id or False, 
                   'location_dest_id': picking_type.default_location_dest_id.id or False,
                   'production_id': this.production_id.id or False, 
                   'request_materials_id':this.id,
                   'state':'draft'
                       }  
                new_id = self.env['stock.picking'].create(var)
                name = '[' + line.product_id.default_code + '] ' + line.product_id.name or '' 
                
                net_qty = line.product_qty - line.basis_qty
                product_uom_qty =0.0
                if line.stack_id.avg_deduction < 0:
                    product_uom_qty = net_qty - (net_qty * abs(line.stack_id.avg_deduction/100))
                else:
                    product_uom_qty = net_qty - (net_qty * abs(line.stack_id.avg_deduction/100))
                    
                move_id = self.env['stock.move'].create({'picking_id': new_id.id or False, 
                    'name': name, 
                    'product_uom': line.product_id.uom_id.id or False,
                    'product_uom_qty': product_uom_qty or 0.0, 
                    'init_qty': line.product_qty - line.basis_qty or 0.0, 
                    'price_unit': 0.0,
                    'picking_type_id': picking_type.id or False,
                    'location_id': picking_type.default_location_src_id.id or False, 
                    'location_dest_id': picking_type.default_location_dest_id.id or False,
                    'date_expected': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False, 
                    'partner_id': False,
                    'type': picking_type.code or False, 
                    'scrapped': False, 
                    'company_id': company, 
                    'zone_id': line.stack_id.zone_id.id or False, 
                    'product_id': line.product_id.id or False,
                    'date': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) or False,
                    'currency_id': False,
                    'state':'draft', 
                    'warehouse_id': warehouse_id.id or False,
                    'stack_id':line.stack_id.id,
                    'production_id': this.production_id.id or False,
                    })
                line.write({'picking_ids': [(4, new_id.id)]})
                new_id.action_done()
            this.state = 'done'
            this.production_id.move_lines =[(4, move_id.id)]
        
        
    def _total_qty(self):
        for order in self:
            total_qty = 0.0
            basis_qty = 0.0
            
            for line in order.request_line:
                total_qty += line.product_qty
                basis_qty += line.basis_qty
            order.total_qty = total_qty
            order.basis_qty = basis_qty
            order.remain_qty = total_qty - basis_qty
            
    total_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Request Qty')
    basis_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Issue Qty')
    remain_qty = fields.Float(compute='_total_qty', digits=(16, 0) , string='Remain Pick')
    scale_ids = fields.One2many('request.materials.scale','request_id',string="Scale")
    state = fields.Selection([('draft', 'New'),('scale','Scale'), ('approved', 'Approved'), ('done', 'Done'),('cancel','Canceled')], string='Status',
                             readonly=True, copy=False, index=True, default='draft')
    