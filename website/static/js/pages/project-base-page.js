'use strict';
var $ = require('jquery');

var pointers = require('js/pointers');
var AccountClaimer = require('js/accountClaimer.js');
var $osf = require('js/osfHelpers');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('js/project');

var node = window.contextVars.node;


new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}

// Works only with anchors with the id of the element that bootstrap uses
// Buffer is the amount to leave on top
function replaceAnchorScroll (buffer){
    buffer = buffer || 100;
    $(document).on('click', 'a[href^="#"]', function(event){
        if(!$(this).attr('data-model') && $(this).attr('href') !== '#') {
            event.preventDefault();
            // get location of the target
            var target = $(this).attr('href'),
                offset = $(target).offset();
            $(window).scrollTop(offset.top-buffer);
        }
    });
}

$(document).ready(function(){
    replaceAnchorScroll();
});


$.getJSON(node.urls.api, function(data) {
    $('body').trigger('nodeLoad', data);
});
