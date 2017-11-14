# -*- coding: utf-8 -*-

import time
from report import report_sxw
import pooler
from osv import osv
from tools.translate import _
import random
from datetime import datetime
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"
import tools
from osv import fields, osv


class analysis_hr_expense(osv.osv):
    _name = "analysis.hr.expense"
    _description = "Analysis Hr Expense"
    _auto = False
    _columns = {
            'months':fields.selection([
                        ('1', '1'),
                        ('2', '2'),
                        ('3', '3'),
                        ('4', '4'),
                        ('5', '5'),
                        ('6', '6'),
                        ('7', '7'),
                        ('8', '8'),
                        ('9', '9'),
                        ('10', '10'),
                        ('11', '11'),
                        ('12', '12'),
                        ], 'Month', readonly=True),
            'years':fields.char('years'),
            'days':fields.char('Day'),
            'type':fields.selection([
                        ('advance', 'Advance'),
                        ('expense', 'Expense'),
                        ], 'Type', readonly=True),
                
            'state':fields.selection([
                    ('draft', 'New'),
                    ('cancelled', 'Refused'),
                    ('confirm', 'Waiting Approval'),
                    ('accepted', 'Manager Approved'),
                    ('head_accepted', 'Head Approved'),
                    ('done', 'Waiting Payment'),
                    ('paid', 'Paid'),
                    ], 'Status', readonly=True),
                
            'employee_id':fields.many2one('hr.employee', 'Employee', readonly=True, states={'draft': [('readonly', False)]}),
            'department_id':fields.many2one('hr.department', 'Department', readonly=True, states={'draft': [('readonly', False)]}),
            'date_value':fields.date('Date'),
            'product_id':fields.many2one('product.product', 'Expense Type'),
            'description':fields.char('Description', size=128),
            'ref':fields.char('ref', size=256),
            'amount':fields.float('Amount'),
    }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'analysis_hr_expense')
        cr.execute("""
        CREATE or REPLACE view analysis_hr_expense as 
        (
            SELECT ROW_NUMBER() OVER() id,* FROM
            (
                SELECT date_part('month',date_value)::varchar months,date_part('years',date_value) years,
                date_part('day',date_value)||'-'||date_part('month',date_value)||'-'||date_part('years',date_value) days,
                    type,state,employee_id,department_id,date_value,product_id,description,ref,unit_amount * unit_quantity amount
                FROM 
                    hr_expense_line hr_line join hr_expense_expense hr on hr_line.expense_id = hr.id
                WHERE  type = 'expense')x
        )
        """)
analysis_hr_expense()
