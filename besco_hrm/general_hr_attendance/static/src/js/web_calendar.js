odoo.define('general_hr_attendance.CalendarViewInherit', function (require) {
	"use strict";
	var calendar = require("web_calendar.CalendarView");
	calendar.include({
		
		get_color: function(key) {
			console.log('get_color INHERITaa')
	        if (key == 'red'){
	            return index = 26
	        }
	        if (key == 'yellow'){
	            return index = 27
	        }
	        if (key =='cyanosis'){
	            return index = 28
	        }
	        if (key =='white'){
	            return index = 29
	        }
	        if (key == 'orange'){
	            return index = 30
	        }
	        if (this.color_map[key]) {
	            return this.color_map[key];
	        }
	        var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
	        this.color_map[key] = index;
	        return index;
	    },
	    
	});
});