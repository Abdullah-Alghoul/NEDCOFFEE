# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
{
	"name" : "General Payroll",
	"version" : "7.0",
	'author': 'Le Truong Thanh <thanh.lt1689@gmail.com>',
    'category': 'BESCO',
	"description" : """
	""",
	"depends" : ["hr_payroll", "hr_overtime", 'general_hr', "general_hr_holidays", "general_hr_contract"],
	"update_xml" : [
 		'security/hr_security.xml',
		'security/ir.model.access.csv',
 		'wizard/report_payrolls_view.xml',
 		'wizard/report_payslips_view.xml',
 		'wizard/report_bank.xml',
 		'wizard/report_general_payslip.xml',
 		
 		'report/template_payroll_view.xml',
 		'report/template_payslip_officier_view.xml',
 		'report/template_payslip_worker_view.xml',
 		'report/template_payslip_manager_view.xml',
 		'report/template_bank_document_exim.xml',
 		'report/template_bank_payroll_exim.xml',
 		'report/template_bank_document_tech.xml',
 		'report/template_bank_payroll_tech.xml',
 		'report/general_payslip_report.xml',
 		
 		
 		'data/hr_payroll_data.xml',
 		
 		'hr_overtime_data.xml',
		'hr_advance_payment_view.xml',
		'hr_insurance_book_view.xml',
		'hr_overtime_view.xml',
		'hr_contract_view.xml',
		'hr_payroll_view.xml',
		'hr_view.xml'
 		
 		
	],
	"active": False,
	"installable": True,

}
