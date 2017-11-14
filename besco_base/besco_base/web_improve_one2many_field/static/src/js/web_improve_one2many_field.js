odoo.define('web_improve_one2many_field', function (require) {
	"use strict";
	var core = require('web.core');
	var data = require('web.data');
	var FormView = require('web.FormView');
	var common = require('web.list_common');
	var ListView = require('web.ListView');
	var utils = require('web.utils');
	var Widget = require('web.Widget');
	var _t = core._t;
	var QWeb = core.qweb;
	var COMMANDS = common.commands;
	var list_widget_registry = core.list_widget_registry;

	ListView.include(/** @lends instance.web.ListView# */{
		prepends_on_create: function () {
	        return (this.editable() === 'bottom');
	    },
	})

	ListView.List.include({
		pad_table: function (count) {
			if (!this.view.x2m){
				this.select_table(count);
				return;
			}
	        if (!this.view.is_action_enabled('create') || this.view.x2m.get('effective_readonly')) {
	            this.select_table(count);
	            return;
	        }
	
	        this.select_table(count > 0 ? count - 1 : 0);
	
	        var self = this;
	        var columns = _(this.columns).filter(function (column) {
	            return column.invisible !== '1';
	        }).length;
	        if (this.options.selectable) { columns++; }
	        if (this.options.deletable) { columns++; }
	
	        var $cell = $('<td>', {
	            colspan: columns,
	            'class': 'oe_form_field_x2many_list_row_add_new'
	        }).append(
	            $('<a>', {href: '#'}).text(_t("Add an item"))
	                .click(function (e) {
	                    e.preventDefault();
	                    e.stopPropagation();
	                    if (self.view.editor.form.__blur_timeout) {
	                        clearTimeout(self.view.editor.form.__blur_timeout);
	                        self.view.editor.form.__blur_timeout = false;
	                    }
	                    self.view.save_edition().done(function () {
	                        self.view.do_add_record();
	                    });
	                    
	                }));
	   	 	var $new_btn = this.view.$el.find('.oe_form_field_x2many_list_row_add_new');
	   	 	var $newrow = $('<tr>').append($cell);
	   	 	if ($new_btn.length == 0){
	   	 		var $first_header = this.view.$el.find('.oe_list_header_columns');
	   	 		$first_header.after($newrow);
	   	 	}
	    },
	    
	    select_table: function (count) {
	        if (this.records.length >= count ||
	                _(this.columns).any(function(column) { return column.meta; })) {
	            return;
	        }
	        var cells = [];
	        if (this.options.selectable) {
	            cells.push('<th class="oe_list_record_selector"></td>');
	        }
	        _(this.columns).each(function(column) {
	            if (column.invisible === '1') {
	                return;
	            }
	            cells.push('<td title="' + column.string + '">&nbsp;</td>');
	        });
	        if (this.options.deletable) {
	            cells.push('<td class="oe_list_record_delete"></td>');
	        }
	        cells.unshift('<tr>');
	        cells.push('</tr>');

	        var row = cells.join('');
	        this.$current
	            .children('tr:not([data-id])').remove().end()
	            .append(new Array(count - this.records.length + 1).join(row));
	    },
	    
	    render: function () {
	        var self = this;
	        this.$current.html(
	            QWeb.render('ListView.rows', _.extend({}, this, {
	                    render_cell: function () {
	                        return self.render_cell.apply(self, arguments); }
	                })));
	        this.pad_table(4);
	    },
	});    
	    
	return ListView;

});