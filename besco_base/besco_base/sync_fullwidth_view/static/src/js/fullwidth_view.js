odoo.define('sync_fullwidth_view.sync_fullwidth_view', function (require) {
	var core = require('web.core');
	var QWeb = core.qweb;
	var _t = core._t;
	var WebClient = require('web.WebClient');
//	var im_chat = require('im_chat.im_chat');
	
	
	WebClient.include({
		start: function() {
			var self = this;
			this._super.apply(this, arguments);
			$(".oe_leftbar").animate({
            	'left': '-1020px'
           	}, 0).addClass("Moved");
			$(".hide-left-menu").click(function(){
	            if (!$(".oe_leftbar").hasClass("Moved")){
	            	$(".oe_leftbar").animate({
	                	'left': '-220px'
	               	}, 100).addClass("Moved");
	                $(".oe_leftbar").css({'position': 'absolute'});
//	                $(this).css('top','0%');
	                $(".arrow-image").css({'transform' : 'rotate(180deg)'});
	            }else{
	                $(".oe_leftbar").animate({
	                    "left": "0px"
	                }, 'slow').removeClass("Moved").css({'position': 'relative'});
//	                $(this).css('top','0%');
	                $(".arrow-image").css({'transform' : 'rotate(0deg)'});
	            }
	        });
			$('button.hide-pane').click(function(){alert("clicked");});
      },
	});
	
//	im_chat.InstantMessaging.include({
//      events: {
//          "keydown .oe_im_searchbox": "input_change",
//          "keyup .oe_im_searchbox": "input_change",
//          "change .oe_im_searchbox": "input_change",
//          "click button.hide-pane": "hide_pane"
//      },
//	  hide_pane: function(){
//		  this.switch_display();
//	  },
//	  
//	  switch_display: function() {
//          var self = this;
//          this._super.apply(this, arguments);
//          if (this.shown)
//              $(".arrow-img").css({'transform' : 'rotate(180deg)'});
//          else
//              $(".arrow-img").css({'transform' : 'rotate(0deg)'});
//	  },
//	  
//	});
		
});

//V8
//openerp.sync_fullwidth_view = function (instance) {
//    var QWeb = instance.web.qweb;
//    var _t = instance.web._t;
//
//	instance.web.WebClient.include({
//		start: function() {
//        	var self = this;
//			this._super.apply(this, arguments);
//			$(".hide-left-menu").click(function(){
//	            if (!$(".oe_leftbar").hasClass("Moved")){
//	            	$(".oe_leftbar").animate({
//	                	'left': '-220px'
//	               	}, 100).addClass("Moved");
//	                $(".oe_leftbar").css({'position': 'absolute'});
//	                $(this).css('top','37%');
//	                $(".arrow-image").css({'transform' : 'rotate(180deg)'});
//	            }else{
//	                $(".oe_leftbar").animate({
//	                    "left": "0px"
//	                }, 'slow').removeClass("Moved").css({'position': 'inherit'});
//	                $(this).css('top','42%');
//	                $(".arrow-image").css({'transform' : 'rotate(0deg)'});
//	            }
//	        });
//			$('button.hide-pane').click(function(){alert("clicked");});
//        }
//	});
//
//	instance.im_chat.InstantMessaging.include({
//        events: {
//            "keydown .oe_im_searchbox": "input_change",
//            "keyup .oe_im_searchbox": "input_change",
//            "change .oe_im_searchbox": "input_change",
//            "click button.hide-pane": "hide_pane"
//        },
//    	hide_pane: function(){
//            this.switch_display();
//        },
//    	switch_display: function() {
//            var self = this;
//            this._super.apply(this, arguments);
//            if (this.shown)
//                $(".arrow-img").css({'transform' : 'rotate(180deg)'});
//            else
//                $(".arrow-img").css({'transform' : 'rotate(0deg)'});
//        }
//	});
//}
