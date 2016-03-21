'use strict';

var $ = require('jquery');
var ko = require('knockout');

ko.punches.enableAll();

var _myProjects = require('js/myProjects.js');
var Projects = _myProjects.MyProjects;
var LinkObject = _myProjects.LinkObject;
var InstitutionNodes = require('js/institutionNodes.js');
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.


$(document).ready(function() {
    var institutionId = window.contextVars.institution.id;
    new InstitutionNodes('#inst', window.contextVars);
    m.mount(document.getElementById('fileBrowser'), m.component(Projects, {
        wrapperSelector : '#fileBrowser',
        systemCollections:[
            new LinkObject('collection', { path : 'institutions/' + institutionId + '/nodes/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'nodes'}, 'All Projects'),
            new LinkObject('collection', { path : 'institutions/' + institutionId + '/registrations/', query : { 'related_counts' : true, 'page[size]'  : 12, 'embed' : 'contributors', 'filter[parent]' : 'null'}, systemCollection : 'registrations'}, 'All Registrations'),
        ],
        initialBreadcrumbs: [new LinkObject('collection', { path : 'users/me/nodes/', query : { 'related_counts' : 'children', 'embed' : 'contributors' }, systemCollection : 'nodes'}, 'All Projects')],
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
