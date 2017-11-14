odoo.define('st_dynamic_kanban_view.shcolumns', function (require){
"use strict";
var core = require('web.core');
var utils = require('web.utils');
var KanbanView = require('web_kanban.KanbanView');
var FormView = require('web.FormView');
var QWeb = core.qweb;
var arr_field = [];
var arr_modifiers = [];
var arr_tesc = [];
var tesc_count = [];
var arr_tesc_str = [];
var arr_img = [];
var arr_class = [];
var arr_css = [];
var tesc_counter = 0;
var img_counter = 0;
var arr_img_sh = true;
var add_fields = true;
var btn = false;
// inherit kanban view
KanbanView.include({
    view_loading: function(fvg){
        this.fields_view = fvg;
        for(var i=0, ii=this.fields_view.arch.children.length; i < ii; i++){
            var child = this.fields_view.arch.children[i];
            if(child.tag === "templates"){
                var temp = fvg['name'];
                try{
                    temp = temp.toLowerCase();
                    temp = temp.search("kanban");
                }
                catch(err){
                     temp = -1;
                }
                if(temp > -1){
                    add_fields = true;
                    this.check_array();
                }
                else{
                    add_fields = false;
                    btn = false;
                }
                transform_qweb_template(child, this.fields_view, this.many2manys);
                add_fields = false;
                break;
            }
        }
        this._super(this.fields_view);
    },
    check_array: function(){
        arr_field = [];
        arr_modifiers = [];
        arr_img = [];
        tesc_count = [];
        arr_tesc = [];
        arr_class = [];
        arr_css = [];
        arr_tesc_str = [];
        arr_img_sh = true;
        btn = true;
    },
    render_buttons: function($node){
        var self = this;
        this._super($node);
        this.$buttons.find('.oe_select_columns').click(this.proxy('custom_view_loading'));
        this.$buttons.find('.oe_dropdown_menu').click(this.proxy('stop_event'));
        this.$buttons.find('.oe_dropdown_btn').click(this.proxy('hide_show_columns'));
    },
    // show or hide columns in kanbanview
    hide_show_columns : function(fvg){
        $("#showcb").hide();
        try{
            if(this.data.grouped){
                this.do_reload();
            }
        }
        catch(err){
           console.log("Failed to load page. " + err);
        }
        try{
            for(var i=0, ii=this.fields_view.arch.children.length; i < ii; i++){
                var child = this.fields_view.arch.children[i];
                if(child.tag === "templates"){
                   transform_qweb_template(child, this.fields_view, this.many2manys);
                   this.qweb.add_template(utils.json_node_to_xml(child));
                   tesc_counter = 0; img_counter = 0; btn = true;
                   break;
                }
            }
            return this.render();
        }catch(err){
            console.log("Failed to load resource. " + err);
        }
    },
    // create and display checkbox in dropdown list
    custom_view_loading: function(fvg){
        // checkbox for fields
        for(var v = 0; v< arr_field.length; v++){
            var field_string = arr_field[v];
            var modifiers_string = arr_modifiers[v];
            var checkbox_id = field_string.replace(/\s+/g, '');
            var firstcheck = $('#'+checkbox_id).attr('id');
            if(typeof firstcheck === "undefined"){
                var list_item = $("<li>").appendTo("#showcb");
                if(modifiers_string == 'true'){
                    $('<input />', {type:'checkbox',id:checkbox_id,checked:false}).appendTo(list_item);
                    $('<label />', {text:field_string }).appendTo(list_item);
                }
                else{
                    $('<input />', {type:'checkbox',id:checkbox_id,checked:true}).appendTo(list_item);
                    $('<label />', {text:field_string }).appendTo(list_item);
                }
            }
            else{
               if(modifiers_string=='true'){
                  $('#'+field_string).prop('checked', false);
               }
               else{
                  $('#'+field_string).prop('checked', true);
               }
            }
        }
        // checkbox for image
        if(arr_img.length){
            var firstcheck = $('#img').attr('id');
            if(typeof firstcheck === "undefined"){
                var list_item = $("<li>").appendTo("#showcb");
                $('<input />', {type: 'checkbox', id: "img", checked: true}).appendTo(list_item);
                $('<label />', {text: "Image" }).appendTo(list_item);
            }
            else{
                if(arr_img_sh == true){
                    $('#img').prop('checked', true);
                }
                else{
                    $('#img').prop('checked', false);
                }
           }
        }
        // checkbox for t-esc tag
        for(var tesc=0;tesc<arr_tesc.length;tesc++){
            var str = arr_tesc[tesc];
            str = str.split(".");
            var cb_tf  = tesc_count[tesc];
            var firstcheck = $('#a' + tesc).attr('id');
            if(typeof firstcheck === "undefined"){
                var list_item = $("<li>").appendTo("#showcb");
                $('<input />', {type: 'checkbox', id: 'a' + tesc, name: 'a' + str[1], checked: true}).appendTo(list_item);
                $('<label />', {text: arr_tesc_str[tesc] }).appendTo(list_item);
            }
            else{
                if(cb_tf == 'true'){
                    $('#a'+ tesc).prop('checked',true);
                }
                else{
                    $('#a'+ tesc).prop('checked',false);
                }
            }
        }
        if(btn){
            $("#showcb").show();
            btn = false;
        }
        else{
            $("#showcb").hide();
            btn = true;
        }
     },
    stop_event : function(e){
        e.stopPropagation();
    },
});
$(document).click(function(){
    $("#showcb").hide();
    btn = true;
});
function qweb_add_if(node, condition){
    if(node.attrs[QWeb.prefix + '-if']){
        condition = _.str.sprintf("(%s) and (%s)", node.attrs[QWeb.prefix + '-if'], condition);
    }
    node.attrs[QWeb.prefix + '-if'] = condition;
}
// set modifier of columns
function transform_qweb_template(node, fvg, many2manys){
    if(!add_fields){
        if(node.tag && node.attrs.modifiers){
            if(fvg.fields[node.attrs.name]){
                var field_index = arr_field.indexOf(fvg.fields[node.attrs.name]['string']);
                var get_checkbox = fvg.fields[node.attrs.name]['string'];
                get_checkbox = get_checkbox.replace(/\s+/g, '');
                var check_checkbox = $('#'+get_checkbox).attr('id');
                if(typeof check_checkbox !== "undefined"){
                    if($("#" + check_checkbox).prop("checked") !== false){
                        arr_modifiers[field_index] = 'false';
                        node.attrs[QWeb.prefix + '-if'] = "";
                        qweb_add_if(node, _.str.sprintf("!kanban_compute_domain(%s)",false));
                    }
                    else{
                        arr_modifiers[field_index] = 'true';
                        node.attrs[QWeb.prefix + '-if'] = "";
                        qweb_add_if(node, _.str.sprintf("!kanban_compute_domain(%s)",true));
                    }
                }
            }
        }
     }
    switch (node.tag){
        case 'field':
            if(add_fields){
                if(fvg.fields[node.attrs.name]){
                    if(fvg.fields[node.attrs.name]['string'] == 'unknown'){
                        fvg.fields[node.attrs.name]['string'] = node.attrs.name;
                    }
                    var str = node.attrs.modifiers;
                    var checkstr = str.search("invisible");
                    if(checkstr > -1){
                        var temp = str.substring(checkstr + 11, checkstr + 17)
                        if(temp = "true}"){
                            node.attrs['invisible'] = 1;
                        }
                    }
                    var find_field = arr_field.indexOf(fvg.fields[node.attrs.name]['string']);
                    if(find_field == -1){
                        arr_field.push(fvg.fields[node.attrs.name]['string']);
                        if(node.attrs['invisible'] == 1){
                          arr_modifiers.push('true');
                        }
                        else{
                          arr_modifiers.push('false');
                        }
                    }
                }
            }
            break;
        case 'span':
            if(add_fields){
                if(node.attrs['class'] == 'badge'){
                    arr_css.push(node.attrs['class']);
                }
                else if(node.attrs['t-attf-class']){
                    arr_css.push(node.attrs['t-attf-class']);
                }
            }
            else if(!add_fields){
                if(node.attrs['class']){
                    if(node.attrs['class'] == arr_css[tesc_counter]){
                        var get_checkbox = $('#a'+ tesc_counter).attr('id');
                        if(typeof get_checkbox !== "undefined"){
                            if($("#" + get_checkbox).prop("checked") == false){
                                node.attrs['class'] = "";
                            }
                        }
                    }
                }
                else if(node.attrs['t-attf-class']){
                    if(node.attrs['t-attf-class'] == arr_css[0]){
                        var get_checkbox = $('#a'+ tesc_counter).attr('id');
                        if(typeof get_checkbox !== "undefined"){
                            if($("#" + get_checkbox).prop("checked") == false){
                                node.attrs['t-attf-class'] = "";
                            }
                        }
                     }
                }
                else if(node.attrs['class'] == "" && (!node.attrs['t-attf-class'])){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == true){
                            node.attrs['class'] = arr_css[tesc_counter];
                        }
                   }
                }
                else if(node.attrs['t-attf-class'] == "" && (!node.attrs['class'])){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == true){
                            node.attrs['t-attf-class'] = arr_css[0];
                        }
                   }
                }
            }
            break;
        case 'i':
            if(add_fields){
                if(node.attrs['class']){
                    arr_class.push(node.attrs['class']);
                }
            }
            else{
                if(node.attrs['class'] == arr_class[tesc_counter]){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == false){
                          node.attrs['class'] = null;
                        }
                   }
                }
                else if(JSON.stringify(node.attrs['class']) == 'null'){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == true){
                            node.attrs['class'] = arr_class[tesc_counter];
                        }
                   }
                }
            }
            break;
        case 't':
            if(add_fields){
                if(node.attrs['t-esc']){
                    arr_tesc.push(node.attrs['t-esc']);
                    tesc_count.push('true');
                    var str = node.attrs['t-esc'].split(".");
                    if(fvg.fields[str[1]]){
                        arr_tesc_str.push(fvg.fields[str[1]]['string']);
                    }
                }
            }
            else{
                if(node.attrs['t-esc'] == arr_tesc[tesc_counter]){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == false){
                            delete node.attrs['t-esc'];
                            tesc_count[tesc_counter] = 'false';
                        }
                        tesc_counter = tesc_counter + 1;
                   }
                }
                else if(JSON.stringify(node.attrs) == '{}'){
                    var get_checkbox = $('#a'+ tesc_counter).attr('id');
                    if(typeof get_checkbox !== "undefined"){
                        if($("#" + get_checkbox).prop("checked") == true){
                            node.attrs['t-esc'] = arr_tesc[tesc_counter];
                            tesc_count[tesc_counter] = 'true';
                        }
                        tesc_counter = tesc_counter + 1;
                    }
                }
             }
            break;
        case 'img':
            if(add_fields){
               if(node.attrs['t-att-src']){
                  arr_img.push(node.attrs);
               }
            }
            else{
                var firstcheck = $('#img').attr('id');
                if(typeof firstcheck !== "undefined"){
                    if($("#" + firstcheck).prop("checked") !== false){
                        if(node.attrs == ""){
                            node.attrs = arr_img[img_counter];
                            arr_img_sh = true;
                            img_counter = img_counter + 1;
                        }
                    }
                    else{
                       node.attrs = "";
                       arr_img_sh = false;
                    }
                }
            }
            break;
        case 'div':
            if(!add_fields){
                if(node.attrs['class'] == 'o_kanban_image'){
                    var firstcheck = $('#img').attr('id');
                    if(typeof firstcheck !== "undefined"){
                        if($("#" + firstcheck).prop("checked") == false){
                           node.attrs['class'] = "";
                        }
                    }
                }
                else if(node.attrs['class'] == ""){
                    var firstcheck = $('#img').attr('id');
                    if(typeof firstcheck !== "undefined"){
                        if($("#" + firstcheck).prop("checked") == true){
                           node.attrs['class'] = 'o_kanban_image';
                        }
                    }
                }
            }
          break;
    }
    if(node.children){
        for(var i=0,ii=node.children.length;i < ii;i++){
            transform_qweb_template(node.children[i], fvg, many2manys);
        }
    }
}
// manage show hide columns details in form view
FormView.include({
    view_loading: function(r){
        this._super(r);
        btn = false;
        try{
            for(var v=0;v< arr_field.length;v++){
                var field_string = arr_field[v];
                var modifiers_string = arr_modifiers[v];
                var checkbox_id = field_string.replace(/\s+/g, '');
                var firstcheck = $('#'+checkbox_id).attr('id');
                if(typeof firstcheck === "undefined"){
                    var list_item = $("<li>").appendTo("#showcb");
                    if(modifiers_string == 'true'){
                        $('<input />',{type:'checkbox',id:checkbox_id,checked:false}).appendTo(list_item);
                        $('<label />',{text:field_string }).appendTo(list_item);
                    }
                    else{
                        $('<input />',{type:'checkbox',id:checkbox_id,checked:true}).appendTo(list_item);
                        $('<label />',{text:field_string }).appendTo(list_item);
                    }
                }
            }
            if(arr_img.length){
               var firstcheck = $('#img').attr('id');
               if(typeof firstcheck === "undefined"){
                    var list_item = $("<li>").appendTo("#showcb");
                    $('<input />', {type:'checkbox',id:"img",checked:true}).appendTo(list_item);
                    $('<label />', {text:"Image"}).appendTo(list_item);
               }
            }
            for(var tesc = 0; tesc <arr_tesc.length; tesc++){
                var str = arr_tesc[tesc];
                str = str.split(".");
                var cb_tf  = tesc_count[tesc];
                var firstcheck = $('#a' + tesc).attr('id');
                if(typeof firstcheck === "undefined"){
                    var list_item = $("<li>").appendTo("#showcb");
                    $('<input />', {type:'checkbox',id:'a'+tesc,name:'a'+str[1],checked:true}).appendTo(list_item);
                    $('<label />', {text:arr_tesc_str[tesc]}).appendTo(list_item);
                }
            }
        }
        catch(err){
            console.log("Unable to load elements. " + err);
        }
    },
});
});