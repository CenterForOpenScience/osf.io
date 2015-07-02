'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

$(document).ready(function() {

    var request = $.ajax({
        url:  '/api/v1/all_drafts/'
    });
    request.done(function(data) {
        console.log(data);
    });
    request.fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Failed to populate data', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });

});
