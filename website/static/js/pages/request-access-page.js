'use strict';

var $osf = require('js/osfHelpers');
var RequestAccessManager = require('js/requestAccess');


var ctx = window.contextVars;


$(window).on('load', function() {
    new RequestAccessManager('#requestAccessScope', ctx.currentUserRequestState);
});

$(function() {
    if (ctx.currentUserRequestState === 'rejected') {
        $('.request-access').popover({
            trigger: 'hover'
        });
    }
});
