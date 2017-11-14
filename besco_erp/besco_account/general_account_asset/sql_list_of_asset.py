# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import fields, osv
from openerp import _

class sql_list_of_asset(osv.osv):
    _name = "sql.list.of.asset"
    _auto = False
    
    #For reports
    def get_line(self, cr, date_type, start_date, end_date, asset_types, company_id):
        filter_asset_types = ''
        if asset_types:
            filter_asset_types += ' and aas.category_id in (%(asset_types)s)'%({'asset_types':asset_types,})
        
        asset_date = 'aas.date' #THANH: default filter asset by entry date
        if date_type == 'purchase_date':
            asset_date = 'ai.date_invoice is not null and ai.date_invoice'
        filter_date = ''
        if start_date and end_date:
            filter_date += " and %(asset_date)s between '%(start_date)s' and '%(end_date)s'"%({'asset_date': asset_date,
                                                                                         'start_date': start_date,
                                                                                         'end_date': end_date})
        if start_date and not end_date:
            filter_date += " and %(asset_date)s >= '%(start_date)s'"%({'asset_date': asset_date, 
                                                                       'start_date': start_date})
        if not start_date and end_date:
            #THANH: Can not filter
            return False
        
        sql = _(u'''
            select 
                swh.name warehouse, hd.name dept_name, 
                ai.reference as invoice_number, ai.date_invoice as invoice_date, 
                sale_ai.date_invoice as dispose_date, sale_ai.amount_untaxed as dispose_value, 
                aas.code, aas.name, aas.date using_date, categ.name categ_name,
                aas.value gross_value, (aas.method_number*aas.method_period) number_of_period,
                round((aas.value - coalesce(aas.salvage_value,0.0)) / (aas.method_number*aas.method_period)) value_of_month,
                em.name_related em_name,
                
                case when (aas.state = 'draft') then 'Nháp'::text
                    else case when (aas.state = 'open') then 'Đang hoạt động'::text
                        else case when aas.sale_invoice_id is not null then 'Đã thanh lý'::text
                                else 'Ngừng khấu hao'::text
                                end
                        end 
                    end state
                        
                --(aas.value - aas.salvage_value) hold_value,
                --aas.method_time, aas.method_number, aas.method_period, 
                --aaa.name account_analytic
            from account_asset_asset aas 
                    left join account_asset_category categ on categ.id=aas.category_id
                    left join account_invoice ai on ai.id=aas.invoice_id
                    left join account_invoice sale_ai on sale_ai.id=aas.sale_invoice_id
                    left join stock_warehouse swh on aas.warehouse_id = swh.id
                    left join hr_department hd on aas.department_id = hd.id
                    left join hr_employee em on aas.employee_id = em.id
                  --left join account_analytic_account aaa on aaa.id = aas.account_analytic_id
            where 
                    aas.active=true and aas.company_id= %(company_id)s
                    %(filter_asset_types)s  
                    %(filter_date)s
            order by aas.date, aas.code, aas.name, swh.name, hd.name, categ.name
        ''')
        
        sql = sql%({
                  'filter_asset_types': filter_asset_types,
                  'filter_date': filter_date,
                  'company_id': company_id,
                  })
        cr.execute(sql)
        
        total_gross_value = 0.0
        total_value_of_month = 0.0
        res = {}
        for line in cr.dictfetchall():
            if not res.has_key(line['warehouse']):
                res.update({line['warehouse']:{line['dept_name']: [line]}})
            else:
                if not res[line['warehouse']].has_key(line['dept_name']):
                    res[line['warehouse']].update({line['dept_name']: [line]})
                else:
                    res[line['warehouse']][line['dept_name']].append(line)
                    
            total_gross_value += line['gross_value']
            total_value_of_month += line['value_of_month'] and line['value_of_month'] or 0.0
        return res, total_gross_value, total_value_of_month
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
