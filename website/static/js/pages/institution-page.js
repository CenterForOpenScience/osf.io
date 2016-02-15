'use strict';

var $ = require('jquery');
var ko = require('knockout');

var $osf = require('js/osfHelpers');
ko.punches.enableAll();

var FileBrowser = require('js/dashboard.js').Dashboard;
var LinkObject = require('js/dashboard.js').LinkObject;
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
    m.mount(document.getElementById('fileBrowser'), m.component(FileBrowser, {wrapperSelector : '#fileBrowser', systemCollections:[
        new LinkObject('collection', { path : 'institutions/ND/nodes/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'nodes'}, 'All Projects'),
        new LinkObject('collection', { path : 'institutions/ND/registrations/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'nodes'}, 'All Registrations'),
    ]}));

    // Add active class to navigation for my projects page
    $('#osfNavMyProjects').addClass('active');
});
