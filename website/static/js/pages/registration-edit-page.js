'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationEditor = require('js/registrationUtils').RegistrationEditor;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {

	var draftEditor = new RegistrationEditor({
		schemas: '/api/v1/project/schema/',
        create: node.urls.api + 'draft/',
        update: node.urls.api + 'draft/{draft_pk}/',
        get: node.urls.api + 'draft/{draft_pk}/'
    }, 'registrationEditor', {
        addDraft: function(draft) {
            if (!self.drafts().filter(function(d) {
                return draft.pk === d.pk;
            }).length) {
                self.drafts.unshift(draft);
            }
        },
        updateDraft: function(draft) {
            self.drafts.remove(function(d) {
                return d.pk === draft.pk;
            });
            self.drafts.unshift(draft);
        }
    });
	var draft = ko.observable(window.contextVars['draft']);
	draft.schema = ko.observable();
	var newDraft = draftEditor.init(draft);
	$osf.applyBindings(draftEditor, '#draftRegistrationScope');

});
