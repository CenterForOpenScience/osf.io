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

    var target = 50,
    timeout = null;
    $(window).scroll(function () {
        if (!timeout) {
            timeout = setTimeout(function () {
                clearTimeout(timeout);
                timeout = null;
                if ($(window).scrollTop() >= target) {
                    $('.cp-handle').css('margin-top', 50);
                }
                else {
                     $('.cp-handle').css('margin-top', 95);
                }
        }, 80);
    }
});
});
