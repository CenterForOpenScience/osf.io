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
        self.allNodes(response.data);
    }).fail(function(response){
    });
};


$(document).ready(function() {
    var self = this;
    var institutionId = window.contextVars.institution.id;
    self.viewModel = new InstitutionViewModel();
    $osf.applyBindings(self.viewModel, '#inst');
    m.mount(document.getElementById('fileBrowser'), m.component(FileBrowser, {
        wrapperSelector : '#fileBrowser',
        systemCollections:[
            new LinkObject('collection', { path : 'institutions/' + institutionId + '/nodes/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'nodes'}, 'All Projects'),
            new LinkObject('collection', { path : 'institutions/' + institutionId + '/registrations/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'registrations'}, 'All Registrations'),
        ],
        viewOnly: true,
        projectOrganizerOptions: {
            resolveToggle: function(){
                return '';
            }
        },
        institutionId: institutionId,
    }));
    setTimeout(function(){
        if($('#inst .spinner-loading-wrapper').length > 0) {
            $('#inst').append('<div class="text-danger text-center text-bigger">This is taking longer than normal. <br>  Try reloading the page. If the problem persist contact us at support@cos.io.</div>');
        }
    }, 10000);
});
