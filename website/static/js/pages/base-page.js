/**
 * JS module included on eveery page of the OSF. Site-wide initialization
 * code goes here.
 */
'use strict';

var $ = require('jquery');
require('jquery.cookie');

var $osf = require('osf-helpers');

// If there isn't a user logged in, show the footer slide-in
var sliderSelector = '#footerSlideIn';
var SlideInViewModel = function (){
    var self = this;
    self.elem = $(sliderSelector);
    if (this.elem.length > 0 && $.cookie('slide') !== '0') {
        setTimeout(function () {
            self.elem.slideDown(1000);
        }, 3000);
    }
    self.dismiss = function() {
        self.elem.slideUp(1000);
        $.cookie('slide', '0', { expires: 1});
    };
};
var NO_FOOTER_PATHS = ['/login/', '/getting-started/'];
if ($(sliderSelector).length > 0 &&
        $.inArray(window.location.pathname, NO_FOOTER_PATHS) === -1) {
    $osf.applyBindings(new SlideInViewModel(), sliderSelector);
}
