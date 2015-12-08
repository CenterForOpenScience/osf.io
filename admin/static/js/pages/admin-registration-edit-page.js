'use strict';

var $ = require('jQuery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;

$(document).ready(function() {

    var draftData = window.contextVars.draft;

    var draftEditor = new RegistrationEditor({
	update: '/admin/pre-reg/drafts/{draft_pk}/update/',
	approve: '/admin/pre-reg/drafts/{draft_pk}/approve/',
	reject: '/admin/pre-reg/drafts/{draft_pk}/reject/',
        list: '/admin/pre-reg/'
    }, 'registrationEditor', true);

    var draft = new registrationUtils.Draft(draftData);
    draftEditor.init(draft);
    $osf.applyBindings(draftEditor, '#draftRegistrationScope');
});
