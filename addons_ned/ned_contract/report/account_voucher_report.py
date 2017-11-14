# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from datetime import datetime
import time
from openerp.osv import osv
from openerp.report import report_sxw
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

from openerp import _
from openerp.exceptions import UserError


class Parser(report_sxw.rml_parse):
        
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context=context)
        
        self.journal_voucher_id = context.get('active_id',False)
        self.company_bank = []
        self.partner_bank = []
        self.code_cr = ''
        self.code_dr = ''
        self.localcontext.update({
            'get_vietnam_date':self.get_vietnam_date,
            
            'get_company_bank': self.get_company_bank,
            'get_partner_bank': self.get_partner_bank,
            'get_journal_currency': self.get_journal_currency,
            'get_format_amount': self.get_format_amount,
            'get_string_amount': self.get_string_amount,
            'get_account_lines': self.get_account_lines,
            'get_origin': self.get_origin,
            'bank_number': self.bank_number,
            'partner_bank_number': self.partner_bank_number,
            'get_format_ds':self.get_format_ds
        })
    
    def get_origin(self, o):
        origin = ''
        if o.source_document:
            return o.source_document
        
        if len(o.payment_lines):
            for line in o.payment_lines:
                origin += u'HĐ số ' + (line.number or '') + ', '
            if len(origin):
                origin = origin[:-2]
            return origin
        
        if len(o.invoice_ids):
            for line in o.invoice_ids:
                if line.state not in ['draft', 'cancel']:
                    origin += u'HĐ số ' + (line.reference or '') + ', '
            if len(origin):
                origin = origin[:-2]
            return origin
        return origin
    
    def get_format_ds(self, obj):
        name = ''
        for o in obj:
            for contract in o.purchase_contract_id:
                name += contract.name
                name += ', '
        return name
    
    def get_format_amount(self, obj):
        amount =0.0
        for o in obj:
            for pay in o.request_payment_ids:
                amount += pay.amount
            string = round(amount, o.purchase_contract_id.currency_id.decimal_places)
        return string
    
    def get_string_amount(self, obj):
        amount =0.0
        for o in obj:
            for pay in o.request_payment_ids:
                amount += pay.amount
        return self.amount_to_text(amount, 'vn')
    
    def get_journal_currency(self, o):
        if not o.journal_id.currency_id:
            return o.journal_id.company_id.currency_id.name
        else:
            return o.journal_id.currency_id.name
    
    def get_company_bank(self, o):
        
        if o.state != 'posted':
            raise UserError(_("Please Posted '%s' !")%(o.name))
        if not self.company_bank:
            bank_journal = o.journal_id
            if not o.journal_id.bank_id:
                raise UserError(_("Please define Bank for Journal '%s' !")%(bank_journal.name))
            
            self.company_bank.append(o.company_id.name or '')
            self.company_bank.append(bank_journal.bank_acc_number or '')
            self.company_bank.append(bank_journal.bank_id.bic or bank_journal.bank_id.name)
            self.company_bank.append(bank_journal.bank_id.name)
            self.company_bank.append(bank_journal.bank_id.city or '')
        return self.company_bank
    
    def bank_number(self):
        bank_number = self.company_bank[1]
        number = ''
        for i in range(0, len(bank_number) - 1):
            number += bank_number[i] + '   '
        return number
            
    def get_partner_bank(self, o):
        if not self.partner_bank:
            if not o.partner_bank_id:
                raise UserError(_("Please define Bank for Partner '%s' !")%(o.partner_id.name))
        
            self.partner_bank.append(o.partner_id.name or '')
            self.partner_bank.append(o.partner_bank_id.acc_number or '')
            self.partner_bank.append(o.partner_bank_id.bank_id.bic or o.partner_bank_id.bank_id.name)
            self.partner_bank.append(o.partner_bank_id.bank_id.name)
            self.partner_bank.append(o.partner_bank_id.bank_id.city or '')
        return self.partner_bank
    
    def partner_bank_number(self):
        bank_number = self.partner_bank[1]
        number = ''
        for i in range(0, len(bank_number) - 1):
            number += bank_number[i] + '   '
        return number
    
    def get_vietnam_date(self, date):
        if not date:
            date = time.strftime(DATE_FORMAT)
        date = datetime.strptime(date, DATE_FORMAT)
        return date.strftime('%d/%m/%Y')
    
    def amount_to_text(self, nbr, lang='vn'):
        user = self.pool.get('res.users')
        return user.amount_to_text(nbr, lang)
    
    def get_user_name(self):
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        return user.name
    
    def get_account_lines(self, o):
        code = ''
        if len(o.payment_lines):
            for line in o.payment_lines:
                code += line.accounts + ', '
        elif len(o.invoice_ids):
            for inv in o.invoice_ids:
                if inv.state not in ['draft', 'cancel']:
                    code = inv.account_id.code + ', '
                
        for fee in o.payment_fee_lines:
            code += fee.account_id.code + ', '
                
        if not len(code):
            code = o.destination_account_id.code + ', '
        if len(code):
            code = code[:-2]
        return code
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
