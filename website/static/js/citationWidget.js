///////////////////////
/// Citation Widget ///
///////////////////////

(function(global, factory) {
    if (typeof define === 'function' && define.amd) {
        define(['knockout', 'jquery', 'osfutils'], factory);
    } else if (typeof $script === 'function') {
    	global.CitationWidget = factory(ko, jQuery);
		$script.done('citationWidget');
    } else {
        global.CitationWidget = factory(ko, jQuery);
    }
}(this, function(ko, $) {

	'use strict';

    function CitationViewModel(data) {

        var self = this;
        self.expanded = ko.observable(false);
        
        self.toggleState = function(){
        	self.expanded(!self.expanded());
        };

        ko.bindingHandlers.slideVisible = {
	    	init: function(element, valueAccessor) {
	        	var value = valueAccessor();
    	    	$(element).toggle(ko.unwrap(value));
	    	},
	    	update: function(element, valueAccessor) {
	    	    var value = valueAccessor();
    	    	ko.unwrap(value) ? $(element).slideDown() : $(element).slideUp();
	    	}
	    };
	}

    function CitationWidget(selector, data) {
        this.CitationViewModel = new CitationViewModel(data);
        $.osf.applyBindings(this.CitationViewModel, selector);
    }

    return CitationWidget;

}));