'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(function() {

    var draftEditor = new RegistrationEditor({
        schemas: '/api/v1/project/schemas/',
        create: node.urls.api + 'drafts/',
        submit: node.urls.api + 'drafts/{draft_pk}/submit/',
        update: node.urls.api + 'drafts/{draft_pk}/',
        get: node.urls.api + 'drafts/{draft_pk}/',
        draftRegistrations: node.urls.web + 'registrations?tab=drafts'
    }, 'registrationEditor');

    var draft = new registrationUtils.Draft(ctx.draft);
    draftEditor.init(draft);
    $osf.applyBindings(draftEditor, '#draftRegistrationScope');
});
