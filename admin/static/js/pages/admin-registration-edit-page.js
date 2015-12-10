'use strict';

var $ = require('jquery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;

$(document).ready(function() {

    var draftData = window.contextVars.draft;

    var draftEditor = new RegistrationEditor({
	update: '/admin/pre_reg/drafts/{draft_pk}/update/',
	approve: '/admin/pre_reg/drafts/{draft_pk}/approve/',
	reject: '/admin/pre_reg/drafts/{draft_pk}/reject/',
        list: '/admin/pre_reg/'
    }, 'registrationEditor', true);

    var draft = new registrationUtils.Draft(draftData);
    draftEditor.init(draft);
    $osf.applyBindings(draftEditor, '#draftRegistrationScope');
});
