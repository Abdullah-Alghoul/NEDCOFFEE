odoo.define('general_mrp_operations.mrp_operation_quick_search', function (require) {
"use strict";

	var core = require('web.core');
	var data = require('web.data');
	var ListView = require('web.ListView');
	var Model = require('web.DataModel');
	
	var QWeb = core.qweb;
	
	var MRPOperationQuickSearch = ListView.extend({
	    init: function() {
	        this._super.apply(this, arguments);
	        this.stages = [];
            this.workcenters = [];
            this.current_stage = null;
            this.current_workcenter = null;
            this.default_workcenter = null;
            this.default_stage = null;
	    },
	    
	    start:function(){
	        var tmp = this._super.apply(this, arguments);
	        var self = this;
	        var defs = [];
	        this.$el.parent().prepend(QWeb.render("MRPOperationQuickSearch", {widget: this}));
	        
	        this.$el.parent().find('.oe_operation_select_stage').change(function() {
                self.current_stage = this.value === '' ? null : parseInt(this.value);
                self.last_context['change_stage'] = '1'
	            self.do_search(self.last_domain, self.last_context, self.last_group_by);
            });
	        this.$el.parent().find('.oe_operation_select_workcenter').change(function() {
	                self.current_workcenter = this.value === '' ? null : parseInt(this.value);
	                self.do_search(self.last_domain, self.last_context, self.last_group_by);
	            });
	        
	        this.on('edit:after', this, function () {
	        	self.$el.parent().find('.oe_operation_select_stage').attr('disabled', 'disabled');
	            self.$el.parent().find('.oe_operation_select_workcenter').attr('disabled', 'disabled');
	        });
	        this.on('save:after cancel:after', this, function () {
	        	self.$el.parent().find('.oe_operation_select_stage').removeAttr('disabled');
	            self.$el.parent().find('.oe_operation_select_workcenter').removeAttr('disabled');
	        });
	         
	        var mod = new Model("mrp.production.workcenter.line", self.dataset.context, self.dataset.domain);
	        
	        defs.push(mod.call("default_quicksearch", []).then(function(result) {
	            self.current_stage = result['congdoan_id'];
	            self.current_workcenter = result['workcenter_id'];
	        }));
	        defs.push(mod.call("list_stages", []).then(function(result) {
	            self.stages = result;
	        }));
	        defs.push(mod.call("list_workcenters", []).then(function(result) {
	            self.workcenters = result;
	        }));
	        return $.when(tmp, defs);
	    },
	    
	    do_search: function(domain, context, group_by) {
            var self = this;
            this.last_domain = domain;
            this.last_context = context;
            this.last_group_by = group_by;
            this.old_search = _.bind(this._super, this);
            
            var o;
            self.$el.parent().find('.oe_operation_select_stage').children().remove().end();
            //self.$el.parent().find('.oe_operation_select_stage').append(new Option('', ''));
            for (var i = 0;i < self.stages.length;i++){
                o = new Option(self.stages[i][1], self.stages[i][0]);
                self.$el.parent().find('.oe_operation_select_stage').append(o);
                
                if (self.stages[i][0] === self.current_stage) {
                	self.$el.parent().find('.oe_operation_select_workcenter').children().remove().end();
                	for (var j = 0;j < self.workcenters.length;j++){
                		if (self.stages[i][2] === self.workcenters[j][2]){
							o = new Option(self.workcenters[j][1], self.workcenters[j][0]);
		                	self.$el.parent().find('.oe_operation_select_workcenter').append(o);
		                	if (self.workcenters[j][0] === self.current_workcenter){
		                		$(o).attr('selected',true);
		                	}
		                	if (context['change_stage'] === '1'){
		                		self.current_workcenter = self.workcenters[j][0]
		                		context['change_stage'] = '0'
		                		$(o).attr('selected',true);
		                	}
	                	}
                	}
                }
            }
		            
            self.$el.parent().find('.oe_operation_select_stage').val(self.current_stage).attr('selected',true);
            //self.$el.parent().find('.oe_operation_select_workcenter').val(self.current_workcenter).attr('selected',true);
            return self.search_by_workcenter_stage();
        },
        
        search_by_workcenter_stage: function() {
            var self = this;
            var domain = [];
            
            if (self.current_stage !== null) domain.push(["congdoan_id", "=", self.current_stage]);
            if (self.current_workcenter !== null) domain.push(["workcenter_id", "=", self.current_workcenter]);
            
            self.last_context["workcenter_id"] = self.current_workcenter === null ? false : self.current_workcenter;
            if (self.current_stage === null) delete self.last_context["congdoan_id"];
            else self.last_context["congdoan_id"] =  self.current_stage;
            var compound_domain = new data.CompoundDomain(self.last_domain, domain);
            self.dataset.domain = compound_domain.eval();
            return self.old_search(compound_domain, self.last_context, self.last_group_by);
        },
	});
	
	core.view_registry.add('tree_mrp_operation_quickadd', MRPOperationQuickSearch);
});