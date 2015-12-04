var $ = require('jQuery');

var $osf = require('js/osfHelpers');
var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;

$(document).ready(function() {

    var draftData = window.contextVars.draft;

    var draftEditor = new RegistrationEditor({
	update: '/admin/pre-reg/update_draft/{draft_pk}/',
	approve: '/admin/pre-reg/approve_draft/{draft_pk}/',
	reject: '/admin/pre-reg/reject_draft/{draft_pk}/',
        list: '/admin/pre-reg/'
    }, 'registrationEditor', true);

    var draft = new registrationUtils.Draft(draftData);
    draftEditor.init(draft);
    $osf.applyBindings(draftEditor, '#draftRegistrationScope');
});
