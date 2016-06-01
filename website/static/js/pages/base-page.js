/**
 * JS module included on every page of the OSF. Site-wide initialization
 * code goes here.
 */
'use strict';
// CSS used on every page
require('../../vendor/bootstrap-editable-custom/css/bootstrap-editable.css');
require('../../vendor/bower_components/jquery-ui/themes/base/minified/jquery.ui.resizable.min.css');
require('../../css/bootstrap-xl.css');
require('../../css/animate.css');
require('../../css/search-bar.css');
require('font-awesome-webpack');

var $ = require('jquery');
require('jquery.cookie');

require('js/crossOrigin.js');
var $osf = require('js/osfHelpers');
var NavbarControl = require('js/navbarControl');
var Raven = require('raven-js');
var moment = require('moment');
var KeenTracker = require('js/keen');
var DevModeControls = require('js/devModeControls');

// Prevent IE from caching responses
$.ajaxSetup({cache: false});

// Polyfill for String.prototype.endsWith
if (String.prototype.endsWith === undefined) {
    String.prototype.endsWith = function(suffix) {
        return this.indexOf(suffix, this.length - suffix.length) !== -1;
    };
}

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
        self.trackClick('Dismiss');
    };
    // Google Analytics click event tracking
    self.trackClick = function(source) {
        window.ga('send', 'event', 'button', 'click', source);
        //in order to make the href redirect work under knockout onclick binding
        return true;
    };
};


$(document).on('click', '.panel-heading', function(){
    var toggle = $(this).find('.project-toggle');
    if(toggle.length > 0){
        var widget = $(this).closest('.panel');
        var up = toggle.find('.fa.fa-angle-up');
        var down = toggle.find('.fa.fa-angle-down');
        if(up.length > 0) {
            up.removeClass('fa fa-angle-up').addClass('fa fa-angle-down');
        }
        if(down.length > 0) {
            down.removeClass('fa fa-angle-down').addClass('fa fa-angle-up');
        }

        widget.find('.panel-body').slideToggle();
    }
});


$(function() {
    if(/MSIE 9.0/.test(window.navigator.userAgent) ||
       /MSIE 8.0/.test(window.navigator.userAgent) ||
       /MSIE 7.0/.test(window.navigator.userAgent) ||
       /MSIE 6.0/.test(window.navigator.userAgent)) {
        $('.placeholder-replace').show();
    }
    if (
        $(sliderSelector).length > 0 &&
        window.contextVars.node
    ) {
        $osf.applyBindings(new SlideInViewModel(), sliderSelector);
    }

    var affix = $('.osf-affix');
    if(affix.length){
        $osf.initializeResponsiveAffix();
    }
    new NavbarControl('.osf-nav-wrapper');
    new DevModeControls('#devModeControls', '/static/built/git_logs.json');
    if(window.contextVars.keenProjectId){
        var params = {};
        params.currentUser = window.contextVars.currentUser;
        params.node = window.contextVars.node;

        //Don't track PhantomJS visits with KeenIO
        if(!(/PhantomJS/.test(navigator.userAgent))){
            new KeenTracker(window.contextVars.keenProjectId, window.contextVars.keenWriteKey, params);
        }
    }

    // Ad script alert
    var adBlockPersistKey = 'adBlock';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        $.cookie(adBlockPersistKey, '0', { expires: 1, path: '/'});
    })
    var dismissed = $.cookie(adBlockPersistKey) === '0';
    if (!dismissed) {
        $adBlock.show();
    }
    // Ad script alert
});
