'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

var drafts;

$(document).ready(function() {
    var test = '/api/v1/drafts/' + window.contextVars.accessToken
    var adminView = {};

    var request = $.ajax({
        url: test
    });
    request.done(function(data) {
    	drafts = data.drafts;
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

$(".row-title").click(function(event) {
	console.log(event.target.id);
	sortedDrafts(event.target.id);
});

var sortedDrafts = function(row) {
   return drafts.sort(function (left, right) { 
        return left.row.order() == right.row.order() ? 
             0 : 
             (left.row.order() < right.row.order() ? -1 : 1); 
   });
};
