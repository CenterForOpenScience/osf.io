'use strict';
var $ = require('jquery');

var pointers = require('js/pointers');
var AccountClaimer = require('js/accountClaimer');
var $osf = require('js/osfHelpers');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('js/project');
require('js/licensePicker');

var node = window.contextVars.node;
var OFFSET = 49;

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
});

$(window).scroll(function() {
    var scrollTop = $(this).scrollTop();
    scrollTop = (scrollTop <= OFFSET ? scrollTop : OFFSET);
    if ($('.comment-handle-icon').is(':hidden')) {
        $('.comment-pane').css({
            'transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)',
            '-webkit-transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)',
            '-moz-transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)'
        });
    }
});

$(window).resize(function() {
    var scrollTop = $(this).scrollTop();
    scrollTop = $('.comment-handle-icon').is(':hidden') ? scrollTop : 0;
    scrollTop = (scrollTop <= OFFSET ? scrollTop : OFFSET);
    $('.comment-pane').css({
        'transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)',
        '-webkit-transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)',
        '-moz-transform': 'translate3d(0, ' + (-scrollTop) + 'px, 0)'
    });
});
