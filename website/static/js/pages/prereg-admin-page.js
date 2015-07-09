'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

$(document).ready(function() {
    var test = '/api/v1/drafts/' + window.contextVars.accessToken
    var adminView = {};

    var request = $.ajax({
        url: test
    });
    request.done(function(data) {
    	adminView = {drafts: data.drafts};
    	$osf.applyBindings(adminView, '#prereg-row');
        console.log(data.drafts);
    });
    request.fail(function(xhr, textStatus, error) {
        console.log(xhr);
        Raven.captureMessage('Failed to populate data', {
            url: test,
            textStatus: textStatus,
            error: error
        });
    });

});
