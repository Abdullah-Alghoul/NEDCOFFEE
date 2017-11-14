# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError, RedirectWarning, ValidationError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.misc import formatLang
import time

DATE_FORMAT = "%Y-%m-%d"


class SupplierManagement(models.Model):
    _name = "supplier.management"
    _order = 'id asc'
    
    from_date = fields.Date(string="Date start")
    to_date = fields.Date(string="Date End")
    distris_ids = fields.Many2many('res.district','res_districts_ids','risk_id','manager_id',string='District')
    supplier_management = fields.One2many('supplier.management.line','line_id',string="Line")
    
    
    @api.multi
    def load_data(self):
        for this in self:
#             sql ='''
#                 DELETE from supplier_management_line ;
#                  
#                 SELECT id,name from res_district where id in (
#                     select distinct district_id  from res_partner where partner_code is not null)
#             '''
#             self.env.cr.execute(sql)
#             for line in self.env.cr.dictfetchall():
#                 val ={
#                       'partner_name':line['name'],
#                       'line_id':this.id
#                 }
#                 self.env['supplier.management.line'].create(val)
            where =''' and rp.ref like ('S0%') and rp.ref not like ('NED%') and rp.ref not like ('SU%')'''
            sql = '''
                DELETE from supplier_management_line ;
                SELECT rp.district_id,rp.id partner_id,rp.name,rp.partner_code, x.*,
                y.total_booked, y.to_receive
               
                
                FROM res_partner rp 
                    left join (
                        select * from supplier_mgt where id in (
                            select max(id)
                            FROM supplier_mgt 
                            GROUP BY partnert_id)) x
                        on rp.id = x.partnert_id
                    
                    left join (
                        SELECT sum(product_qty) total_booked,pc.partner_id, sum(qty_unreceived) to_receive
                        FROM purchase_contract_line pcl join purchase_contract pc on pc.id = pcl.contract_id
                        WHERE pc.type = 'purchase' and date_order between '%s' and '%s'
                        GROUP BY pc.partner_id) y on rp.id = y.partner_id
                    
                WHERE rp.partner_code is not null %s
                ORDER BY rp.partner_code
            '''%(this.from_date,this.to_date,where)
        print sql
        self.env.cr.execute(sql)
        for i in self.env.cr.dictfetchall():
            if i['total_booked'] ==0 or i['total_booked'] == None:
                continue
            if i['ppkg'] and i['ppkg'] == None:
                i['ppkg'] = 0
            if i['total_booked'] and i['total_booked'] ==None:
                i['total_booked'] = 0
            
            m2m = 0
            sql = '''
            SELECT sum(m2m) as m2m
            FROM(
                SELECT  ((pcl.product_qty - pc.qty_received) * x.exporter_faq_price) -  (pcl.product_qty - pc.qty_received) * pcl.price_unit as m2m
                FROM 
                    purchase_contract pc join purchase_contract_line pcl on pc.id = pcl.contract_id join 
                   (select exporter_faq_price,mdate from market_price ) x on x.mdate = pc.date_order
                WHERE pc.qty_received < pcl.product_qty
                    and pc.partner_id = %s
                    and pc.date_order between '%s' and '%s') x
                    
            '''%(i['partner_id'],this.from_date,this.to_date)
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                m2m = j['m2m'] or 0.0
            
            npe_unfixqty = 0.0
            sql ='''
                SELECT sum(x.received) -  sum(pc.total_qty_fixed) as npe_unfixqty
                FROM  purchase_contract pc
                    join (
                            SELECT pc.partner_id,pc.id ,sum(qty_allocation) received
                            FROM stock_allocation sa join stock_picking sp on sa.picking_id = sp.id
                                join purchase_contract pc on pc.id = sa.contract_id and pc.type != 'purchase'
                            WHERE date_allocation between '%s' and '%s' and pc.partner_id = %s
                            group by pc.partner_id,pc.id) x
                on pc.id = x.id
                group by pc.partner_id
            '''%(this.from_date,this.to_date,i['partner_id'])
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                npe_unfixqty = j['npe_unfixqty'] or 0.0
                
            npe_funixvalue =0
            sql ='''
                SELECT  (x.received - x.fix_qty) * mp.exporter_faq_price - x.amount as npe_funixvalue 
                FROM
                    (
                    SELECT pc.name,pc.date_order,sum(qty_allocation) received,sum(total_qty_fixed) fix_qty,sum(ap.amount) amount
                        FROM stock_allocation sa join stock_picking sp on sa.picking_id = sp.id
                            join purchase_contract pc on pc.id = sa.contract_id and pc.type != 'purchase'
                            left join account_payment ap on pc.id = ap.purchase_contract_id
                        WHERE 
                            pc.partner_id = %s
                            and date_allocation between '%s' and '%s'
                        GROUP by pc.name,pc.date_order) x left join market_price mp on x.date_order = mp.mdate
            '''%(i['partner_id'],this.from_date,this.to_date)
            self.env.cr.execute(sql)
            for j in self.env.cr.dictfetchall():
                npe_funixvalue = j['npe_funixvalue'] or 0.0
            
            val ={
                  'realizable': i['ppkg'] and i['total_booked']/i['ppkg'] or 0.0,
                  'district_id':i['district_id'],
                  'partner_id':i['partner_id'],
                  'partner_name':i['name'],
                  'partner_code':i['partner_code'],
                  'repperson1':i['repperson1'],
                  'repperson2':i['repperson2'],
                  'goods':i['goods'],
                  'ppkg':i['ppkg'],
                  'estimated_annual_volume':i['estimated_annual_volume'],
                  'purchase_undelivered_limit':i['purchase_undelivered_limit'],
                  'property_evaluation':i['property_evaluation'],
                  'm2mlimit':i['m2mlimit'],
                  'negative_m2m_loss_limit':i['negative_m2m_loss_limit'],
                  'line_id':this.id,
                  'delivery_at':i['delivery_at'],
                  'total_booked':i['total_booked'],
                  'remain_qty':i['to_receive'],
                  'npe_qty':npe_unfixqty,
                  'marked_to_marke':m2m,
                  'npe_value':npe_funixvalue,
                  'ttl_m2m':m2m + npe_funixvalue,
                  'negative_m2m': m2m + npe_funixvalue < 0 and (m2m + npe_funixvalue) or 0.0
            }
            self.env['supplier.management.line'].create(val)
            
        imd = self.env['ir.model.data']
        action = imd.xmlid_to_object('ned_contract.action_ned_supplier_management_line')
        list_view_id = imd.xmlid_to_res_id('view_ned_supplier_management_line_tree')
        pivot_view_id = imd.xmlid_to_res_id('view_ned_supplier_management_line_pivot')
 
        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'],[pivot_view_id, 'pivot']],
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
            'view_type':'tree'
        }
        return result
                
            
                                                       
class SupplierManagementLine(models.Model):
    _name = "supplier.management.line"
    _order = 'id asc'
    
    partner_id = fields.Many2one('res.partner',string="Supplier")
    district_id = fields.Many2one('res.district',string="District")
    partner_code = fields.Char(string="Partner Code")
    partner_name = fields.Char(string="Partner Name")
    
    repperson1 = fields.Char(string='Primary')
    repperson2 = fields.Char(string='Secondary')
    goods = fields.Selection([('FAQ', 'FAQ'), ('Graded', 'Graded'),('Partner','Partner'),('Stop trading','Stop trading')], string='Goods')
    ppkg = fields.Float(string='PPKg',digits=(12, 0))
    
    estimated_annual_volume = fields.Float(string='Estimated Annual Volume',digits=(12, 0),group_operator = None)
    purchase_undelivered_limit = fields.Float(string='Purchase Undelivered Limit',digits=(12, 0),group_operator = None)
    property_evaluation = fields.Float(string='Property Evaluation',digits=(12, 0))
    m2mlimit = fields.Float(string='M2MLimit',digits=(12, 0))
    partnert_id = fields.Many2one('res.partner',string= 'Supplier',domain="[('supplier', '=', True)]")
    negative_m2m_loss_limit = fields.Float(string='Negative M2M loss Limit',digits=(12, 0))
    line_id = fields.Many2one('supplier.management',string= 'Report Line')
    delivery_at = fields.Selection([('Factory', 'Factory'), ('HCM', 'HCM'),('Station','Station'),
                                    ('Stop trading','Stop trading')], string='Delivery at')
    
    total_booked = fields.Float(string='Total Booked',digits=(12, 0))
    realizable = fields.Float(string='Realizable %',digits=(12, 2))
    remain_qty =  fields.Float(string='Remain qty',digits=(12, 0))
    marked_to_marke =   fields.Float(string='M2M',digits=(12, 0))
    npe_qty = fields.Float(string='NPE qty',digits=(12, 0))
    npe_value = fields.Float(string='NPE Values',digits=(12, 0))
    deposited = fields.Float(string='Deposited',digits=(12, 0))
    ttl_m2m = fields.Float(string='TTL M2M',digits=(12, 0))
    negative_m2m =fields.Float(string='Negative M2M',digits=(12, 0))
    
    limit_qty = fields.Float(string='Limit Qty',digits=(12, 0))
    limit_value = fields.Float(string='Limit value',digits=(12, 0))
    
    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False, lazy=True):
        if 'estimated_annual_volume' in fields:
            fields.remove('estimated_annual_volume')
        if 'purchase_undelivered_limit' in fields:
            fields.remove('purchase_undelivered_limit')
        if 'property_evaluation' in fields:
            fields.remove('property_evaluation')
        if 'ppkg' in fields:
            fields.remove('ppkg')
        
        if 'm2mlimit' in fields:
            fields.remove('m2mlimit')
        
        if 'negative_m2m_loss_limit' in fields:
            fields.remove('negative_m2m_loss_limit')
        
        if 'realizable' in fields:
            fields.remove('realizable')
        
        if 'marked_to_marke' in fields:
            fields.remove('marked_to_marke')
        
        if 'limit_qty' in fields:
            fields.remove('limit_qty')
            
        if 'limit_value' in fields:
            fields.remove('limit_value')
        
        if 'ttl_m2m' in fields:
            fields.remove('ttl_m2m')
        
        if 'negative_m2m' in fields:
            fields.remove('negative_m2m')
            
            
            
        res = super(SupplierManagementLine, self).read_group(cr, uid, domain, fields, groupby, offset=offset, limit=limit, context=context, orderby=orderby, lazy=lazy)
        return res

class GainLoss(models.Model):
    _name = "gain.loss"
    _order = 'id desc'
    
    from_date = fields.Date(string="Date start")
    to_date = fields.Date(string="Date End")
    picking_type_id = fields.Many2one('stock.picking.type',string="Branch/Buying Station")
    loss_line = fields.One2many('gain.loss.line','loss_id',string="Loss Line")
    loss_summary = fields.One2many('gain.loss.summary','loss_id',string="Summary")
    
    #abc = fields.Text('asas')
    
    @api.multi
    def export_data(self):
        return {
                'type': 'ir.actions.report.xml',
                'report_name':'gain_loss_report',
    }
    @api.multi
    def load_data(self):
        
#         self.abc = '''
#                 <html>
#                       <head>
#                         <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>
#                         <script type="text/javascript">
#                           google.charts.load('current', {'packages':['geochart']});
#                           google.charts.setOnLoadCallback(drawRegionsMap);
#                     
#                           function drawRegionsMap() {
#                     
#                             var data = google.visualization.arrayToDataTable([
#                               ['Country', 'Popularity'],
#                               ['Germany', 200],
#                               ['United States', 300],
#                               ['Brazil', 400],
#                               ['Canada', 500],
#                               ['France', 600],
#                               ['RU', 700]
#                             ]);
#                     
#                             var options = {};
#                     
#                             var chart = new google.visualization.GeoChart(document.getElementById('regions_div'));
#                     
#                             chart.draw(data, options);
#                           }
#                         </script>
#                       </head>
#                       <body>
#                         <div id="regions_div" style="width: 900px; height: 500px;"></div>
#                       </body>
#                     </html>
#             
#             '''
        
        loss_basis_qty  = loss_init_qty = station_basis_qty = factory_basis_qty = 0
        for this in self:
            # Tao chi tiet
            sql ='''
                DELETE FROM gain_loss_line where loss_id = %s;
                 
                DELETE FROM gain_loss_summary where loss_id = %s;
            '''%(this.id,this.id)
            self.env.cr.execute(sql)
             
            sql ='''
                SELECT id,total_init_qty,total_qty,date_done
                FROM 
                    stock_picking 
                WHERE date(timezone('UTC',date_done::timestamp)) between  '%s' and '%s'
                and picking_type_id = %s
                and state ='done'
                order by date_done
            '''%(self.from_date,self.to_date,self.picking_type_id.id)
            self.env.cr.execute(sql)
            for line in self.env.cr.dictfetchall():
                pick =self.env['stock.picking'].browse(line['id'])
                grn_nm =False
                grn_factory =''
                init_qty =0.0
                product_qty= 0.0
                date_nm = False
                
                sql ='''
                    SELECT id picking_id from stock_picking 
                        WHERE backorder_id = %s
                        and picking_type_id in (151,104)
                '''%(line['id'])
                self.env.cr.execute(sql)
                for j in self.env.cr.dictfetchall():
                    pick =self.env['stock.picking'].browse(j['picking_id'])
                    if pick.state != 'done':
                        continue
#                     grn_nm = pick.id
                    grn_factory += pick.name +','
                    init_qty += pick.total_init_qty
                    product_qty += pick.total_qty
                    date_nm = pick.date_done
                
#                 sql ='''
#                     SELECT picking_id from transfer_internal_res 
#                         where transfer_id = %s
#                 '''%(line['id'])
#                 self.env.cr.execute(sql)
#                 for i in self.env.cr.dictfetchall():
#                     sql='''
#                         SELECT picking_id from transfer_internal_res 
#                             where transfer_id = %s
#                     '''%(i['picking_id'])
#                     self.env.cr.execute(sql)
#                     for j in self.env.cr.dictfetchall():
#                         pick =self.env['stock.picking'].browse(j['picking_id'])
#                         if pick.state != 'done':
#                             continue
#                         grn_nm = pick.id
#                         grn_factory += pick.name +','
#                         init_qty += pick.total_init_qty
#                         product_qty += pick.total_qty
#                         date_nm = pick.date_done
                 
                station_basis_qty += line['total_init_qty']
                factory_basis_qty += product_qty
                loss_init_qty +=   init_qty - line['total_init_qty']
                loss_basis_qty +=  (product_qty - line['total_qty']) - (init_qty - line['total_init_qty'])
                 
                vals ={
                       'loss_id':this.id,
                       'date_station':line['date_done'],
                       'date_factory':date_nm,
                       'grn_station_id':line['id'],
                       'grn_factory':grn_factory,
                       'grn_factory_id':grn_nm,
                       'net_station':line['total_init_qty'],
                       'Net_factory':init_qty,
                       'basic_station':line['total_qty'],
                       'basic_factory':product_qty,
                       'loss_station':init_qty - line['total_init_qty'],
                       'loss_factory':(product_qty - line['total_qty']) - (init_qty - line['total_init_qty']),
                       'total_factory':(init_qty - line['total_init_qty']) + (product_qty - line['total_qty']) - (init_qty - line['total_init_qty'])
                }
                 
                self.env['gain.loss.line'].create(vals)
             
            #Tao summary
            for loop in (1,2,3,4,5,6,7,8):
                if loop == 1:
                    vals ={
                    'name':   'Total received at Station- Kg',
                    'value':station_basis_qty,
                    'loss_id':this.id
                       }
                    self.env['gain.loss.summary'].create(vals)
                 
                if loop == 2:
                    vals ={
                    'name':   'Total received at Factory- Kg',
                    'value': factory_basis_qty,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                 
                if loop == 3:
                    vals ={
                    'name':   'Gain/Loss Weight - Kg',
                    'value': loss_init_qty,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                 
                if loop == 4:
                    vals ={
                    'name':   '%',
                    'value': station_basis_qty and (loss_init_qty / station_basis_qty) *100 or 0.0 ,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                 
                if loop == 5:
                    vals ={
                    'name':   'Gain/Loss Quality - Kg',
                    'value': loss_basis_qty,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                     
                if loop == 6:
                    vals ={
                    'name': '%',
                    'value': loss_basis_qty and (loss_basis_qty / factory_basis_qty) *100 or 0.0,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                 
                if loop == 7:
                    vals ={
                    'name':   'Total Gain/Loss - Kg',
                    'value': loss_init_qty + loss_basis_qty,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
                     
                if loop == 8:
                    vals ={
                    'name':   '%',
                    'value':station_basis_qty and  (loss_init_qty +loss_basis_qty ) / station_basis_qty*100  or 0.0,
                    'loss_id':this.id
                    }
                    self.env['gain.loss.summary'].create(vals)
            
                    
class GainLossLine(models.Model):
    _name = "gain.loss.line"
    _order = 'id asc'
    
    loss_id = fields.Many2one('gain.loss',string="Gain Loss" ,ondelete='cascade')
    date_station = fields.Date('Date Station')
    date_factory = fields.Date('Date Factory')
    grn_station_id = fields.Many2one('stock.picking',string="GRN Station")
    grn_factory_id = fields.Many2one('stock.picking',string="GRN Factory")
    grn_factory = fields.Char(string="GRN Factory")
    net_station = fields.Float(string="Net Station" ,digits=(12, 0))
    Net_factory = fields.Float(string="Net Factory" , digits=(12, 0))
    basic_station = fields.Float(string="Basic Station", digits=(12, 0))
    basic_factory = fields.Float(string="Basic Factory", digits=(12, 0))
    
    loss_station = fields.Float(string="Gain/Loss Weight", digits=(12, 0))
    loss_factory = fields.Float(string="Gain/Loss Quality",digits=(12, 0))
    total_factory = fields.Float(string="Total Gain/Loss", digits=(12, 0))

class GainLossSumarry(models.Model):
    _name = "gain.loss.summary"
    _order = 'id asc'
    
    name= fields.Char('Name')
    value =fields.Float('')
    loss_id = fields.Many2one('gain.loss',string="Gain Loss" ,ondelete='cascade')
    
               
    
    
    