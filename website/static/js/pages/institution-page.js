'use strict';

var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');
ko.punches.enableAll();

var InstitutionViewModel = function() {
    var self = this;
    self.id = window.contextVars.institution.id;
    self.allNodes = ko.observable();
    // Need to get the node
    $osf.ajaxJSON(
        'GET',
        window.contextVars.apiV2Prefix + 'institutions/' + self.id + '/nodes/',
        {
            isCors: true
        }
    ).done( function(response){
        console.log(response.data);
        self.allNodes(response.data);
    }).fail(function(response){
    });
};


$(document).ready(function() {
    var self = this;
    self.viewModel = new InstitutionViewModel();
    $osf.applyBindings(self.viewModel, '#inst');
});
