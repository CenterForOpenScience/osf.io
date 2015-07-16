'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {

    var draftEditor = new RegistrationEditor({
        schemas: '/api/v1/project/schema/',
        create: node.urls.api + 'draft/',
	submit: node.urls.api + 'draft/{draft_pk}/submit/',
        update: node.urls.api + 'draft/{draft_pk}/',
        get: node.urls.api + 'draft/{draft_pk}/'
    }, 'registrationEditor');

    var draft = new registrationUtils.Draft(window.contextVars.draft);
    draftEditor.init(draft);
    window.draftEditor = draftEditor;
    $osf.applyBindings(draftEditor, '#draftRegistrationScope');

});
