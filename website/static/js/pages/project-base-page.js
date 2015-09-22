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
    self.thresholdScrollPosition = 50;
    self.smallScreenSize = 767;
    self.nonNavTopMargin = 50;
    self.navMaxTopMargin = 95;
    self.checkPanelPosition = function() {
        var bodyWidth = $(document.body).width();
        var scrollTopPosition = $(window).scrollTop();
        if (bodyWidth <= self.smallScreenSize) {
            if (scrollTopPosition >= self.thresholdScrollPosition) {
                $('.cp-handle').css('margin-top', self.nonNavTopMargin);
            }
            else {
                $('.cp-handle').css('margin-top', self.navMaxTopMargin - scrollTopPosition);
            }
        }
    };
    self.THROTTLE = 10;
    self.debouncePanelPosition = $osf.debounce(function() {
        self.checkPanelPosition();
    }, self.THROTTLE);

    self.checkPanelPosition(); /* Init when refreshing the page*/
    $(window).scroll(function () {
        self.debouncePanelPosition();
    });

    $( window ).resize(function() {
        var bodyWidth = $(document.body).width();
        var scrollTopPosition = $(window).scrollTop();
        if (bodyWidth > self.smallScreenSize || scrollTopPosition < self.thresholdScrollPosition) {
            $('.cp-handle').css('margin-top', self.navMaxTopMargin);
        } else if (bodyWidth < self.smallScreenSize || scrollTopPosition > self.thresholdScrollPosition) {
            $('.cp-handle').css('margin-top', self.nonNavTopMargin);
        }
    });
});
