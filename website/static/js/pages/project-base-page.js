'use strict';
var $ = require('jquery');

var pointers = require('js/pointers');
var AccountClaimer = require('js/accountClaimer');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('js/project');
require('js/licensePicker');
require('css/pages/project-page.css');

var node = window.contextVars.node;
var OFFSET = 49;

new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

// Used for clearing backward/forward cache issues
$(window).on('unload', function(){
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
