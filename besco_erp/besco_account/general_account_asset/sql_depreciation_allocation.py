# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import fields, osv
from openerp import _
from openerp import SUPERUSER_ID

class sql_depreciation_allocation(osv.osv):
    _name = "sql.depreciation.allocation"
    _auto = False
    
    #For reports
    def get_line(self, cr, date_type, show_all, start_date, end_date, asset_types, company_id):
        filter_asset_types = ''
        if asset_types:
            filter_asset_types += ' and aas.category_id in (%(asset_types)s)'%({'asset_types':asset_types,})
            
        asset_date = False #THANH: default filter asset by entry date
        if date_type == 'using_date':
            asset_date = 'aas.date'
        if date_type == 'purchase_date':
#             asset_date = 'ai.date_invoice is not null and ai.date_invoice'
            asset_date = 'coalesce(ai.date_invoice, aas.date)'
        filter_date = ''
        if start_date and end_date and asset_date:
            filter_date += " and %(asset_date)s between '%(start_date)s' and '%(end_date)s'"%({'asset_date': asset_date,
                                                                                     'start_date': start_date, 'end_date': end_date})
        extend_sql = ''
        if date_type == 'depreciation_date':
            if show_all:
                extend_sql = _(u'''
                        union all
                        
                        (select aas.id asset_id, aas.currency_id, rc.name currency_name, 
                            swh.name warehouse, hd.name dept_name, 
                            ai.reference as invoice_number, ai.date_invoice as invoice_date, 
                            sale_ai.date_invoice as dispose_date, coalesce(sale_ai.amount_untaxed,0.0) as dispose_value, 
                            aas.code, aas.name, aas.date using_date, categ.name categ_name,
                            
                            aas.value gross_value, 
                            (aas.value - coalesce(aas.salvage_value,0.0) - aas.value_residual) as acc_depreciation,
                            0.0 as depreciation_value, 
                            aas.value_residual remain_value, 
                            
                            (aas.method_number*aas.method_period) number_of_period,
                            round((aas.value - coalesce(aas.salvage_value,0.0)) / (aas.method_number*aas.method_period)) value_of_month,
                            
                            em.name_related em_name,
                            
                            case when (aas.state = 'draft') then 'Nháp'::text
                                else case when (aas.state = 'open') then 'Đang hoạt động'::text
                                    else case when aas.sale_invoice_id is not null then 'Đã thanh lý'::text
                                            else 'Ngừng khấu hao'::text
                                            end
                                    end 
                                end state
                                    
                        from account_asset_asset aas 
                                left join account_asset_category categ on categ.id=aas.category_id
                                left join account_invoice ai on ai.id=aas.invoice_id
                                left join account_invoice sale_ai on sale_ai.id=aas.sale_invoice_id
                                left join stock_warehouse swh on aas.warehouse_id = swh.id
                                left join hr_department hd on aas.department_id = hd.id
                                left join hr_employee em on aas.employee_id = em.id
                                left join res_currency rc on rc.id = aas.currency_id
                              --left join account_analytic_account aaa on aaa.id = aas.account_analytic_id
                        where 
                            aas.active=true and aas.company_id= %(company_id)s
                            %(filter_asset_types)s  
                            
                            --THANH: get asset has depreciation_date smaller than printed date
                            and aas.id in   (   select distinct adl.asset_id 
                                                from account_asset_depreciation_line adl 
                                                where adl.depreciation_date < '%(start_date)s' 
                                                    and adl.move_check = true
                                            /*
                                            union
                                                select distinct adl.asset_id 
                                                from account_asset_depreciation_line adl 
                                                where adl.depreciation_date between '%(start_date)s' and '%(end_date)s'
                                            */
                                            )
                            and aas.id not in (select distinct adl.asset_id 
                                                from account_asset_depreciation_line adl 
                                                where adl.depreciation_date between '%(start_date)s' and '%(end_date)s')
                            
                        order by swh.name, hd.name, categ.name, aas.date, aas.code, aas.name)
                    ''')
                extend_sql = extend_sql%({
                  'filter_asset_types': filter_asset_types,
                  'start_date': start_date,
                  'end_date': end_date,
                  'company_id': company_id,
                })
                
            sql =_(u'''
            SELECT *
            FROM (
                (select aas.id asset_id, aas.currency_id, rc.name currency_name, 
                    swh.name warehouse, hd.name dept_name, 
                    ai.reference as invoice_number, ai.date_invoice as invoice_date, 
                    sale_ai.date_invoice as dispose_date, coalesce(sale_ai.amount_untaxed,0.0) as dispose_value, 
                    aas.code, aas.name, aas.date using_date, categ.name categ_name,
                    
                    coalesce(dep1.gross_value, aas.value) as gross_value,
                    coalesce(dep1.acc_depreciation,(aas.value - coalesce(aas.salvage_value,0.0) - aas.value_residual)) as acc_depreciation,
                    coalesce(dep.depreciation_value,0.0) as depreciation_value, 
                    coalesce(dep1.remain_value,aas.value_residual) as remain_value, 
                    
                    (aas.method_number*aas.method_period) number_of_period,
                    --round(coalesce(dep1.acc_depreciation,(aas.value - coalesce(aas.salvage_value,0.0) - aas.value_residual)) / (aas.method_number*aas.method_period)) value_of_month,
                    round((aas.value - coalesce(aas.salvage_value,0.0)) / (aas.method_number*aas.method_period)) value_of_month,
                    
                    em.name_related em_name,
                    
                    case when (aas.state = 'draft') then 'Nháp'::text
                        else case when (aas.state = 'open') then 'Đang hoạt động'::text
                            else case when aas.sale_invoice_id is not null then 'Đã thanh lý'::text
                                    else 'Ngừng khấu hao'::text
                                    end
                            end 
                        end state
                            
                from account_asset_asset aas 
                        left join account_asset_category categ on categ.id=aas.category_id
                        left join account_invoice ai on ai.id=aas.invoice_id
                        left join account_invoice sale_ai on sale_ai.id=aas.sale_invoice_id
                        left join stock_warehouse swh on aas.warehouse_id = swh.id
                        left join hr_department hd on aas.department_id = hd.id
                        left join hr_employee em on aas.employee_id = em.id
                        left join res_currency rc on rc.id = aas.currency_id
                        
                    join (--THANH: show future depreciation
                        select adl.asset_id, 
                        
                        --sum(adl.amount) depreciation_value
                        sum(case when (adl.move_check = true) then adl.amount
                            else 0.0 end) depreciation_value
                
                        from account_asset_depreciation_line adl 
                        where (adl.depreciation_date between '%(start_date)s' and '%(end_date)s' 
                                --and adl.move_check = true
                            )
                        group by adl.asset_id
                    ) dep on aas.id = dep.asset_id
                    
                    join (--THANH: get asset information
                        select adl.asset_id, adl.value gross_value, 
                            --adl.depreciated_value acc_depreciation, adl.remaining_value remain_value
                            
                            case when (adl.move_check = true) then adl.depreciated_value
                            else round((adl.depreciated_value - adl.amount)::numeric, 5) end acc_depreciation,
            
                            case when (adl.move_check = true) then adl.remaining_value
                            else adl.remaining_value + adl.amount end remain_value
                
                        from account_asset_depreciation_line adl 
                            join (select asset_id, max(depreciation_date) maxDate
                                    from account_asset_depreciation_line
                                    where depreciation_date between '%(start_date)s' and '%(end_date)s'
                                    group by asset_id) adl1 ON adl.asset_id = adl1.asset_id AND adl.depreciation_date = adl1.maxDate
                        where adl.depreciation_date between '%(start_date)s' and '%(end_date)s' 
                        --and adl.move_check = true
                    ) dep1 on aas.id = dep1.asset_id
                    
                    --left join account_analytic_account aaa on aaa.id = aas.account_analytic_id
                where 
                        aas.active=true and aas.company_id= %(company_id)s
                        %(filter_asset_types)s 
                order by swh.name, hd.name, categ.name, aas.date, aas.code, aas.name)
                
                %(extend_sql)s
            ) v
            order by using_date, code, name, warehouse, dept_name, categ_name
            ''')
        else:
            sql = _(u'''select aas.id asset_id, aas.currency_id, rc.name currency_name, 
                        swh.name warehouse, hd.name dept_name, 
                        ai.reference as invoice_number, ai.date_invoice as invoice_date, 
                        sale_ai.date_invoice as dispose_date, coalesce(sale_ai.amount_untaxed,0.0) as dispose_value, 
                        aas.code, aas.name, aas.date using_date, categ.name categ_name,
                        
                        aas.value gross_value, 
                        (aas.value - coalesce(aas.salvage_value,0.0) - aas.value_residual) as acc_depreciation,
                        0.0 as depreciation_value, 
                        aas.value_residual remain_value, 
                        
                        (aas.method_number*aas.method_period) number_of_period,
                        round((aas.value - coalesce(aas.salvage_value,0.0)) / (aas.method_number*aas.method_period)) value_of_month,
                        
                        em.name_related em_name,
                        
                        case when (aas.state = 'draft') then 'Nháp'::text
                            else case when (aas.state = 'open') then 'Đang hoạt động'::text
                                else case when aas.sale_invoice_id is not null then 'Đã thanh lý'::text
                                        else 'Ngừng khấu hao'::text
                                        end
                                end 
                            end state
                                
                    from account_asset_asset aas 
                            left join account_asset_category categ on categ.id=aas.category_id
                            left join account_invoice ai on ai.id=aas.invoice_id
                            left join account_invoice sale_ai on sale_ai.id=aas.sale_invoice_id
                            left join stock_warehouse swh on aas.warehouse_id = swh.id
                            left join hr_department hd on aas.department_id = hd.id
                            left join hr_employee em on aas.employee_id = em.id
                            left join res_currency rc on rc.id = aas.currency_id
                          --left join account_analytic_account aaa on aaa.id = aas.account_analytic_id
                    where 
                            aas.active=true and aas.company_id= %(company_id)s
                            %(filter_asset_types)s  
                            %(filter_date)s
                    order by aas.date, aas.code, aas.name, swh.name, hd.name, categ.name
                ''')
        sql = sql%({
                  'filter_asset_types': filter_asset_types,
                  'start_date': start_date,
                  'end_date': end_date,
                  'extend_sql': extend_sql,
                  'filter_date': filter_date,
                  'company_id': company_id,
                  })
        cr.execute(sql)
        
        depreciation_value = 0.0
        acc_depreciation = 0.0
        remain_value = 0.0
#         total_second_gross_value  = 0.0
#         total_second_depreciation_value = 0.0
#         total_second_acc_depreciation = 0.0
#         total_second_remain_value = 0.0
        currency_obj = self.pool.get('res.currency')
        res = {}
        for line in cr.dictfetchall():
            currency = currency_obj.browse(cr, SUPERUSER_ID, line['currency_id'])
            line.update({'decimal_places': currency.round_decimal_places})
#             second_gross_value = line['gross_value']
#             second_depreciation_value = line['depreciation_value']
#             second_acc_depreciation = line['acc_depreciation']
#             second_remain_value = line['remain_value']
#             second_rate = 1
#             
#             if line['currency_id']:
#                 currency = currency_obj.browse(self.cr, self.uid, line['currency_id'])
#                 if self.company.second_currency_id and line['currency_id'] != self.company.second_currency_id.id:
#                     second_gross_value = currency.with_context({'date':line['date_invoice']}).compute(line['amount_untaxed'], self.company.second_currency_id)
#                     second_depreciation_value = line['depreciation_value']
#                     second_acc_depreciation = line['acc_depreciation']
#                     second_remain_value = line['remain_value']
#                     second_rate = self.company.second_currency_id.round(second_amount_untaxed / line['amount_untaxed'])
                        
            if not res.has_key(line['warehouse']):
                res.update({line['warehouse']:{line['dept_name']: [line]}})
            else:
                if not res[line['warehouse']].has_key(line['dept_name']):
                    res[line['warehouse']].update({line['dept_name']: [line]})
                else:
                    res[line['warehouse']][line['dept_name']].append(line)
            
            depreciation_value += line['depreciation_value']# and line['depreciation_value'] or 0.0
            acc_depreciation += line['acc_depreciation']# and line['acc_depreciation'] or 0.0
            remain_value += line['remain_value']# and line['remain_value'] or 0.0
#             total_second_gross_value += second_gross_value
#             total_second_depreciation_value = second_depreciation_value
#             total_second_acc_depreciation = second_acc_depreciation
#             total_second_remain_value = second_remain_value
        return res, depreciation_value, acc_depreciation, remain_value\
#             , total_second_gross_value, total_second_depreciation_value, total_second_acc_depreciation, total_second_remain_value

