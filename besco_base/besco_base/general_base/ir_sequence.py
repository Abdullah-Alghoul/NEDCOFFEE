# -*- coding: utf-8 -*-
import time
import pytz

from datetime import datetime
from openerp import _, api, fields, models, SUPERUSER_ID
from openerp.exceptions import UserError

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

def _update_nogap(self, number_increment):
    number_next = self.number_next
    self.env.cr.execute("SELECT number_next FROM %s WHERE id=%s FOR UPDATE NOWAIT" % (self._table, self.id))
    self.env.cr.execute("UPDATE %s SET number_next=number_next+%s WHERE id=%s " % (self._table, number_increment, self.id))
    self.invalidate_cache(['number_next'], [self.id])
    return number_next

class ir_sequence(models.Model):
    _inherit = 'ir.sequence'
    
    date_get = fields.Selection([('1', 'System Date'),
                                 ('2', 'Transact Date')],
                                string='Date Get', default='2')
    split_number = fields.Boolean(string='Split number')
    rollback_rule = fields.Selection([('None', 'None'), 
                                      ('Daily', 'Daily'),
                                      ('Monthly', 'Monthly'),
                                      ('Yearly', 'Yearly'),],
                                      string='Rollback Rule', default='Monthly')
    barcode_seq = fields.Boolean(string='Create Barcode', default=False)
    sequence_his = fields.One2many('ir.sequence.his', 'seq_id', string='Sequence Histories', readonly=False)
    
    @api.model
    def default_get(self, fields):
        rec = super(ir_sequence, self).default_get(fields)
        rec.update({
            #THANH: alway = true at creation
            'padding': 4,
            'use_date_range': False,
        })
        return rec
    
    def seq_generate_ean13(self, barcode):
        if barcode is None:
            return None
        
        if len(barcode) <> 12:
            return None
        
        total = 0
        chars = str(barcode)
        for i, c in enumerate(chars):
            total += int(c) if i % 2 == 0 else int(c) * 3
        
        check_sum = (10 - (total % 10)) % 10
        return barcode + str(check_sum)
    
    #Thanh: Add more Fields to sequence
    def _interpolation_dict_extend(self, obj_ids):
        def get_shop_code(id):
            if (id is None):
                return ''
            
            try:
                self.env.cr.execute("Select code from sale_shop where id = %s"%(id))
                res = self.env.cr.fetchone()
                return res and res[0] or ''
            except:
                return ''
        
        def get_pos_code(id):
            if (id is None):
                return ''
                
            try:
                self.env.cr.execute("Select code from pos_config where id = %s"%(id))
                res = self.env.cr.fetchone()
                return res and res[0] or ''
            except:
                return None
        
        def get_warehouse_code(id):
            if (id is None):
                return ''
                
            try:
                self.env.cr.execute("Select code from stock_warehouse where id = %s"%(id))
                res = self.env.cr.fetchone()
                return res and res[0] or ''
            except:
                return None
        
        def get_analytic_code(id):
            if (id is None):
                return ''
                
            try:
                self.env.cr.execute("Select code from account_analytic_account where id = %s"%(id))
                res = self.env.cr.fetchone()
                return res and res[0] or ''
            except:
                return None
            
        res = {'shop': '',
               'warehouse': '',
               'analis': '',
               'pos': ''}
        for obj_id in obj_ids:
            if obj_id[0] == 'shop':
                res['shop'] = get_shop_code(obj_id[1])
            if obj_id[0] == 'warehouse':
                res['warehouse'] = get_warehouse_code(obj_id[1])
            if obj_id[0] == 'analis':
                res['analis'] = get_analytic_code(obj_id[1])
            if obj_id[0] == 'pos':
                res['pos'] = get_pos_code(obj_id[1])
        return res
    
    #Thanh: Add more Fields
    def get_next_char(self, number_next):
        context = self._context
        
        def _interpolate(s, d):
            if s:
                return s % d
            return ''
        
        def _interpolation_dict():
            now = datetime.now(pytz.timezone(self.env.context.get('tz') or 'UTC'))
            if self.env.context.get('ir_sequence_date'):
                t = datetime.strptime(self.env.context.get('ir_sequence_date'), '%Y-%m-%d')
            else:
                t = now
            
            #THANH: Get transaction date
            context = self._context
            if context.get('ir_sequence_date', False) and self.date_get == '2':
                t = datetime.strptime(context['ir_sequence_date'], DATE_FORMAT)
            else:
                t = datetime.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d')
                
            sequences = {
                'year': '%Y', 'month': '%m', 'day': '%d', 'y': '%y', 'doy': '%j', 'woy': '%W',
                'weekday': '%w', 'h24': '%H', 'h12': '%I', 'min': '%M', 'sec': '%S'
            }
            res = {}
            for key, sequence in sequences.iteritems():
                res[key] = t.strftime(sequence)
                res['range_' + key] = t.strftime(sequence)

            return res
        
        #Thanh: Change to way to get sequence number
        type_standard = False
        if not number_next: #Thanh: Mean type = standard
            type_standard = True
            if context.get('ir_sequence_date', False) and self.date_get == '2':
                transaction_date = datetime.strptime(context['ir_sequence_date'], DATE_FORMAT)
                day = int(transaction_date.strftime('%d'))
                m = int(transaction_date.strftime('%m'))
                y = int(transaction_date.strftime('%Y'))
            else:
                day = int(time.strftime('%d'))
                m = int(time.strftime('%m'))
                y = int(time.strftime('%Y'))
             
            sql = "select coalesce(max(his.number_current),0) from ir_sequence_his his where his.seq_id = %s"%(self.id)
            if self.rollback_rule == 'Yearly':
                sql += " and his.year = %s"%(y)
            if self.rollback_rule == 'Monthly':
                sql += " and his.year = %s"%(y) + " and his.month = %s"%(m)
            if self.rollback_rule == 'Daily':
                sql += ' and his.year = %s'%(y) + ' and his.month = %s'%(m) + ' and his.day = %s'%(day)
            self.env.cr.execute(sql)
            result = self.env.cr.fetchone()
            
            if result and result[0] != 0:
                number_current = result[0]
                number_next = number_current + self.number_increment
            else:
                #Thanh: Default get from field number_next if no sequence history
                number_next = self.number_next_actual
        #Thanh: Change to way to get sequence number
        
        d = _interpolation_dict()
        
        #Thanh: Get more _interpolation_dict
        d.update(self._interpolation_dict_extend(context.get('sequence_obj_ids',[])))
        #Thanh: Get more _interpolation_dict
        
        try:
            interpolated_prefix = _interpolate(self.prefix, d)
            interpolated_suffix = _interpolate(self.suffix, d)
        except ValueError:
            raise UserError(_('Invalid prefix or suffix for sequence \'%s\'') % (self.get('name')))
        sequence = interpolated_prefix + '%%0%sd' % self.padding % number_next + interpolated_suffix
        #Thanh: Insert into History
        if type_standard: 
            self.env.cr.execute('''
                        INSERT INTO ir_sequence_his (create_uid,create_date,write_uid,write_date,
                            seq_id,generate_code,company_id,number_current,
                            day,month,year)
                        VALUES (%s,current_timestamp,%s,current_timestamp,
                                %s,'%s',%s,%s,
                                %s,%s,%s);
            '''%(self.env.user.id, self.env.user.id, self.id, sequence, self.env.user.company_id.id, number_next, day, m, y))
        #Thanh: Insert into History
        return sequence
    
    #Thanh: dont get number for type standard
    def _next_do(self):
        if self.implementation == 'standard':
            number_next = False
#             number_next = _select_nextval(self.env.cr, 'ir_sequence_%03d' % self.id)
        else:
            number_next = _update_nogap(self, self.number_increment)
        return self.get_next_char(number_next)
    
class ir_sequence_date_range(models.Model):
    _inherit = 'ir.sequence.date_range'
    
    #Thanh: dont get number for type standard
    def _next(self):
        if self.sequence_id.implementation == 'standard':
            number_next = False
        else:
            number_next = _update_nogap(self, self.sequence_id.number_increment)
        return self.sequence_id.get_next_char(number_next)
    
class ir_sequence_his(models.Model):
    _name = 'ir.sequence.his'
    _order = 'generate_code desc'
    
    seq_id = fields.Many2one('ir.sequence', 'Sequence', required=False)
    generate_code = fields.Char('Generate Code', size=64, required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True,
                                 default=lambda s: s.env['res.company']._company_default_get('ir.sequence'))
    number_current = fields.Integer('Number Current', required=True)
    day = fields.Integer('Day', help="Day of a month (1..31)")
    month = fields.Integer('Month', help="Month of a year (1..12)")
    year = fields.Integer('Year')
#         'f_key': fields.integer('F Key', required=False),
#         'f_table': fields.char('F Table', size=64, required=False),

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: