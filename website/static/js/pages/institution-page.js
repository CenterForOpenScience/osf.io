'use strict';

var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');
ko.punches.enableAll();

var FileBrowser = require('js/fileBrowser.js').FileBrowser;
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.

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
    m.mount(document.getElementById('fileBrowser'), m.component(FileBrowser, {wrapperSelector : '#fileBrowser'}));

    // Add active class to navigation for my projects page
    $('#osfNavMyProjects').addClass('active');
});
