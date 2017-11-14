odoo.define('web_printscreen_zb.web_printscreen_zb', function (require) {
	"use strict";
	
    var core = require('web.core');
	var QWeb = core.qweb;
	var _t = core._t;
//	var WebClient = require('web.WebClient');
	var ControlPanel = require('web.ControlPanel');
//	var ControlPanelMixin = require('web.ControlPanelMixin');
	var ListView = require('web.ListView');
	var formats = require('web.formats');
	var Model = require('web.DataModel');
	
	ListView.include({
//		events: {
//	        "click .oe_list_button_import_excel": "export_to_excel('excel')",
//	    },
	    
//		start:function(){
//            var result = this._super();
//            this.$(".oe_list_button_import_excel").click(function(event){self.export_to_excel("excel")});
////            this.$(".oe_list_button_import_excel").unbind('click').click(function(event){self.export_to_excel("excel")})
//            this.$(".oe_list_button_import_pdf").unbind('click').click(function(event){self.export_to_excel("pdf")})
//            return result;
//		},
		
		render_buttons: function($node) {
			var result = this._super($node);
			var self = this;
			
			this.$buttons.find('.oe_list_button_import_excel').click(function(event){self.export_to_excel("excel")});
			this.$buttons.find('.oe_list_button_import_pdf').click(function(event){self.export_to_excel("pdf")});
			
			return result
		},
		
        export_to_excel: function(export_type) {
            var self = this
            var export_type = export_type
            var view = this.getParent()
            // Find Header Element
            var header_eles = self.$el.find('.oe_list_header_columns')
            var header_name_list = []
            $.each(header_eles,function(){
                var $header_ele = $(this)
                var header_td_elements = $header_ele.find('th')
                $.each(header_td_elements,function(){
                	var $header_td = $(this)
                    var text = $header_td.text().trim() || ""
                    var data_id = $header_td.attr('data-id')
                    if (text && !data_id){
                        data_id = 'group_name'
                    }
                    header_name_list.push({'header_name': text.trim(), 'header_data_id': data_id})
                   // }
                });
            });
            
            //Find Data Element
            var data_eles = self.$el.find('.oe_list_content > tbody > tr')
            var export_data = []
            $.each(data_eles,function(){
            	var data = []
            	var $data_ele = $(this)
                var is_analysis = false
                if ($data_ele.text().trim()){
                //Find group name
	                var group_th_eles = $data_ele.find('th')
	                $.each(group_th_eles,function(){
	                	var $group_th_ele = $(this)
	                    var text = $group_th_ele.text().trim() || ""
	                    var is_analysis = true
	                    data.push({'data': text, 'bold': true})
	                });
	                var data_td_eles = $data_ele.find('td')
	                $.each(data_td_eles,function(){
	                	var $data_td_ele = $(this)
	                    var text = $data_td_ele.text().trim() || ""
	                    if ($data_td_ele && $data_td_ele[0].classList.contains('oe_number') && !$data_td_ele[0].classList.contains('oe_list_field_float_time')){
	                        text = text.replace('%', '')
	                        if (isNaN(Number(text.substr(text.length -2,text.length))))
	                        	text = text.substring(0, text.length - 2)
	                        text = formats.parse_value(text, { type:"float" })
	                        data.push({'data': text || "", 'number': true})
	                    }
	                    else{
	                        data.push({'data': text})
	                    }
	                });
	                export_data.push(data)
                }
            });
            
            //Find Footer Element
            
            var footer_eles = self.$el.find('.oe_list_content > tfoot> tr')
            $.each(footer_eles,function(){
            	var data = []
            	var $footer_ele = $(this)
                var footer_td_eles = $footer_ele.find('td')
                $.each(footer_td_eles,function(){
                	var $footer_td_ele = $(this)
                    var text = $footer_td_ele.text().trim() || ""
                    if ($footer_td_ele && $footer_td_ele[0].classList.contains('oe_number')){
                    	if (isNaN(Number(text.substr(text.length -2,text.length))))
                        	text = text.substring(0, text.length - 2)
                        text = formats.parse_value(text, { type:"float" })
                        data.push({'data': text || "", 'bold': true, 'number': true})
                    }
                    else{
                        data.push({'data': text, 'bold': true})
                    }
                });
                export_data.push(data)
            });
            
            //Export to excel
            $.blockUI();
            if (export_type === 'excel'){
                 view.session.get_file({
                     url: '/web/export/zb_excel_export',
                     data: {data: JSON.stringify({
                            model : view.model,
                            headers : header_name_list,
                            rows : export_data,
                     })},
                     complete: $.unblockUI
                 });
             }
             else{
                console.log(view)
                new Model("res.users").get_func("read")(this.session.uid, ["company_id"]).then(function(res) {
                    new Model("res.company").get_func("read")(res['company_id'][0], ["name"]).then(function(result) {
                        view.session.get_file({
                             url: '/web/export/zb_pdf_export',
                             data: {data: JSON.stringify({
                                    uid: view.session.uid,
                                    model : view.model,
                                    headers : header_name_list,
                                    rows : export_data,
                                    company_name: result['name']
                             })},
                             complete: $.unblockUI
                         });
                    });
                });
             }
        },
    });
	
});
