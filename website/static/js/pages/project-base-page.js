'use strict';
var $ = require('jquery');

var pointers = require('js/pointers');
var AccountClaimer = require('js/accountClaimer.js');
var $osf = require('js/osfHelpers');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('js/project');

require('js/registerNode');

var node = window.contextVars.node;


new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}

// Used for clearing backward/forward cache issues
$(window).unload(function(){
    return 'Unload';
});
$(document).ready(function() {
    $.getJSON(node.urls.api, function(data) {    
        $('body').trigger('nodeLoad', data);
    });

    var self = this;
    var THRESHOLD_SCROLL_POSITION  = 50;
    var SMALL_SCREEN_SIZE = 767;
    var NON_NAV_TOP_MARGIN = 50;
    var NAV_MAX_TOP_MARGIN = 95;
    self.adjustPanelPosition = function() {
        var bodyWidth = $(document.body).width();
        var scrollTopPosition = $(window).scrollTop();
        if (bodyWidth <= SMALL_SCREEN_SIZE) {
            if (scrollTopPosition >= THRESHOLD_SCROLL_POSITION) {
                $('.cp-handle').css('margin-top', NON_NAV_TOP_MARGIN);
            }
            else {
                $('.cp-handle').css('margin-top', NAV_MAX_TOP_MARGIN - scrollTopPosition);
            }
        }
    };
    var THROTTLE = 10;

    self.adjustPanelPosition(); /* Init when refreshing the page*/
    $(window).scroll(
        $osf.debounce(
            function() {
                self.adjustPanelPosition();
    }, THROTTLE));

    THROTTLE = 50;
    $( window ).resize(
        $osf.debounce(
            function() {
                var bodyWidth = $(document.body).width();
                var scrollTopPosition = $(window).scrollTop();
                if (bodyWidth > SMALL_SCREEN_SIZE || scrollTopPosition < THRESHOLD_SCROLL_POSITION) {
                    $('.cp-handle').css('margin-top', NAV_MAX_TOP_MARGIN);
                } else if (bodyWidth < SMALL_SCREEN_SIZE || scrollTopPosition > THRESHOLD_SCROLL_POSITION) {
                    $('.cp-handle').css('margin-top', NON_NAV_TOP_MARGIN);
                }
    }, THROTTLE));
});
