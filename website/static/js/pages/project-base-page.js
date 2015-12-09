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
    var st = $(this).scrollTop();
    var offset = 49;
    st = (st <= offset ? st : offset);
    if ($('.comment-handle-icon').is(':hidden')) {
        $('.comment-pane').css({
            'transform': 'translate3d(0, ' + (-st) + 'px, 0)',
            '-webkit-transform': 'translate3d(0, ' + (-st) + 'px, 0)',
            '-moz-transform': 'translate3d(0, ' + (-st) + 'px, 0)'
        });
    }
});

$(window).resize(function() {
    var st = $(this).scrollTop();
    st = $('.comment-handle-icon').is(':hidden') ? st : 0;
    var offset = 49;
    st = (st <= offset ? st : offset);
    $('.comment-pane').css({
        'transform': 'translate3d(0, ' + (-st) + 'px, 0)',
        '-webkit-transform': 'translate3d(0, ' + (-st) + 'px, 0)',
        '-moz-transform': 'translate3d(0, ' + (-st) + 'px, 0)'
    });
});
