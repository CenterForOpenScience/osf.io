'use strict';
require('css/registrations.css');

var ko = require('knockout');
var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationManager = require('js/registrationUtils').RegistrationManager;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {
    var draftManager = new RegistrationManager(node, '#draftRegistrationScope', '#registrationEditorScope', {
        showEditor: function() {
            $('#editDraftsControl').removeClass('disabled');
            $('#editDraftsControl').tab('show');
        },
        showManager: function() {
            $('#draftsControl').tab('show');
        }
    });
    draftManager.init();

    $('#draftsControl').click(function(event) {
        draftManager.refresh();
    });

    $('#registerNode').click(function(event) {
        event.preventDefault();
        draftManager.beforeRegister();
    });
});
