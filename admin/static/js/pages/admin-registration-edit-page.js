var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;
var $ = require('jquery');
var $osf = require('js/osfHelpers');

$(document).ready(function() {

	var params = context[0];

	var draftEditor = new RegistrationEditor({
	    schemas: '/admin/pre-reg/get_schemas/',
	    update: '/admin/pre-reg/update_draft/{draft_pk}/',
	    approve: '/admin/pre-reg/approve_draft/{draft_pk}/',
	    reject: '/admin/pre-reg/reject_draft/{draft_pk}/',
	    request_revisions: '/admin/pre-reg/reject_draft/{draft_pk}/',
	    home: '/admin/pre-reg/prereg/'
	}, 'registrationEditor', true);

	var draft = new registrationUtils.Draft(params);
	draftEditor.init(draft);
	window.draftEditor = draftEditor;
	$osf.applyBindings(draftEditor, '#draftRegistrationScope');

});
