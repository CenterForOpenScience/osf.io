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

    var target = 50, smallScreenSize = 767,
    timeout = null;
    var checkPanelPosition = function() {
        var bodyWidth = $(document.body).width();
        if (bodyWidth <= smallScreenSize) {
            if ($(window).scrollTop() >= target) {
                $('.cp-handle').css('margin-top', 50);
            }
            else {
                $('.cp-handle').css('margin-top', 95);
            }
        }
    };

    checkPanelPosition(); /* Init when refreshing the page*/
    $(window).scroll(function () {
        if (!timeout) {
            timeout = setTimeout(function () {
                clearTimeout(timeout);
                timeout = null;
                checkPanelPosition();
            }, 80);
        }
    });

    $( window ).resize(function() {
        var bodyWidth = $(document.body).width();
        if (bodyWidth > smallScreenSize || $(window).scrollTop() < target) {
            $('.cp-handle').css('margin-top', 95);
        } else if (bodyWidth < smallScreenSize || $(window).scrollTop() > target) {
            $('.cp-handle').css('margin-top', 50);
        }
    });
});
