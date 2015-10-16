var registrationUtils = require('js/registrationUtils');
var RegistrationEditor = registrationUtils.RegistrationEditor;
var $ = require('jquery');
var $osf = require('js/osfHelpers');

$(document).ready(function() {

	var params = context[0];

	var draftEditor = new RegistrationEditor({
	    schemas: '/get-schemas/',
	    update: '/update-draft/{draft_pk}/',
	    approve: '/approve-draft/{draft_pk}/',
	    reject: '/reject-draft/{draft_pk}/',
	    request_revisions: '/reject-draft/{draft_pk}/',
	    home: '/prereg/'
	}, 'registrationEditor');

	var draft = new registrationUtils.Draft(params);
	draftEditor.init(draft);
	window.draftEditor = draftEditor;
	$osf.applyBindings(draftEditor, '#draftRegistrationScope');

});
