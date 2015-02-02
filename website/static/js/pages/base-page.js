/**
 * JS module included on every page of the OSF. Site-wide initialization
 * code goes here.
 */
'use strict';

var $ = require('jquery');
require('jquery.cookie');
require('../crossOrigin.js');

var NavbarControl = require('navbar-control');
var $osf = require('osfHelpers');

// Prevent IE from caching responses
$.ajaxSetup({ cache: false });

// Apply an empty view-model to the navbar, just so the tooltip bindingHandler
// can be used
// $osf.applyBindings({}, '#navbarScope');

$('[rel="tooltip"]').tooltip();

// If there isn't a user logged in, show the footer slide-in
var sliderSelector = '#footerSlideIn';
var SlideInViewModel = function (){
    var self = this;
    self.elem = $(sliderSelector);

    var dismissed = false;

    try {
        dismissed = dismissed || window.localStorage.getItem('slide') === '0';
    } catch (e) {}

    dismissed = dismissed || $.cookie('slide') === '0';

    if (this.elem.length > 0 && !dismissed) {
        setTimeout(function () {
            self.elem.slideDown(1000);
        }, 3000);
    }
    self.dismiss = function() {
        self.elem.slideUp(1000);
        try {
            window.localStorage.setItem('slide', '0');
        } catch (e) {
            $.cookie('slide', '0', { expires: 1, path: '/'});
        }
    };
};
var NO_FOOTER_PATHS = ['/login/', '/getting-started/', '/register/'];
if ($(sliderSelector).length > 0 &&
        $.inArray(window.location.pathname, NO_FOOTER_PATHS) === -1) {
    $osf.applyBindings(new SlideInViewModel(), sliderSelector);
}


$(document).on('click', '.project-toggle', function() {
    var widget = $(this).closest('.addon-widget-container');
    var up = $(this).find('.icon-angle-up');
    var down = $(this).find('.icon-angle-down');
    if(up.length > 0) {
        up.removeClass('icon-angle-up').addClass('icon-angle-down');
    }
    if(down.length > 0) {
        down.removeClass('icon-angle-down').addClass('icon-angle-up');            
    }

    widget.find('.addon-widget-body').slideToggle();
    return false;
});

new NavbarControl('.osf-nav-wrapper');
