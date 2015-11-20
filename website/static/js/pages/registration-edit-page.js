'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;
var ContribManager = require('js/contribManager');
var ContribAdder = require('js/contribAdder');

var ctx = window.contextVars;
var node = window.contextVars.node;

var draftEditor = new RegistrationEditor({
    schemas: '/api/v1/project/schemas/',
    create: node.urls.api + 'drafts/',
    submit: node.urls.api + 'drafts/{draft_pk}/submit/',
    update: node.urls.api + 'drafts/{draft_pk}/',
    get: node.urls.api + 'drafts/{draft_pk}/',
    draftRegistrations: node.urls.web + 'registrations/#drafts'
}, 'registrationEditor');

var draft = new registrationUtils.Draft(ctx.draft);
draftEditor.init(draft);
$(function() {

    var callback = function(data) {
        draftEditor.contributors($.map(data.contributors, function(c){ return c.fullname; }));
    };
    var adder = new ContribAdder(
        '#addContributors',
        node.title,
        node.id,
        null,
        null,
        {async: true, callback: callback}
    );

    $('.admin-info').popover({
        trigger: 'hover'
    });

    var contributorsUrl = node.urls.api + 'get_contributors/';
    $.getJSON(contributorsUrl).done(function(data) {
        new ContribManager('#manageContributors', data.contributors, data.contributors, $osf.currentUser, false);
    });

    $osf.applyBindings(draftEditor, '#draftRegistrationScope');

});
