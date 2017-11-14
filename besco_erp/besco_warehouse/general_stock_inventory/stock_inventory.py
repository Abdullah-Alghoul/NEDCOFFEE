# -*- coding: utf-8 -*-
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp import SUPERUSER_ID
from openerp.exceptions import UserError
import openerp.addons.decimal_precision as dp

import base64
import xlrd

class stock_inventory(osv.osv):
    _inherit = "stock.inventory"
    
    #Thanh: Add more options to filter inventory
    def _get_available_filters(self, cr, uid, context=None):
        """
           This function will return the list of filter allowed according to the options checked
           in 'Settings\Warehouse'.

           :rtype: list of tuple
        """
        #default available choices
        res_filter = [
                      ('partial', _('Manual Selection of Products')),
                      #Thanh: Add more options
                      ('products', _('By Products')),
                      ('cats', _('By Categories')),
                      ('none', _('All products')),
                      #Thanh: Hide these options
#                       ('product', _('One product only'))
                      #Thanh: Hide these options
                      ]
        settings_obj = self.pool.get('stock.config.settings')
        config_ids = settings_obj.search(cr, uid, [], limit=1, order='id DESC', context=context)
        #If we don't have updated config until now, all fields are by default false and so should be not dipslayed
        if not config_ids:
            return res_filter

        stock_settings = settings_obj.browse(cr, uid, config_ids[0], context=context)
        if stock_settings.group_stock_tracking_owner:
            res_filter.append(('owner', _('One owner only')))
            res_filter.append(('product_owner', _('One product for a specific owner')))
        if stock_settings.group_stock_tracking_lot:
            res_filter.append(('lot', _('One Lot/Serial Number')))
        if stock_settings.group_stock_packaging:
            res_filter.append(('pack', _('A Pack')))
        return res_filter
    
    INVENTORY_STATE_SELECTION = [
        ('draft', 'Draft'),
        ('cancel', 'Cancelled'),
        ('confirm', 'In Progress'),
        #THANH: Add one status
        ('in_queue', 'In Queue'),
        #THANH: Add one status
        ('done', 'Validated'),
    ]
    
    _columns = {
        'date': fields.datetime('Inventory Date', required=True, readonly=False),
        'filter': fields.selection(_get_available_filters, 'Inventory of', required=True,
                                   help="If you do an entire inventory, you can choose 'All Products' and it will prefill the inventory with the current stock.  If you only do some products  "\
                                      "(e.g. Cycle Counting) you can choose 'Manual Selection of Products' and the system won't propose anything.  You can also let the "\
                                      "system propose for a single product / lot /... "),
                
        'search_product_ean': fields.char('Search Product/EAN', size=300),
        'freeze_date': fields.datetime('Freeze Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'file': fields.binary('File', help='Choose file Excel', required=False, readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}),
        'file_name': fields.char('Filename', 100, readonly=True),
        'picking_type_id': fields.many2one('stock.picking.type', 'Inventory Type', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        
        'categ_ids': fields.many2many('product.category', 'stock_inventory_category_rel', 
                                      'inventory_id', 'categ_id', 'Categories', readonly=True, states={'draft': [('readonly', False)]}),
        'product_ids': fields.many2many('product.product', 'stock_inventory_product_rel', 
                                      'inventory_id', 'product_id', 'Products', readonly=True, states={'draft': [('readonly', False)]}),
        
        #THANH: Add one status
        'state': fields.selection(INVENTORY_STATE_SELECTION, 'Status', readonly=True, select=True, copy=False),
        'queue_from_date': fields.datetime("Queue From", readonly=True),
        'queue_to_date': fields.datetime("Queue To", readonly=True),
    }
    
    _defaults = {
        'filter': 'partial',
        'freeze_date': fields.datetime.now,
        'file_name': 'Inventory Count.xls',
        
        #THANH: Auto get location from picking type
        'location_id': False,
        'name': '/',
    }
    
    #THANH: Cancel a done inventory
    def action_cancel_done_inventory(self, cr, uid, ids, context=None):
        move_obj = self.pool.get('stock.move')
        for inv in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [inv.id], {'line_ids': [(5,)]}, context=context)
            
            for move in inv.move_ids:
                default_val = {
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': move.location_id.id,
                    'scrapped': True,
                    'picking_id': False,
                }
                new_move_id = move_obj.copy(cr, uid, move.id, default_val)
                move_obj.action_done(cr, uid, [new_move_id])
                
                #Thanh: Delete these revert move to balance stock
                try:
                    cr.execute('''DELETE FROM stock_picking 
                                    WHERE id in (select picking_id from stock_move where id=%s)'''%(new_move_id))
                    cr.execute("DELETE FROM stock_move WHERE id=%s"%(new_move_id))
                except Exception, ex:
                    pass
                    
                move_obj.action_cancel(cr, uid, [move.id])
                move_obj.write(cr, uid, [move.id], {'state': 'draft'})
                
            self.write(cr, uid, [inv.id], {'state': 'draft', 'queue_from_date': False, 'queue_to_date': False,
                                           'move_ids': [(5,)]}, context=context)
        return True
        
    #THANH: Put this inventory in to queue that cron will handle it
    def action_in_queue(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        
        dummy, schedule_id = tuple(mod_obj.get_object_reference(cr, uid, 'general_stock_inventory', "ir_cron_validate_inventory"))
        if not schedule_id:
            raise UserError(_('Schedule validate inventory is not defined !'))
#             self.pool.get('ir.cron').write(cr, SUPERUSER_ID, [schedule_id], {'active': True,
#                                                                              'numbercall': 1,
#                                                                              'nextcall': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
#         else:
#             raise UserError(_('Schedule validate inventory is not defined !'))
        
        #THANH: Generate stock_move lines
        self.action_check(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'in_queue', 'queue_from_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
    
    #THANH: After creating stock_move, it should post and done before going to next line
    def action_done(self, cr, uid, ids, context=None):
        """ Finish the inventory
        @return: True
        """
        stock_move_obj = self.pool.get('stock.move')
        
        for inv in self.browse(cr, uid, ids, context=context):
            for inventory_line in inv.line_ids:
                if inventory_line.product_qty < 0 and inventory_line.product_qty != inventory_line.theoretical_qty:
                    raise UserError(_('You cannot set a negative product quantity in an inventory line:\n\t%s - qty: %s' % (inventory_line.product_id.name, inventory_line.product_qty)))
            
            #THANH: Done each stock move then run next line
            for move in inv.move_ids:
                try:
                    if move.state != 'done':
                        stock_move_obj.action_done(cr, uid, [move.id], context=context)
                        cr.execute('commit;')
                except Exception, ex:
                    pass
            
#             self.action_check(cr, uid, [inv.id], context=context)
            self.write(cr, uid, [inv.id], {'state': 'done'}, context=context)
#             self.post_inventory(cr, uid, inv, context=context)
        return True
    #THANH: After creating stock_move, it should post and done before going to next line
       
    def cron_watch_cron_validate_inventory(self, cr, uid, context=None):
        mod_obj = self.pool.get('ir.model.data')
        
        dummy, schedule_id = tuple(mod_obj.get_object_reference(cr, uid, 'general_stock_inventory', "ir_cron_validate_inventory"))
        if schedule_id:
            try:
                schedule = self.pool.get('ir.cron').browse(cr, SUPERUSER_ID, schedule_id)
                inv_ids = self.search(cr, SUPERUSER_ID, [('state', '=', 'in_queue')])
                if len(inv_ids) and not schedule.active:
                    self.pool.get('ir.cron').method_direct_trigger(cr, SUPERUSER_ID, [schedule_id])
#                     self.pool.get('ir.cron').write(cr, SUPERUSER_ID, [schedule_id], {'active': True,
#                                                                                      'numbercall': 1,
#                                                                                      'nextcall': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
            except Exception, ex:
                pass
        return True
    
    def cron_validate_inventory(self, cr, uid, context=None):
        context = {}
        mod_obj = self.pool.get('ir.model.data')
        
        dummy, schedule_id = tuple(mod_obj.get_object_reference(cr, uid, 'general_stock_inventory', "ir_cron_validate_inventory"))
        if schedule_id:
            try:
                inv_ids = self.search(cr, SUPERUSER_ID, [('state', '=', 'in_queue')], order='freeze_date', limit=1)
                if len(inv_ids):
#                 for inv_id in inv_ids:
                    self.action_done(cr, SUPERUSER_ID, [inv_ids[0]], context=context)
                    self.write(cr, SUPERUSER_ID, [inv_ids[0]], {'queue_to_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})
                    cr.execute('commit;')
                self.pool.get('ir.cron').write(cr, SUPERUSER_ID, [schedule_id], {'active': False})
            except Exception, ex:
                self.pool.get('ir.cron').write(cr, SUPERUSER_ID, [schedule_id], {'active': False})
        return True
    
#    Duyanh: Get location from picking type
    def onchange_picking_type(self,cr,uid,ids,picking_type_id,context=None):
        if picking_type_id:
            type = self.pool.get('stock.picking.type').browse(cr, uid, picking_type_id, context=context)
            src_location = type.default_location_src_id.id or False
            dest_location = type.default_location_dest_id.id or False
            return {'value': {'location_id': src_location,'location_dest_id':dest_location}}
        else:
            return True
    
    def read_files(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        inven_line_obj = self.pool.get('stock.inventory.line')
        
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            for row in range(sh.nrows):
                if row >= 8:
                    inv_line_id = sh.cell(row,1).value
                    if inv_line_id:
                        inv_line_id = int(inv_line_id)
                        product_qty = sh.cell(row,10).value or 0.0
                        freeze_cost = sh.cell(row,11).value or 0.0
                        
                        vals = {'product_qty': product_qty}
                        if freeze_cost:
                            vals.update({'freeze_cost':freeze_cost})
                            
                        inven_line_obj.write(cr, uid, [inv_line_id], vals)
                    else:
                        location = location_obj.search(cr, uid, [('name','=',sh.cell(row,2).value)])
                        try:
                            location_id = location and location[0] or this.location_id.id
                        except:
                            continue
                        
                        product_qty = sh.cell(row,10).value or 0.0
                        freeze_cost = sh.cell(row,11).value or 0.0
                        
                        default_code = sh.cell(row,5).value
                        if isinstance(default_code, float):
                            default_code = int(default_code)
                            default_code = str(default_code)
                        
                        barcode = sh.cell(row,6).value
                        if isinstance(barcode, float):
                            barcode = int(barcode)
                            barcode = str(barcode)
                            
                        product_id = product_obj.search(cr, uid, ['|', 
                                                     ('default_code','=', default_code), 
                                                     ('barcode','=', barcode)])
                        if product_id:
                            product_id = product_id[0] or False
                        else:
                            raise osv.except_osv(_('Warning!'), _('The Barcode ' + barcode +' is not exist !!!'))
                        
                        product = product_obj.read(cr, uid, product_id, ['uom_id', 'standard_price'])
                        product_uom = product['uom_id'][0]
                        standard_price = product['standard_price']
                        
                        vals = {
                              'inventory_id':ids[0],
                              'product_id':product_id,
                              'product_uom_id': product_uom or False,
                              'product_qty': product_qty,
                              'location_id': location_id,
                              'freeze_cost':freeze_cost,
                        }
                         
                        #THANH: Check exist inventory for this product
                        cr.execute('''
                            select sil.id 
                            from stock_inventory_line sil 
                                inner join stock_inventory si on sil.inventory_id=si.id and si.state = 'done' 
                                    and si.freeze_date < '%s'
                            where sil.product_id = %s and si.company_id=%s
                        '''%(this.freeze_date, product_id, this.company_id.id))
                        if len(cr.fetchall()) > 0:
                            sql = '''
                                SELECT stm.price_unit
                                FROM
                                stock_move stm 
                                    join stock_location loc1 on stm.location_id = loc1.id
                                    join stock_location loc2 on stm.location_dest_id = loc2.id
                                WHERE 
                                    stm.date < '%s' and product_id = %s
                                    and stm.state = 'done'
                                    and ((loc1.usage = 'internal' and loc2.usage != 'internal')
                                    or (loc1.usage = 'internal' and loc2.usage = 'internal'))
                                    and stm.company_id=%s
                                ORDER BY stm.date desc
                                LIMIT 1
                            '''%(this.freeze_date, product_id, this.company_id.id)
                            cr.execute(sql)
                            res = cr.fetchone()
                            vals.update({'freeze_cost':res and res[0] or 0.0})
                        
                        inven_line_ids = inven_line_obj.search(cr, uid, [('location_id','=',location_id),
                                                                         ('inventory_id','=',ids[0]),
                                                                         ('product_id','=',product_id),
                                                                         ('product_uom_id','=',product_uom)]) or []
                        if inven_line_ids:
                            inven_line_obj.write(cr, uid, inven_line_ids ,vals)
                        else:
                            try:
                                inven_line_ids.append(inven_line_obj.create(cr, uid, vals))
                            except Exception, e:
                                raise osv.except_osv(_('Warning!'), str(e))
                        
                        if len(inven_line_ids):
                            inven_line = inven_line_obj.browse(cr, uid,  inven_line_ids[0])
                            if inven_line.theoretical_qty <= 0 and freeze_cost <= 0:
                                inven_line_obj.write(cr, uid, inven_line_ids, {'freeze_cost': standard_price})
        return True
    
    def read_file(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids[0])
        product_obj = self.pool.get('product.product')
        inven_line_obj = self.pool.get('stock.inventory.line')
        
        try:
            recordlist = base64.decodestring(this.file)
            excel = xlrd.open_workbook(file_contents = recordlist)
            sh = excel.sheet_by_index(0)
        except Exception, e:
            raise osv.except_osv(_('Warning!'), str(e))
        if sh:
            falg = False
            for row in range(sh.nrows):
                if not falg:
                    falg = True
                    continue
                product_qty = sh.cell(row,10).value or 0.0
                total_cost = sh.cell(row,11).value or 0.0
                if not product_qty and product_qty ==0:
                    continue
                
                try:
                    freeze_cost = float(total_cost)/ float(product_qty)
                except Exception, e:
                    print sh.cell(row,0).value
                
                default_code = sh.cell(row,0).value
#                 if isinstance(default_code, float):
#                     default_code = int(default_code)
#                     default_code = str(default_code)
                
                    
                product_id = product_obj.search(cr, uid, [('default_code','=', default_code)])
                if product_id:
                    product_id = product_id[0] or False
                else:
                    print 'tim khong ra' +sh.cell(row,0).value
                    continue
                    
                product = product_obj.read(cr, uid, product_id, ['uom_id', 'standard_price'])
                product_uom = product['uom_id'][0]
                
                vals = {
                      'inventory_id':ids[0],
                      'product_id':product_id,
                      'product_uom_id': product_uom or False,
                      'product_qty': product_qty,
                      'location_id': 73,
                      'freeze_cost':freeze_cost,
                }
                 
                #THANH: Check exist inventory for this product
                try:
                    inven_line_obj.create(cr, uid, vals)
                except Exception, e:
                    raise osv.except_osv(_('Warning!'), str(e))
                        
        return True
    
#     def read_file(self, cr, uid, ids, context=None):
#         this = self.browse(cr, uid, ids[0])
#         falg = False
#         try:
#             recordlist = base64.decodestring(this.file)
#             excel = xlrd.open_workbook(file_contents = recordlist)
#             sh = excel.sheet_by_index(0)
#         except Exception, e:
#             raise osv.except_osv(_('Warning!'), str(e))
#         if sh:
#             for row in range(sh.nrows):
#                 a = sh.cell(row,0).value 
#                 if sh.cell(row,0).value == u'Vị trí kho':
#                     falg = True
#                     continue
#                 if falg:
#                     freeze_cost = sh.cell(row,6).value or 0.0
#                     location = self.pool.get('stock.location').search(cr, uid, [('name','=',sh.cell(row,0).value)])
#                     try:
#                         location_id = location and location[0] or this.location_id.id
#                     except:
#                         a = sh.cell(row,0).value
#                     product_uom = self.pool.get('product.uom').search(cr, uid, [('name','=',sh.cell(row,4).value)])
#                     if product_uom:
#                         product_uom = product_uom[0] or False
#                     
#                     barcode = sh.cell(row,3).value
#                     if isinstance(barcode, float):
#                         barcode = int(barcode)
#                         barcode = str(barcode)
#                     if isinstance(barcode, str):
#                         barcode = barcode.split("'")
#                         if len(barcode) > 1:
#                             barcode = barcode[1]
#                         else:
#                             barcode = barcode[0]
#                         
#                     default_code = sh.cell(row,2).value
#                     if isinstance(default_code, float):
#                         default_code = int(default_code)
#                         default_code = str(default_code)
#                         
#                     if isinstance(barcode, float):
#                         barcode = int(barcode)
#                         barcode = str(barcode)
#                     product_id = self.pool.get('product.product').search(cr,uid,['|', 
#                                                  ('default_code','=', default_code), 
#                                                  ('barcode','=', barcode)])
#                     if product_id:
#                         product_id = product_id[0] or False
#                         if not product_uom:
#                             product = self.pool.get('product.product').browse(cr,uid,product_id)
#                             product_uom = product.uom_id.id
#                     else:
#                         continue
#                     
#                     count_quantity = sh.cell(row,5).value or 0.0
#                     var = {
#                           'inventory_id':ids[0],
#                           'product_id':product_id,
#                           'product_uom_id':product_uom or False,
#                           'product_qty': count_quantity,
#                           'location_id':location_id,
#                     }
#                     
#                     #THANH: Check exist inventory for this product
#                     cr.execute('''
#                         select sil.id 
#                         from stock_inventory_line sil 
#                             inner join stock_inventory si on sil.inventory_id=si.id and si.state = 'done' 
#                                 and si.freeze_date < '%s'
#                         where sil.product_id = %s and si.company_id=%s
#                     '''%(this.freeze_date, product_id, this.company_id.id))
#                     if len(cr.fetchall()) > 0:
#                         sql = '''
#                             SELECT stm.price_unit
#                             FROM
#                             stock_move stm 
#                                 join stock_location loc1 on stm.location_id = loc1.id
#                                 join stock_location loc2 on stm.location_dest_id = loc2.id
#                             WHERE 
#                                 stm.date < '%s' and product_id = %s
#                                 and stm.state = 'done'
#                                 and ((loc1.usage = 'internal' and loc2.usage != 'internal')
#                                 or (loc1.usage = 'internal' and loc2.usage = 'internal'))
#                                 and stm.company_id=%s
#                             ORDER BY stm.date desc
#                             LIMIT 1
#                         '''%(this.freeze_date, product_id, this.company_id.id)
#                         cr.execute(sql)
#                         res = cr.fetchone()
#                         var.update({'freeze_cost':res and res[0] or 0.0})
#                     else:
#                         var.update({'freeze_cost':freeze_cost})
#                     
#                     inventory_ids = self.pool.get('stock.inventory.line').search(cr, uid, [('location_id','=',location_id),('inventory_id','=',ids[0]),('product_id','=',product_id),('product_uom_id','=',product_uom)])
#                     if inventory_ids:
#                         self.pool.get('stock.inventory.line').write(cr, uid, inventory_ids ,var)
#                     else:
#                         try:
#                             self.pool.get('stock.inventory.line').create(cr, uid,var)
#                         except Exception, e:
#                             a = sh.cell(row,2).value
#                             b= sh.cell(row,3).value
#                             c = sh.cell(row,1).value
#                             print a,b,c
#                             raise osv.except_osv(_('Warning!'), str(c))
#         return True
    
    def print_report(self, cr, uid, ids,context=None):
        return {'type': 'ir.actions.report.xml', 'report_name': 'inventory_count'}
    
    def _get_inventory_lines(self, cr, uid, inventory, context=None):
        location_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        location_ids = location_obj.search(cr, uid, [('id', 'child_of', [inventory.location_id.id])], context=context)
        domain = ' location_id in %s'
        args = (tuple(location_ids),)
        if inventory.partner_id:
            domain += ' and owner_id = %s'
            args += (inventory.partner_id.id,)
        if inventory.lot_id:
            domain += ' and lot_id = %s'
            args += (inventory.lot_id.id,)
        if inventory.product_id:
            domain += ' and product_id = %s'
            args += (inventory.product_id.id,)
        if inventory.package_id:
            domain += ' and package_id = %s'
            args += (inventory.package_id.id,)
        
        #kiet add điều kiện Feeze_date 
        if inventory.freeze_date:
            domain += ' and in_date <= %s'
            args += (inventory.freeze_date,)
        
        #Thanh: Change filter by products and categs
        categ_obj = self.pool.get('product.category')
        if inventory.filter == 'cats':
            categ_ids = categ_obj.search(cr, uid, [('id',
                             'child_of', [x.id for x in inventory.categ_ids])], order="id",
                             context=context)
            domain += ' and categ_id in %s'
            args += (tuple(categ_ids),)
        if inventory.filter == 'products':
            product_ids = [x.id for x in inventory.product_ids]
            domain += ' and product_id in %s'
            args += (tuple(product_ids),)
        #Thanh: Change filter by products and categs
        
        cr.execute('''
           SELECT product_id, sum(qty) as product_qty, location_id, lot_id as prod_lot_id, package_id, owner_id as partner_id
           FROM stock_quant WHERE''' + domain + '''
           GROUP BY product_id, location_id, lot_id, package_id, partner_id
        ''', args)
        vals = []
        product_ids = []
        for product_line in cr.dictfetchall():
            #replace the None the dictionary by False, because falsy values are tested later on
            for key, value in product_line.items():
                if not value:
                    product_line[key] = False
            product_line['inventory_id'] = inventory.id
            product_line['theoretical_qty'] = product_line['product_qty']
            if product_line['product_id']:
                product = product_obj.browse(cr, uid, product_line['product_id'], context=context)
                product_line['product_uom_id'] = product.uom_id.id
                
                product_ids.append(product.id)
                #THANH: Get product cost to this line
                if product_line['theoretical_qty'] < 0:
                    product_line.update({'freeze_cost': product.standard_price})
            
                #THANH: Get th_qty from stock_move
                if inventory.freeze_date:
                    sql = '''
                        SELECT foo.product_id, 
                        sum(start_onhand_qty) start_onhand_qty
                        From
                            (SELECT
                                stm.product_id,
                                 
                                case when loc1.usage != 'internal' and loc2.usage = 'internal' and stm.date < '%(start_date)s' and loc2.id in (%(loc2)s)
                                then stm.product_qty
                                else
                                case when loc1.usage = 'internal' and loc2.usage != 'internal' and stm.date < '%(start_date)s' and loc1.id in (%(loc1)s)
                                then -1*stm.product_qty 
                                else 0.0 end
                                end start_onhand_qty
                                 
                            FROM stock_move stm 
                                join stock_location loc1 on stm.location_id=loc1.id
                                join stock_location loc2 on stm.location_dest_id=loc2.id
                            WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
                        GROUP BY foo.product_id
                         
                     '''%({
                          'start_date': inventory.freeze_date,
                          'product_id': product.id,
                          'loc2': ','.join(map(str, location_ids)),
                          'loc1': ','.join(map(str, location_ids)),
                          })
                    cr.execute(sql)
                    start_onhand_qty = 0.0
                    for i in cr.dictfetchall():
                        start_onhand_qty += i['start_onhand_qty']
                    if start_onhand_qty != product_line['product_qty']:
                        product_line['product_qty'] = start_onhand_qty
            #THANH: Get th_qty from stock_move
            vals.append(product_line)
        
        #THANH:
        sql = '''
            SELECT foo.product_id product_id, 
            sum(start_onhand_qty) product_qty
            From
                (SELECT
                    stm.product_id,
                    
                    case when loc1.usage != 'internal' and loc2.usage = 'internal' and stm.date < '%(start_date)s' and loc2.id in (%(loc2)s)
                    then stm.product_qty
                    else
                    case when loc1.usage = 'internal' and loc2.usage != 'internal' and stm.date < '%(start_date)s' and loc1.id in (%(loc1)s)
                    then -1*stm.product_qty 
                    else 0.0 end
                    end start_onhand_qty
                    
                FROM stock_move stm 
                    join stock_location loc1 on stm.location_id=loc1.id
                    join stock_location loc2 on stm.location_dest_id=loc2.id
                WHERE stm.state= 'done' and stm.product_id not in (%(product_ids)s))foo
            GROUP BY foo.product_id
            HAVING sum(start_onhand_qty) <> 0.0
         '''%({
              'start_date': inventory.freeze_date,
              'loc2': ','.join(map(str, location_ids)),
              'loc1': ','.join(map(str, location_ids)),
              'product_ids': ','.join(map(str, product_ids)),
              })
        cr.execute(sql)
        for product_line in cr.dictfetchall():
            product_qty = product_line['product_qty']
            product_line['inventory_id'] = inventory.id
            product_line['theoretical_qty'] = product_qty
            product_line['product_qty'] = product_qty
            product_line['location_id'] = inventory.location_id.id
            product_line['prod_lot_id'] = False
            product_line['package_id'] = False 
            product_line['partner_id'] = False 
            if product_line['product_id']:
                product = product_obj.browse(cr, uid, product_line['product_id'], context=context)
                product_line['product_uom_id'] = product.uom_id.id
            
                #THANH: Get product cost to this line
                if product_line['theoretical_qty'] < 0:
                    product_line.update({'freeze_cost': product.standard_price})
            vals.append(product_line)
        return vals
    
    def onchange_product(self, cr, uid, ids, search_product_ean):
        if not ids:
            return {}
        value = {}
             
        inventory_line_pool = self.pool.get('stock.inventory.line')
        domain = []
        domain.append(('inventory_id','=',ids[0]))
        if search_product_ean:
            domain.append('|')
            domain.append('|')
            domain.append(('product_id.barcode','ilike',search_product_ean))
            domain.append(('product_id.name','ilike',search_product_ean))
            domain.append(('product_id.default_code','ilike',search_product_ean))
        if domain:
            line_ids = inventory_line_pool.search(cr, uid, domain)
            value = {'line_ids':line_ids}
        return {'value':value}

class stock_inventory_line(osv.osv):
    _inherit = "stock.inventory.line"
    
    def _get_adjust_qty(self,cr,uid,ids, field_name, arg, context=None):
        res ={}
        cost_item = 0
        for line in self.browse(cr,uid,ids,context=context):
            res[line.id] = {
                            'adjust_quantity': 0,
                            'adjust_value': 0,
                            }
            adjust = line.theoretical_qty - line.product_qty
            if adjust == 0.0:
                continue
            cost_item = line.freeze_cost
            if adjust >0:
                res[line.id]['adjust_quantity'] = adjust
                res[line.id]['adjust_value'] = round(adjust * cost_item,6)
            else:
                res[line.id]['adjust_quantity'] = adjust 
                res[line.id]['adjust_value'] = round(adjust *(-1) * cost_item,6)
        return res
    
    def _get_theoretical_qty(self, cr, uid, ids, name, args, context=None):
        res = {}
        quant_obj = self.pool["stock.quant"]
        uom_obj = self.pool["product.uom"]
        for line in self.browse(cr, uid, ids, context=context):
            quant_ids = self._get_quants(cr, uid, line, context=context)
            quants = quant_obj.browse(cr, uid, quant_ids, context=context)
            tot_qty = sum([x.qty for x in quants])
            
            #THANH: Get th_qty from stock_move
            if line.inventory_id.freeze_date:
                sql = '''
                    SELECT foo.product_id, 
                    sum(start_onhand_qty) start_onhand_qty
                    From
                        (SELECT
                            stm.product_id,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and stm.date < '%(start_date)s' and loc2.id=%(loc2)s
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and stm.date < '%(start_date)s' and loc1.id=%(loc1)s
                            then -1*stm.product_qty 
                            else 0.0 end
                            end start_onhand_qty
                            
                        FROM stock_move stm 
                            join stock_location loc1 on stm.location_id=loc1.id
                            join stock_location loc2 on stm.location_dest_id=loc2.id
                        WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
                    GROUP BY foo.product_id
                    
                 '''%({
                      'start_date': line.inventory_id.freeze_date,
                      'product_id': line.product_id.id,
                      'loc2': line.location_id.id,
                      'loc1': line.location_id.id,
                      })
                cr.execute(sql)
                start_onhand_qty = 0.0
                for i in cr.dictfetchall():
                    start_onhand_qty += i['start_onhand_qty']
                if start_onhand_qty != tot_qty:
                    tot_qty = start_onhand_qty
            #THANH: Get th_qty from stock_move
            
            if line.product_uom_id and line.product_id.uom_id.id != line.product_uom_id.id:
                tot_qty = uom_obj._compute_qty_obj(cr, uid, line.product_id.uom_id, tot_qty, line.product_uom_id, context=context)
            res[line.id] = tot_qty
        return res
    
    _columns = {
        'move_id':fields.many2one('stock.move','Move id'),
        'freeze_cost': fields.float('Freeze Cost', readonly=False, digits=(16,6)),
        'adjust_quantity': fields.function(_get_adjust_qty, readonly=True, string='Adjust Quantity', type ='float', multi='pro_info'), 
        'adjust_value': fields.function(_get_adjust_qty, readonly=True, string='Adjust Value', type ='float', multi='pro_info'),
        
        'theoretical_qty': fields.function(_get_theoretical_qty, type='float', digits_compute=dp.get_precision('Product Unit of Measure'),
                                           store={'stock.inventory.line': (lambda self, cr, uid, ids, c={}: ids, ['location_id', 'product_id', 'package_id', 'product_uom_id', 'company_id', 'prod_lot_id', 'partner_id'], 20),},
                                           readonly=True, string="Theoretical Quantity"),
    }
    
    _defaults = {
        #THANH: Always set it default = False
        'product_uom_id': False,
    }
        
    def _get_quants(self, cr, uid, line, context=None):
        quant_obj = self.pool["stock.quant"]
        dom = [('in_date', '<=', line.inventory_id.freeze_date),('company_id', '=', line.company_id.id), ('location_id', '=', line.location_id.id), ('lot_id', '=', line.prod_lot_id.id),
                        ('product_id','=', line.product_id.id), ('owner_id', '=', line.partner_id.id), ('package_id', '=', line.package_id.id)]
        quants = quant_obj.search(cr, uid, dom, context=context)
        return quants
    
    def _resolve_inventory_line(self, cr, uid, inventory_line, context=None):
        stock_move_obj = self.pool.get('stock.move')
        quant_obj = self.pool.get('stock.quant')
        diff = inventory_line.theoretical_qty - inventory_line.product_qty
        if not diff:
            return
        #each theorical_lines where difference between theoretical and checked quantities is not 0 is a line for which we need to create a stock move
        vals = {
            'name': _('INV:') + (inventory_line.inventory_id.name or ''),
            'product_id': inventory_line.product_id.id,
            'product_uom': inventory_line.product_uom_id.id,
            'date': inventory_line.inventory_id.date,
            'company_id': inventory_line.inventory_id.company_id.id,
            'inventory_id': inventory_line.inventory_id.id,
            'state': 'confirmed',
            'restrict_lot_id': inventory_line.prod_lot_id.id,
            'restrict_partner_id': inventory_line.partner_id.id,
         }
        inventory_location_id = inventory_line.product_id.property_stock_inventory.id
        
        #Thanh: Change the way to get destination locationand update stock move date done
        vals.update({'date': inventory_line.inventory_id.freeze_date,
                     'price_unit': inventory_line.freeze_cost})
        if inventory_line.inventory_id.picking_type_id and inventory_line.inventory_id.picking_type_id.default_location_dest_id:
            inventory_location_id = inventory_line.inventory_id.picking_type_id.default_location_dest_id.id
        #Thanh: Change the way to get destination location
        
        if diff < 0:
            #found more than expected
            vals['location_id'] = inventory_location_id
            vals['location_dest_id'] = inventory_line.location_id.id
            vals['product_uom_qty'] = -diff
        else:
            #found less than expected
            vals['location_id'] = inventory_line.location_id.id
            vals['location_dest_id'] = inventory_location_id
            vals['product_uom_qty'] = diff
        move_id = stock_move_obj.create(cr, uid, vals, context=context)
        move = stock_move_obj.browse(cr, uid, move_id, context=context)
        if diff > 0:
            domain = [('qty', '>', 0.0), ('package_id', '=', inventory_line.package_id.id), ('lot_id', '=', inventory_line.prod_lot_id.id), ('location_id', '=', inventory_line.location_id.id)]
            preferred_domain_list = [[('reservation_id', '=', False)], [('reservation_id.inventory_id', '!=', inventory_line.inventory_id.id)]]
            quants = quant_obj.quants_get_preferred_domain(cr, uid, move.product_qty, move, domain=domain, preferred_domain_list=preferred_domain_list)
            quant_obj.quants_reserve(cr, uid, quants, move, context=context)
        elif inventory_line.package_id:
            stock_move_obj.action_done(cr, uid, move_id, context=context)
            quants = [x.id for x in move.quant_ids]
            quant_obj.write(cr, uid, quants, {'package_id': inventory_line.package_id.id}, context=context)
            res = quant_obj.search(cr, uid, [('qty', '<', 0.0), ('product_id', '=', move.product_id.id),
                                    ('location_id', '=', move.location_dest_id.id), ('package_id', '!=', False)], limit=1, context=context)
            if res:
                for quant in move.quant_ids:
                    if quant.location_id.id == move.location_dest_id.id: #To avoid we take a quant that was reconcile already
                        quant_obj._quant_reconcile_negative(cr, uid, quant, move, context=context)
        return move_id
    
    def onchange_createline(self, cr, uid, ids, location_id=False, product_id=False, uom_id=False, package_id=False, prod_lot_id=False, partner_id=False, company_id=False, context=None):
        quant_obj = self.pool["stock.quant"]
        uom_obj = self.pool["product.uom"]
        res = {'value': {}}
        # If no UoM already put the default UoM of the product
        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            #THANH: Always get product uom
            res['value']['product_uom_id'] = product.uom_id.id
#             uom = self.pool['product.uom'].browse(cr, uid, uom_id, context=context)
#             if product.uom_id.category_id.id != uom.category_id.id:
#                 res['value']['product_uom_id'] = product.uom_id.id
#                 res['domain'] = {'product_uom_id': [('category_id','=',product.uom_id.category_id.id)]}
#                 uom_id = product.uom_id.id

        # Calculate theoretical quantity by searching the quants as in quants_get
        if product_id and location_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            if not company_id:
                company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
            
            dom = [('company_id', '=', company_id), ('location_id', '=', location_id), ('lot_id', '=', prod_lot_id),
                        ('product_id','=', product_id), ('owner_id', '=', partner_id), ('package_id', '=', package_id)]
            
            #THANH: Add filter by freeze_date
            if context.get('freeze_date',False):
                dom.append(('in_date', '<=', context['freeze_date']))
                
            quants = quant_obj.search(cr, uid, dom, context=context)
            th_qty = sum([x.qty for x in quant_obj.browse(cr, uid, quants, context=context)])
            
            #THANH: Get th_qty from stock_move
            if context.get('freeze_date',False):
                sql = '''
                    SELECT foo.product_id, 
                    sum(start_onhand_qty) start_onhand_qty
                    From
                        (SELECT
                            stm.product_id,
                            
                            case when loc1.usage != 'internal' and loc2.usage = 'internal' and stm.date < '%(start_date)s' and loc2.id=%(loc2)s
                            then stm.product_qty
                            else
                            case when loc1.usage = 'internal' and loc2.usage != 'internal' and stm.date < '%(start_date)s' and loc1.id=%(loc1)s
                            then -1*stm.product_qty 
                            else 0.0 end
                            end start_onhand_qty
                            
                        FROM stock_move stm 
                            join stock_location loc1 on stm.location_id=loc1.id
                            join stock_location loc2 on stm.location_dest_id=loc2.id
                        WHERE stm.state= 'done' and stm.product_id=%(product_id)s)foo
                    GROUP BY foo.product_id
                    
                 '''%({
                      'start_date': context['freeze_date'],
                      'product_id': product.id,
                      'loc2': location_id,
                      'loc1': location_id,
                      })
                cr.execute(sql)
                start_onhand_qty = 0.0
                for i in cr.dictfetchall():
                    start_onhand_qty += i['start_onhand_qty']
                if start_onhand_qty != th_qty:
                    th_qty = start_onhand_qty
            #THANH: Get th_qty from stock_move
            
            if product_id and uom_id and product.uom_id.id != uom_id:
                th_qty = uom_obj._compute_qty(cr, uid, product.uom_id.id, th_qty, uom_id)
            res['value']['theoretical_qty'] = th_qty
            
            #THANH: Get standard price for th_qty <0
            if th_qty <= 0:
                res['value']['freeze_cost'] = product.standard_price
        return res
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
