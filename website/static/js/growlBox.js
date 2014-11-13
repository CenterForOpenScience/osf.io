// website/static/js/growlBox.js

// Initial semicolon for safe minification
;(function (global, factory) {
    // Support RequireJS/AMD or no module loader
    if (typeof define === 'function' && define.amd) {
        // Dependency IDs here
        define(['jquery', 'vendor/bower_components/bootstrap.growl/bootstrap-growl'], factory);
    } else { // No module loader, just attach to global namespace
        global.GrowlBox = factory(jQuery);
    }
}(this, function($) {  // named dependencies here
    'use strict';
    // Private methods go up here

    // This is the public API

    // The constructor
    function GrowlBox (title, message) {
        var self = this;

        self.title = title;
        self.message = message;
        self.init(self);
    }
    // Methods
    GrowlBox.prototype.init = function(self) {
        $.growl({
            title: '<strong>' + self.title + '<strong><br />',
            message: self.message
        },{
            type: 'danger',
            delay: 0,
            animate: {
                enter: 'animated slideInDown',
                exit: 'animated slideOutRight'
	        }
        });
    };

    return GrowlBox;
}));