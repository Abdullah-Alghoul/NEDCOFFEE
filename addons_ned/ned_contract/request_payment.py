# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
DATE_FORMAT = "%Y-%m-%d"

class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Payments"
    
    request_payment_id = fields.Many2one('request.payment', string='Reason')
    

class InterestRate(models.Model): 
    _name = "interest.rate"
    
    month = fields.Selection([('1', 'Tháng 1'), ('2', 'Tháng 2'),  ('3', 'Tháng 3'),
                              ('4', 'Tháng 4'),  ('5', 'Tháng 5')], string='Months',
                             readonly=False, copy=False, index=True,)
    rate = fields.Float(string ="Rate %",digits=(12, 3))
    request_id = fields.Many2one('request.payment', string='Request payment')
    
    def _compute_provisional_rate(self,date=None):
        if not date:
            current_date = time.strftime(DATE_FORMAT)
        else:
            current_date =date
        for request in self:
            provisional_rate =0.0
            if request.request_id:
                for payment in request.request_id.request_payment_ids:
                    days = 0
                    allocation_amount =0.0
                    payment_date = payment.payment_date
                    sql ='''
                        SELECT sum(allocation_amount) allocation_amount
                        FROM payment_allocation
                        WHERE
                            pay_id =%s
                    '''%(payment.id)
                    self.env.cr.execute(sql)
                    for allocation in self.env.cr.dictfetchall():
                        allocation_amount = allocation['allocation_amount'] or 0.0
                    
                    
                    amount = (payment.amount - allocation_amount) /30
                    if request.month in ('1','2','3','4'):
                        if request.month == '1':
                            sql = '''
                            SELECT '%s'::Date - '%s'::Date as days
                        '''%(current_date , payment_date)
                        elif request.month == '2':
                            sql = '''
                                SELECT '%s'::Date - ('%s'::Date + 30) as days
                            '''%(current_date , payment_date)
                        elif request.month == '3':
                            sql = '''
                                SELECT '%s'::Date - ('%s'::Date + 60) as days
                            '''%(current_date , payment_date)
                        else:
                            sql = '''
                                SELECT '%s'::Date - ('%s'::Date + 90) as days
                            '''%(current_date , payment_date)
                             
                        self.env.cr.execute(sql)
                        for da in self.env.cr.dictfetchall():
                            days = da['days']
                         
                        if days>0 and days <=30:
                            amount = amount * days * request.rate/100
                        elif days >30:
                            amount = amount * 30 * request.rate/100
                        else:
                            amount = 0
                        
                        provisional_rate += amount
                    else:
                        sql = '''
                            SELECT '%s'::Date - ('%s'::Date + 120) as days
                        '''%(current_date, payment_date)
                        self.env.cr.execute(sql)
                        for da in self.env.cr.dictfetchall():
                            days = da['days']
                        
                        if days>0 :
                            amount = amount * days * request.rate/100
                        else:
                            amount = 0
                        provisional_rate += amount
                    
            request.provisional_rate =  provisional_rate       
    
    provisional_rate = fields.Float(string='Lãi tạm tính',compute='_compute_provisional_rate',digits=(12, 0))
    
class RequestPayment(models.Model):
    _name = "request.payment"
    _order = "id desc"
    
    
    
    @api.depends('invoice_ids')  
    def _compute_invoices(self):
        for contract in self:
            invoices = self.env['account.invoice']
            for line in contract.invoice_ids: 
                invoices = (line.filtered(lambda r: r.state != 'cancel'))
            contract.invoice_ids = invoices
            contract.invoice_count = len(invoices)
    
    @api.model
    def create(self, vals):
        result = super(RequestPayment, self).create(vals)
        return result
    
    @api.multi
    def btt_approved(self):
        self.state ='approved'
        
    @api.multi
    def btt_cancel(self):
        self.state ='request'
        
    @api.model
    def default_get(self, fields):
        res = {}
        val = []
        month =1
        partner_id = self._context.get('partner_id') or False
        type = self._context.get('type') or False
        while(month<6):
            val.append((0, 0, {
                 'month':str(month),
                 'rate':0.0
                 }))
            month +=1
        res.update({'users_request_id':self.env.uid,'rate_ids':val,'partner_id':partner_id,'type':type,'state':'request'})
        return res
    @api.depends('request_payment_ids','request_amount','advance_payment_quantity')
    def _compute_request_payment(self):
        for request in self:
            total_payment = 0.0
            for line in request.request_payment_ids:
                total_payment += line.amount
            request.total_payment = total_payment   
#             if not request.advance_price:
#                 request.advance_payment_quantity = 0.0
#             else:
#                 request.advance_payment_quantity = request.request_amount / request.advance_price
            
            if not request.advance_payment_quantity:
                request.advance_price = 0.0
            else:
                request.advance_price = request.request_amount / request.advance_payment_quantity
                
            request.total_remain = request.request_amount - total_payment
#             if request.total_remain == 0.0:
#                 if total_payment !=0:
#                     request.state ='paid'
    
    
    def _compute_provisional_amount(self):
        for line in self:
            amount =0.0
            for rate in line.rate_ids:
                amount  += rate.provisional_rate or 0.0
            line.provisional_amount = amount
    
    def _compute_refunded(self):
        for line in self:
            if line.purchase_contract_id.type =='consign':
                payment_refunded = open_advance = 0.0
                for payment in line.request_payment_ids:
                    payment_refunded  += payment.payment_refunded or 0.0
                    open_advance  += payment.open_advance or 0.0
                line.payment_refunded = payment_refunded or 0.0
                line.open_advance = open_advance or 0.0
            else:
                line.payment_refunded =  0.0
                line.open_advance =  0.0
    
    @api.depends('request_payment_ids')
    def _compute_payment(self):
        for request in self:
            orders =False
            for line in request.request_payment_ids: 
                orders = line.filtered(lambda r: r.state != 'draft')
            if not orders:
                request.payment_count = 0
            else:
                request.payment_count = len(orders)
    
    @api.multi
    def action_view_payment(self):
        action = self.env.ref('account.action_account_payments_payable')
        result = action.read()[0]
        
        #override the context to get rid of the default filtering
        result['context'] = {'partner_type': 'supplier'}

        result['domain'] = "[('id', 'in', " + str(self.request_payment_ids.ids) + ")]"
        res = self.env.ref('account.view_account_supplier_payment_tree', False)
        result['views'] = [(res and res.id or False, 'tree')]
        result['res_id'] = self.request_payment_ids.id
        return result
    
    payment_count = fields.Integer(compute='_compute_payment', string='Receptions', default=0)
    name = fields.Char(string= 'Reason', required=True)
    date = fields.Date('Request Date', default=fields.Datetime.now)
    partner_id = fields.Many2one('res.partner', string='Partner')
    request_amount = fields.Float(string = 'Request Amount',digits=(12, 0))
    chinhanh = fields.Char(string= 'Chi Nhánh', required=True)
    songay = fields.Integer(string='Số ngày',digits=(12, 0))
    advance_price = fields.Float(string='Advance Price',digits=(12, 0),compute='_compute_request_payment')
    advance_payment_quantity = fields.Float(string='Advance payment quantity',digits=(12, 0))
    company_id = fields.Many2one('res.company', string='Company', required=False,
              default=lambda self: self.env['res.company']._company_default_get('request.payment'))
    purchase_contract_id = fields.Many2one('purchase.contract', 'Purchase contract', required=False)
    request_payment_ids = fields.One2many('account.payment','request_payment_id', string='Payment', copy=False)
    total_payment = fields.Float(string='Total Payment', store=True, readonly=False, compute='_compute_request_payment',digits=(12, 0))
    total_remain = fields.Float(string='Total Remain', store=True, readonly=False, compute='_compute_request_payment',digits=(12, 0))
    users_request_id = fields.Many2one('res.users', string='Users Request',default=lambda self: self._uid)
    state = fields.Selection([('request', 'Request'), ('approved', 'Approved'),('paid','Paid')],
                          string='State',readonly=False, copy=False, index=True,default='request')
    rate_ids = fields.One2many('interest.rate','request_id', string='Request payment')
    partner_bank_id = fields.Many2one('res.partner.bank',string= 'Partner bank', required=False)
    
    provisional_amount = fields.Float(string='Lãi tạm tính',compute='_compute_provisional_amount',digits=(12, 0))
    
    payment_refunded = fields.Float(string='Refunded',compute='_compute_refunded',digits=(12, 0))
    open_advance = fields.Float(string='Open Advance',compute='_compute_refunded',digits=(12, 0)) 
    type = fields.Selection(selection=[('consign', 'Consignment Agreement'), ('purchase', 'Purchase Contract')],
                            related='purchase_contract_id.type',  string='Type',store = True)
    
    amount_approved = fields.Float(string='Amount Approved', digits=(12, 0))
    
    bank_id = fields.Many2one('res.bank',related='partner_bank_id.bank_id',  string='Bank',store = False)


    @api.multi
    def print_payment_request(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'payment_npe_report'}
    
    @api.multi
    def print_advance_payment(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'advance_payment_report'}
    
    @api.multi
    def print_printout_payment_npv(self):
        return {'type': 'ir.actions.report.xml', 'report_name': 'printout_payment_npv_report'}
    

class PurchaseContract(models.Model):
    _inherit = "purchase.contract"
    
    request_payment_ids = fields.One2many('request.payment','purchase_contract_id', string='Request Payment')