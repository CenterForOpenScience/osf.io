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
    var thresholdScrollPosition = 50;
    var smallScreenSize = 767;
    var nonNavTopMargin = 50;
    var navMaxTopMargin = 95;
    self.adjustPanelPosition = function() {
        var bodyWidth = $(document.body).width();
        var scrollTopPosition = $(window).scrollTop();
        if (bodyWidth <= smallScreenSize) {
            if (scrollTopPosition >= thresholdScrollPosition) {
                $('.cp-handle').css('margin-top', nonNavTopMargin);
            }
            else {
                $('.cp-handle').css('margin-top', navMaxTopMargin - scrollTopPosition);
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
                if (bodyWidth > smallScreenSize || scrollTopPosition < thresholdScrollPosition) {
                    $('.cp-handle').css('margin-top', navMaxTopMargin);
                } else if (bodyWidth < smallScreenSize || scrollTopPosition > thresholdScrollPosition) {
                    $('.cp-handle').css('margin-top', nonNavTopMargin);
                }
    }, THROTTLE));
});
