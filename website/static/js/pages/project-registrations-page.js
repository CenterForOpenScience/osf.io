'use strict';
require('css/registrations.css');

var $ = require('jquery');

var $osf = require('js/osfHelpers');
var RegistrationManager = require('js/registrationUtils').RegistrationManager;

var ctx = window.contextVars;
var node = window.contextVars.node;

$(document).ready(function() {

    $('#registrationsTabs').tab();
    $('#registrationsTabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    });

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

    $('#registerNode').click(function(event) {
        event.preventDefault();
        draftManager.beforeRegister();        
    });
});
