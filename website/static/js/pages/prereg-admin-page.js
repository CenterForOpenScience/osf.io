'use strict';

var $osf = require('js/osfHelpers');
var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');

var drafts;

ko.bindingHandlers.enterkey = {
    init: function (element, valueAccessor, allBindings, viewModel) {
        var callback = valueAccessor();
        $(element).keypress(function (event) {
            var keyCode = (event.which ? event.which : event.keyCode);
            if (keyCode === 13) {
                callback.call(viewModel);
                return false;
            }
            return true;
        });
    }
};

function adminView(data) {
    var self = this;
    self.data = data.drafts;
    console.log(self.data);
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

    // variables for editing items in row
    self.edit = ko.observable(false);
    self.item = ko.observable();
    self.commentsSent = ko.observable('no');
    self.proofOfPub = ko.observable('no');
    self.paymentSent = ko.observable('no');
    self.notes = ko.observable('none');

    self.setSort = function(data, event) {
        self.sortBy(event.target.id);
    };

    self.highlightRow = function(data, event) {  
        var row = event.currentTarget;
        $(row).css("background","#E0EBF3"); 
    };

    self.unhighlightRow = function(data, event) {
        var row = event.currentTarget;
        $(row).css("background",""); 
    };

    self.formatTime = function(time) {
        var parsedTime = time.split(".");
        return parsedTime[0]; 
    };

    self.goToDraft = function(data, event) {
        if (self.edit() === false) {
            var path = "/project/" + data.branched_from.node.id + "/draft/" + data.pk;
            location.href = path;
        }
    };

    self.selectValue = function(data, event) {
        var path = "/project/" + data.branched_from.node.id + "/draft/" + data.pk;
        console.log(path);
    };

    self.addNotes = function(data, event) {
        var path = "/project/" + data.branched_from.node.id + "/draft/" + data.pk;
        console.log(path);
    };

    self.enlargeIcon = function(data, event) {
        var icon = event.currentTarget;
        $(icon).addClass("fa-2x");
    };

    self.shrinkIcon = function(data, event) {
        var icon = event.currentTarget;
        $(icon).removeClass("fa-2x");
    };

    self.editItem = function(item) {
        self.edit(true);
        $('.'+item).hide();
        $('.input_' + item).show();
        $('.input_' + item).focus();
    };

    self.stopEditing = function(item) {
        $('.'+item).show();
        $('.input_' + item).hide();
    };

}

$(document).ready(function() {
    var test = '/api/v1/drafts/';
    var request = $.ajax({
        url: test
    });
    request.done(function(data) {
    	$osf.applyBindings(new adminView(data), '#prereg-row');
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
