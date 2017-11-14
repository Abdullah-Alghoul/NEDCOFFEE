odoo.define('web_search_range_date', function (require) {
	"use strict";
	
	var core = require('web.core');
	var ViewManager = require('web.ViewManager');
	var ControlPanel = require('web.ControlPanel');
	var FormView = require('web.FormView');
	var SearchView = require('web.SearchView');
	var QWeb = core.qweb;
	var Model = require('web.DataModel');
	var Widget = require('web.Widget');
	
	var session = require('web.session');
	var pyeval = require('web.pyeval');
	var FavoriteMenu = require('web.FavoriteMenu');
	var _t = core._t;
	
	//THANH: Remove search range date when saving Filter
	FavoriteMenu.include({
		save_favorite: function () {
	        var self = this,
	            filter_name = this.$inputs[0].value,
	            default_filter = this.$inputs[1].checked,
	            shared_filter = this.$inputs[2].checked;
	        if (!filter_name.length){
	            this.do_warn(_t("Error"), _t("Filter name is required."));
	            this.$inputs.first().focus();
	            return;
	        }
	        if (_.chain(this.filters)
	                .pluck('name')
	                .contains(filter_name).value()) {
	            this.do_warn(_t("Error"), _t("Filter with same name already exists."));
	            this.$inputs.first().focus();
	            return;
	        }
	        var search = this.searchview.build_search_data(),
	            view_manager = this.findAncestor(function (a) {
	                // HORRIBLE HACK. PLEASE SAVE ME FROM MYSELF (BUT IN A PAINLESS WAY IF POSSIBLE)
	                return 'active_view' in a;
	            }),
	            view_context = view_manager ? view_manager.active_view.controller.get_context() : {},
	            results = pyeval.sync_eval_domains_and_contexts({
	                domains: search.domains,
	                contexts: search.contexts.concat(view_context || []),
	                group_by_seq: search.groupbys || [],
	            });
	        if (!_.isEmpty(results.group_by)) {
	            results.context.group_by = results.group_by;
	        }
	        // Don't save user_context keys in the custom filter, otherwise end
	        // up with e.g. wrong uid or lang stored *and used in subsequent
	        // reqs*
	        var ctx = results.context;
	        _(_.keys(session.user_context)).each(function (key) {
	            delete ctx[key];
	        });
	        
	        //THANH: Remove domain for field date or datetime from search active object
	        if (results.domain.length && self.searchview.fields_selection){
	        	var fields_selection = self.searchview.fields_selection
	        	for (var i = 0; i < fields_selection.length; i++) {
	        		for (var j = 0; j < results.domain.length; j++) {
	        			if (results.domain[j][0] == fields_selection[0].name){
	        				results.domain.splice(j,1);
	        				j = j - 1;
	                	};
	        		}
	            };
	        }
	        //THANH: Remove domain for field date or datetime from search active object
	        
	        var filter = {
	            name: filter_name,
	            user_id: shared_filter ? false : session.uid,
	            model_id: this.searchview.dataset.model,
	            context: results.context,
	            domain: results.domain,
	            sort: JSON.stringify(this.searchview.dataset._sort),
	            is_default: default_filter,
	            action_id: this.action_id,
	        };
	        return this.model.call('create_or_replace', [filter]).done(function (id) {
	            filter.id = id;
	            self.toggle_save_menu(false);
	            self.$save_name.find('input').val('').prop('checked', false);
	            self.append_filter(filter);
	            self.toggle_filter(filter, true);
	        });
		}
	});
	
	var format_search_datetime = function(datetime) {
		var yyyy = datetime.getUTCFullYear().toString();
		var mm = (datetime.getUTCMonth()+1).toString(); // getMonth() is zero-based
		var dd  = datetime.getUTCDate().toString();
		
		var HH = datetime.getUTCHours().toString();
		var MM = datetime.getUTCMinutes().toString();
		var SS  = datetime.getUTCSeconds().toString();
		
		return yyyy + '-' + (mm[1] ? mm:"0" + mm[0]) + '-' + (dd[1] ? dd:"0" + dd[0]) + ' ' + HH + ':' + MM + ':' + SS// padding
	};
	
	var format_search_date = function(date) {
		var yyyy = date.getFullYear().toString();
		var mm = (date.getMonth()+1).toString(); // getMonth() is zero-based
		var dd  = date.getDate().toString();
		
		return yyyy + '-' + (mm[1] ? mm:"0" + mm[0]) + '-' + (dd[1] ? dd:"0" + dd[0])// padding
	};
	
	SearchView.include({
        search_date_range: function(){
            var filter_domain = [];
            var self = this;
            
            var from_date = self.from_date
            var to_date = self.to_date
            
            if (self.field_type == "datetime"){
            	if (self.from_date){
            		from_date = from_date.split(' ')
        			from_date = from_date[0].split('/').reverse().join('/') + ' ' + from_date[1]
	            	from_date = new Date(from_date);
	    			from_date = format_search_datetime(from_date);
            	}
            	if (self.to_date){
            		to_date = to_date.split(' ')
        			to_date = to_date[0].split('/').reverse().join('/') + ' ' + to_date[1]
            		to_date = new Date(to_date);
            		to_date = format_search_datetime(to_date);
            	}
            }else{
            	if (self.from_date){
            		from_date = from_date.split('/').reverse().join('/')
	            	from_date = new Date(from_date);
	    			from_date = format_search_date(from_date);
            	}
            	if (self.to_date){
            		to_date = to_date.split('/').reverse().join('/')
            		to_date = new Date(to_date);
            		to_date = format_search_date(to_date);
            	}
            }
            
            if (self.field_name_selection && from_date) {
            	if (to_date) {
	                filter_domain.push("[('" + self.field_name_selection + "', '>=', '" + from_date + "'),"+"('" + self.field_name_selection + "', '<=', '" + to_date + "')]")
	            }else{
	            	filter_domain.push("[('" + self.field_name_selection + "', '=', '" + from_date + "')]")
	            }
            };
            
            if (filter_domain.length) {
                var filter_or_domain = [];
                for (var i = 0; i < filter_domain.length-1; i++) {
                    filter_or_domain.push("['|']");
                }
                return filter_or_domain.concat(filter_domain || []);
            }
            return filter_domain;
        },
        build_search_data: function () {
            var result = this._super();
            var filter_domain = this.search_date_range();
            
            if (filter_domain)
                result['domains'] = filter_domain.concat(result.domains || []);
            return result;
        },
    });
	
	var getDaysInMonth = function(m, y) {
	    return (m === 2) ? (!((y % 4) || (!(y % 100) && (y % 400))) ? 29 : 28) : 30 + ((m + (m >> 3)) & 1);
	}
	
	var SearchRangeDate = Widget.extend(/** @lends instance.web.SearchRangeDate# */{
	    template: "SearchRangeDate",
	    
	    events: {
	        'click button.clear_filter': function (e) {
	        	var SeachViewModel = this.searchview;
	        	$('.search_from_date').val(null);
				$('.search_to_date').val(null);
				
				$(this).toggleClass('enabled');
	        	SeachViewModel.from_date = false;
	        	SeachViewModel.to_date = false;
	            SeachViewModel.do_search();
	        },
	        
	        'change #field_name_selection': function (e) {
	        	var SeachViewModel = this.searchview;
	        	SeachViewModel.field_name_selection = $('#field_name_selection').val();
                for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
                SeachViewModel.from_date =  $(".search_to_date").val();
                SeachViewModel.to_date =  $(".search_from_date").val();
                SeachViewModel.do_search();
	        },
	        
	        'click button.search_range_date': function (e) {
	        	var SeachViewModel = this.searchview;
	        	SeachViewModel.field_name_selection = $('#field_name_selection').val()
	        	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
	        		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
	        			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
	        			break;
	        		}
	        	}
	        	SeachViewModel.from_date = $(".search_from_date").val();
	        	SeachViewModel.to_date = $(".search_to_date").val();
	            SeachViewModel.do_search();
	        },
	        
	        //THANH: Button Search To Day
	        'click button.o_calendar_button_today': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	SeachViewModel.field_name_selection = $('#field_name_selection').val()
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	var d = new Date();
            	var month = d.getMonth()+1;
            	var year = d.getFullYear();
            	var day = d.getDate();
            	if (SeachViewModel.field_type == 'datetime'){
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date + " 00:00:00");
                	$(".search_to_date").val(from_date + " 23:59:59");
            	}else{
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date);
                	$('.search_to_date').val(from_date);
            	}
            	SeachViewModel.from_date = $(".search_from_date").val();
            	SeachViewModel.to_date = $(".search_to_date").val();
                SeachViewModel.do_search();
	        },
	        
	        'click button.o_calendar_button_day': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	//THANH: Button Search To Day
            	SeachViewModel.field_name_selection = $('#field_name_selection').val()
            	$(".o_calendar_button_week").removeClass("activity");
             		$(".o_calendar_button_day").removeClass("activity");
             		$(".o_calendar_button_month").removeClass("activity");
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	var d = new Date();
            	var month = d.getMonth()+1;
            	var year = d.getFullYear();
            	var day = d.getDate();
            	if (SeachViewModel.field_type == 'datetime'){
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date + " 00:00:00");
                	$(".search_to_date").val(from_date + " 23:59:59");
            	}else{
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date);
                	$('.search_to_date').val(from_date);
            	}
            	SeachViewModel.from_date = $(".search_from_date").val();
            	SeachViewModel.to_date = $(".search_to_date").val();
                SeachViewModel.do_search();
                self.calendar_mode = 'mode_day';
	        },
	        
	        'click button.o_calendar_button_week': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	//THANH: Button Search This Week
            	SeachViewModel.field_name_selection = $('#field_name_selection').val()
             		$(".o_calendar_button_day").removeClass("activity");
             		$(".o_calendar_button_month").removeClass("activity");
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	var d = new Date();
            	var month = d.getMonth()+1;
            	var year = d.getFullYear();
            	var first = d.getDate() - d.getDay() + 1;
            	var last = first + 6; // last day is the first day + 6
            	if (SeachViewModel.field_type == 'datetime'){
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date + " 00:00:00");
                	$(".search_to_date").val(to_date + " 23:59:59");
            	}else{
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last < 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date);
                	$('.search_to_date').val(to_date);
            	}
            	SeachViewModel.from_date = $(".search_from_date").val();
            	SeachViewModel.to_date = $(".search_to_date").val();
                SeachViewModel.do_search();
                self.calendar_mode ='mode_week';
	            
	        },
	        
	        'click button.o_calendar_button_month': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	//THANH: Button Search This Month
            	$(".o_calendar_button_week").removeClass("activity");
         		$(".o_calendar_button_day").removeClass("activity");
            	SeachViewModel.field_name_selection = $('#field_name_selection').val()
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	var d = new Date();
            	var month = d.getMonth() + 1;
            	var year = d.getFullYear();
            	var first = '1'
            	var last = getDaysInMonth(month, year)
            	if (SeachViewModel.field_type == 'datetime'){
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	
                	$(".search_from_date").val(from_date + " 00:00:00");
                	$(".search_to_date").val(to_date + " 23:59:59");
            	}else{
            		var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	$(".search_from_date").val(from_date);
                	$('.search_to_date').val(to_date);
            	}
            	SeachViewModel.from_date = $(".search_from_date").val();
            	SeachViewModel.to_date = $(".search_to_date").val();
                SeachViewModel.do_search();
                self.calendar_mode = 'mode_month';
	        },
	        
	        'click button.o_calendar_button_prev': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	//THANH: Button Search Previous Date
            	SeachViewModel.field_name_selection = $('#field_name_selection').val()
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	if ($(".search_from_date").val()){
            		var curr_from_date = $(".search_from_date").val()
                	curr_from_date = curr_from_date.split(' ')
                	if (SeachViewModel.field_type == 'datetime'){
            			curr_from_date = curr_from_date[0].split('/').reverse().join('/') + ' ' + curr_from_date[1]
                	}else{
            			curr_from_date = curr_from_date[0].split('/').reverse().join('/')
                	}
                	var curr_from_date = new Date(curr_from_date);
                	if (self.calendar_mode == "mode_month"){
                		$(".o_calendar_button_week").removeClass("activity");
                		$(".o_calendar_button_day").removeClass("activity");
                		$(".o_calendar_button_month").addClass("activity");
            		    var first_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth()-1, curr_from_date.getDate());
            		    var last_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth(), curr_from_date.getDate()-1);
            		    
            		    var first  = first_date.getDate();
                		var last = last_date.getDate();
        		    	var from_date = (first < 10 ? '0' : '') + first + '/' + ((first_date.getMonth()+1) < 10 ? '0' : '') + (first_date.getMonth()+1) + '/' + first_date.getFullYear();
                    	var to_date = (last < 10 ? '0' : '') + last + '/' + ((last_date.getMonth()+1) < 10 ? '0' : '') + (last_date.getMonth()+1) + '/' + last_date.getFullYear();
            		    if (SeachViewModel.field_type == 'datetime'){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                    	}else{
                        	$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                    	}
                	}
                	if (self.calendar_mode == "mode_week"){
                		$(".o_calendar_button_week").addClass("activity");
                		$(".o_calendar_button_day").removeClass("activity");
                		$(".o_calendar_button_month").removeClass("activity");
            		    var first_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth(), curr_from_date.getDate()-7);
            		    var last_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth(), curr_from_date.getDate()-1);
            		    
            		    var first  = first_date.getDate();
                		var last = last_date.getDate();
            		    var from_date = (first < 10 ? '0' : '') + first + '/' + ((first_date.getMonth()+1) < 10 ? '0' : '') + (first_date.getMonth()+1) + '/' + first_date.getFullYear();
                    	var to_date = (last < 10 ? '0' : '') + last + '/' + ((last_date.getMonth()+1) < 10 ? '0' : '') + (last_date.getMonth()+1) + '/' + last_date.getFullYear();
                    	
            		    if (SeachViewModel.field_type == 'datetime'){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                    	}else{
                        	$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                    	}
                	}
                	if (self.calendar_mode == "mode_day"){
                		$(".o_calendar_button_week").removeClass("activity");
                		$(".o_calendar_button_day").addClass("activity");
                		$(".o_calendar_button_month").removeClass("activity");
                	 	
                		var day = curr_from_date.getDate()
                		curr_from_date.setDate(day - 1);
                		var yyyy = curr_from_date.getFullYear();
                		var month = curr_from_date.getMonth() + 1;
                		var first  = curr_from_date.getDate();
                		var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + yyyy;
                    	var to_date = (first< 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + yyyy;
                    	
                		if (SeachViewModel.field_type == "datetime"){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                		}else{
                			$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                		}
                    }
            	}else{
            		//When range date is empty but click button pre and next first so call filter to day as default
            		var d = new Date();
            		var month = d.getMonth()+1;
            		var year = d.getFullYear();
            		var day = d.getDate();
                	if (SeachViewModel.field_type == 'datetime'){
                    	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                    	$(".search_from_date").val(from_date + " 00:00:00");
                    	$(".search_to_date").val(from_date + " 23:59:59");
                	}else{
                    	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                    	$(".search_from_date").val(from_date);
                    	$('.search_to_date').val(from_date);
                	}
            	}
            	SeachViewModel.from_date = $(".search_from_date").val();
            	SeachViewModel.to_date = $(".search_to_date").val();
                SeachViewModel.do_search();
	        },
	        
	        'click button.o_calendar_button_next': function (e) {
	        	var SeachViewModel = this.searchview;
	        	var self = this;
	        	//THANH: Button Search Next Date
            	SeachViewModel.field_name_selection = $('#field_name_selection').val()
            	for (var i=0; i < SeachViewModel.fields_selection.length; i++){
            		if (SeachViewModel.fields_selection[i].name == SeachViewModel.field_name_selection){
            			SeachViewModel.field_type = SeachViewModel.fields_selection[i].type
            			break;
            		}
            	}
            	
            	if ($(".search_from_date").val()){
            		var curr_from_date = $(".search_from_date").val()
                	curr_from_date = curr_from_date.split(' ')
                	if (SeachViewModel.field_type == 'datetime'){
            			curr_from_date = curr_from_date[0].split('/').reverse().join('/') + ' ' + curr_from_date[1]
                	}else{
            			curr_from_date = curr_from_date[0].split('/').reverse().join('/')
                	}
                	var curr_from_date = new Date(curr_from_date);
                	
                	if (self.calendar_mode == "mode_month"){
                		$(".o_calendar_button_week").removeClass("activity");
                		$(".o_calendar_button_day").removeClass("activity");
                		$(".o_calendar_button_month").addClass("activity");
            		    var first_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth()+1, curr_from_date.getDate());
            		    var last_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth()+2, curr_from_date.getDate()-1);
            		    
            		    var first  = first_date.getDate();
                		var last = last_date.getDate();
        		    	var from_date = (first < 10 ? '0' : '') + first + '/' + ((first_date.getMonth()+1) < 10 ? '0' : '') + (first_date.getMonth()+1) + '/' + first_date.getFullYear();
                    	var to_date = (last < 10 ? '0' : '') + last + '/' + ((last_date.getMonth()+1) < 10 ? '0' : '') + (last_date.getMonth()+1) + '/' + last_date.getFullYear();
            		    if (SeachViewModel.field_type == 'datetime'){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                    	}else{
                        	$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                    	}
                	}
                	if (self.calendar_mode == "mode_week"){
                		$(".o_calendar_button_week").addClass("activity");
                		$(".o_calendar_button_day").removeClass("activity");
                		$(".o_calendar_button_month").removeClass("activity");
            		    var first_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth(), curr_from_date.getDate()+7);
            		    var last_date = new Date(curr_from_date.getFullYear(), curr_from_date.getMonth(), curr_from_date.getDate()+13);
            		    
            		    var first  = first_date.getDate();
                		var last = last_date.getDate();
            		    var from_date = (first < 10 ? '0' : '') + first + '/' + ((first_date.getMonth()+1) < 10 ? '0' : '') + (first_date.getMonth()+1) + '/' + first_date.getFullYear();
                    	var to_date = (last < 10 ? '0' : '') + last + '/' + ((last_date.getMonth()+1) < 10 ? '0' : '') + (last_date.getMonth()+1) + '/' + last_date.getFullYear();
                    	
            		    if (SeachViewModel.field_type == 'datetime'){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                    	}else{
                        	$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                    	}
                	}
                	if (self.calendar_mode == "mode_day"){
                		$(".o_calendar_button_week").removeClass("activity");
                		$(".o_calendar_button_day").addClass("activity");
                		$(".o_calendar_button_month").removeClass("activity");
                	 	
                		var day = curr_from_date.getDate()
                		curr_from_date.setDate(day + 1);
                		var yyyy = curr_from_date.getFullYear();
                		var month = curr_from_date.getMonth() + 1;
                		var first  = curr_from_date.getDate();
                		
                		var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + yyyy;
                    	var to_date = (first< 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + yyyy;
                    	
                		if (SeachViewModel.field_type == "datetime"){
                        	$(".search_from_date").val(from_date + " 00:00:00");
                        	$(".search_to_date").val(to_date + " 23:59:59");
                		}else{
                			$(".search_from_date").val(from_date);
                        	$(".search_to_date").val(to_date);
                		}
                    }
            	}else{
            		//When range date is empty but click button pre and next first so call filter to day as default
            		var d = new Date();
            		var month = d.getMonth()+1;
            		var year = d.getFullYear();
                	var day = d.getDate();
                	if (SeachViewModel.field_type == 'datetime'){
                    	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                    	$(".search_from_date").val(from_date + " 00:00:00");
                    	$(".search_to_date").val(from_date + " 23:59:59");
                	}else{
                    	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                    	$(".search_from_date").val(from_date);
                    	$('.search_to_date').val(from_date);
                	}
            	}
            	SeachViewModel.from_date = $(".search_from_date").val()
            	SeachViewModel.to_date = $(".search_to_date").val()
                SeachViewModel.do_search();
	        },
	    },
	    
	    init: function(parent, options) {
	        this._super(parent);
	        var self = this;
	        this.filter_fields = options.filter_fields;
	        this.default_filter_time = options.default_filter_time;
	        this.searchview = options.searchview;
	        this.calendar_mode = 'mode_day'
	    },
	    
	    start: function() {
	    	var result = this._super();
	    	var self = this;
	    	var SeachViewModel = self.searchview
	    	var default_filter_time = self.default_filter_time;
	    	
	    	//THANH: set format date or datetime for default search field
	    	var first_field = self.filter_fields[0]
            if(first_field.type == "datetime"){
            	self.$('.search_from_date').datetimepicker({
            		format: 'DD/MM/YYYY HH:MM:SS',
                });
            	self.$('.search_to_date').datetimepicker({
            		format: 'DD/MM/YYYY HH:MM:SS',
                });
            }else{
            	$('.search_from_date').datepicker({
            		dateFormat: 'dd/mm/yy',
                });
            	self.$('.search_to_date').datepicker({
            		dateFormat: 'dd/mm/yy',
                });
            };
	    	
            //THANH: set default value for field date
            var d = new Date();
            var month = d.getMonth()+1;
            var year = d.getFullYear();
            if(default_filter_time == 'day'){
            	self.calendar_mode = 'mode_day';
            	if (first_field.type == 'datetime'){
                	var day = d.getDate();
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	self.$(".search_from_date").val(from_date + " 00:00:00");
                	self.$(".search_to_date").val(from_date + " 23:59:59");
            	}else{
                	var month = d.getMonth()+1;
                	var day = d.getDate();
                	var from_date = (day < 10 ? '0' : '') + day + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	self.$(".search_from_date").val(from_date);
                	self.$('.search_to_date').val(from_date);
            	}
            };
            if(default_filter_time == 'week'){
            	self.calendar_mode = 'mode_week';
            	var first = d.getDate() - d.getDay() + 1;
            	var last = first + 6; // last day is the first day + 6
            	
            	if (first_field.type == 'datetime'){
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	
                	self.$(".search_from_date").val(from_date + " 00:00:00");
                	self.$(".search_to_date").val(to_date + " 23:59:59");
            	}else{
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last < 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	self.$(".search_from_date").val(from_date);
                	self.$('.search_to_date').val(to_date);
            	}
            };
            if(default_filter_time == 'month'){
            	self.calendar_mode = 'mode_month';
            	var first = '1'
            	var last = getDaysInMonth(month, year)
            	if (first_field.type == 'datetime'){
                	var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	
                	self.$(".search_from_date").val(from_date + " 00:00:00");
                	self.$(".search_to_date").val(to_date + " 23:59:59");
            	}else{
            		var from_date = (first < 10 ? '0' : '') + first + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	var to_date = (last< 10 ? '0' : '') + last + '/' + (month < 10 ? '0' : '') + month + '/' + year;
                	self.$(".search_from_date").val(from_date);
                	self.$('.search_to_date').val(to_date);
            	}
            };
            
            if (default_filter_time){
            	SeachViewModel.field_type = first_field.type;
            	SeachViewModel.field_name_selection = $('#field_name_selection').val();
	        	SeachViewModel.from_date = self.$(".search_from_date").val();
	        	SeachViewModel.to_date = self.$(".search_to_date").val();
//	            SeachViewModel.do_search();
	        };
	        return result;
	    },
	});
	
    ViewManager.include({
    	start: function() {
            var result = this._super();
            var self = this;
            self.calendar_mode = 'mode_day'
            var SeachViewModel = this.searchview
            var filter_array = [];
            var default_filter_time = null;
            
        	if (self.action && self.action.context.search_by_field_date){
            	filter_array = self.action.context.search_by_field_date;
            }else{
            	if (self.context && self.context.search_by_field_date){
            		filter_array = self.context.search_by_field_date;
            	}
            }
        	
        	if (self.action && self.action.context.default_filter_array){
        		default_filter_time = self.action.context.default_filter_array;
            }else{
            	if (self.context && self.context.default_filter_array){
            		default_filter_time = self.context.default_filter_array;
            	}
            }
            if (filter_array.length && SeachViewModel){
            	SeachViewModel.fields_selection = [];
                self.dataset.call('fields_get', {context: this.dataset.context}).done(function (fields) {
                	$.each(fields, function (name, attribute) {
                        if((attribute.type == "datetime" || attribute.type == "date") && filter_array.indexOf(name)>= 0){
                        	attribute.name = name
                        	SeachViewModel.fields_selection.push(attribute);
                        }
                    })
                    
                    if(SeachViewModel.fields_selection.length){
                    	//Thanh: Revert the field order
                        SeachViewModel.fields_selection.reverse()
                        
                        if ($('#SearchRangeDate').length > 0) {
    	            		// THANH: check exists and destroy it.
                        	$('#SearchRangeDate').remove();
    	        		}
                        
                    	//THANH: render SearchRangeDate template and add to layout
    	            	if ($('#SearchRangeDate').length <= 0) {
    	            		// THANH: check not exists.
    	            		var options = {
	            				filter_fields: SeachViewModel.fields_selection,
	            				default_filter_time: default_filter_time,
	            				searchview: SeachViewModel,
	            	        };
    	            		var searchrangedate = new SearchRangeDate(self, options);
    	            		searchrangedate.insertAfter($(".oe-control-panel"));
    	        		}
                    }
                });
            }
    	},
    
        switch_mode: function(view_type, no_store, view_options) {
        	var result = this._super(view_type, no_store, view_options);
            var view = this.views[view_type];
            var self = this;
            var filter_array = [];
            
        	if (self.action && self.action.context.search_by_field_date){
            	filter_array = self.action.context.search_by_field_date;
            }else{
            	if (self.context && self.context.search_by_field_date){
            		filter_array = self.context.search_by_field_date;
            	}
            }
        	
            if (this.active_view && this.active_view.type != "form" && filter_array.length > 0) {
            	$('#SearchRangeDate').show();
            }
            else{
                $('#SearchRangeDate').hide();
            }
            
            if (!this.active_search){
        		this.active_search = $.Deferred();
        	}
            
            return result;
        },
    });
    
});
