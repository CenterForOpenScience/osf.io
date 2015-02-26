/**
 * JS module included on every page of the OSF. Site-wide initialization
 * code goes here.
 */
'use strict';
// CSS used on every page
require('../../vendor/bower_components/bootstrap/dist/css/bootstrap-theme.css');
require('../../vendor/bower_components/x-editable/dist/bootstrap3-editable/css/bootstrap-editable.css');
require('../../vendor/bower_components/jquery-ui/themes/base/minified/jquery.ui.resizable.min.css');
require('../../css/bootstrap-xl.css');
require('../../css/animate.css');
require('../../css/site.css');


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

var NO_FOOTER_PATHS = ['/', '/login/', '/getting-started/', '/register/', '/forgotpassword/', '/share/'];
$(function() {
    if(/MSIE 9.0/.test(navigator.userAgent) || /MSIE 8.0/.test(navigator.userAgent) ||/MSIE 7.0/.test(navigator.userAgent) ||/MSIE 6.0/.test(navigator.userAgent)) {
        $('.placeholder-replace').show();
    }
    if ($(sliderSelector).length > 0 &&
            $.inArray(window.location.pathname, NO_FOOTER_PATHS) === -1) {
        $osf.applyBindings(new SlideInViewModel(), sliderSelector);
    }
    new NavbarControl('.osf-nav-wrapper');
});
