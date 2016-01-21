'use strict';
var $ = require('jquery');
var $osf = require('js/osfHelpers');
require('css/typeahead.css');
require('typeahead.js');

(function($) {
    $.fn.projectsSelect = function (options) {

        // Default options
        var settings = $.extend({
            data : [],
            complete: null
        }, options);

        return this.keyup(function() {
            if ( $.isFunction( settings.complete ) ) {
                settings.complete.call( this );
            }
        });
    };

})($);
