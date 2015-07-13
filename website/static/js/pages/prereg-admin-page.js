'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

var drafts;

var adminView = function(data) {
    self.data = data.drafts;
    self.drafts = ko.pureComputed(function() {
        var row = self.sortBy();
        return data.drafts.sort(function (left, right) { 
            var a = deep_value(left, row).toLowerCase()
            var b = deep_value(right, row).toLowerCase()
            return a == b ? 0 : 
                (a < b ? -1 : 1); 
        });
    }, this);
    self.sortBy = ko.observable('registration_metadata.q1.value');

    self.setSort = function(data, event) {
        self.sortBy(event.target.id);
    };

    self.highlightRow = function(data, event) {
        $(event.target.id).css("background-color", "yellow");
    };
};

$(document).ready(function() {
    var test = '/api/v1/drafts/';
    var request = $.ajax({
        url: test
    });
    request.done(function(data) {
    	$osf.applyBindings(adminView(data), '#prereg-row');
    });
    request.fail(function(xhr, textStatus, error) {
        Raven.captureMessage('Failed to populate data', {
            url: test,
            textStatus: textStatus,
            error: error
        });
    });
});

var deep_value = function(obj, path){
    for (var i=0, path=path.split('.'), len=path.length; i<len; i++){
        obj = obj[path[i]];
    };
    return obj;
};
