'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var language = require('js/osfLanguage').registrations;

var MetaData = require('js/metadata_1.js');
var ctx = window.contextVars;

require('pikaday-css');

/**
    * Unblock UI and display error modal
    */
function registrationFailed() {
    $osf.unblock();
    bootbox.alert('Registration failed');
}

function registerNode(data) {

    // Block UI until request completes
    $osf.block();

    // POST data
    $.ajax({
        url:  ctx.node.urls.api + 'register/' + ctx.regTemplate + '/',
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        if (response.status === 'initiated') {
            $osf.unblock();
            window.location.assign(response.urls.registrations);
        }
        else if (response.status === 'error') {
            registrationFailed();
        }
    }).fail(function() {
        registrationFailed();
    });

    // Stop event propagation
    return false;

}

$(document).ready(function() {

    // Don't submit form on enter; must use $.delegate rather than $.on
    // to catch dynamically created form elements
    $('#registration_template').delegate('input, select', 'keypress', function(event) {
        return event.keyCode !== 13;
    });

    var registrationViewModel = new MetaData.ViewModel(
        ctx.regSchema,
        ctx.registered,
        [ctx.node.id].concat(ctx.node.children)
    );
    // Apply view model
    ko.applyBindings(registrationViewModel, $('#registration_template')[0]);
    registrationViewModel.updateIdx('add', true);

    if (ctx.registered) {
        registrationViewModel.unserialize(ctx.regPayload);
    }

    $('#registration_template form').on('submit', function() {

        // If embargo is requested, verify its end date, and inform user if date is out of range
        if (registrationViewModel.embargoAddon.requestingEmbargo()) {
            if (!registrationViewModel.embargoAddon.isEmbargoEndDateValid()) {
                registrationViewModel.continueText('');
                $osf.growl(
                    language.invalidEmbargoTitle,
                    language.invalidEmbargoMessage,
                    'warning'
                );
                $('#endDatePicker').focus();
                return false;
            }
        }
        // Serialize responses
        var serialized = registrationViewModel.serialize(),
            data = serialized.data,
            complete = serialized.complete;

        // Clear continue text and stop if incomplete
        if (!complete) {
            registrationViewModel.continueText('');
            return false;
        }

        $osf.block();
        $.ajax({
            url: ctx.node.urls.api + 'beforeregister/',
            contentType: 'application/json',
            success: function(response) {
                var preRegisterWarnings = function() {
                    bootbox.confirm(
                        $osf.joinPrompts(response.prompts, language.registerConfirm),
                        function(result) {
                            if (result) {
                                registerNode(data);
                            }
                        }
                    );
                };
                var preRegisterErrors = function(confirm, reject) {
                    bootbox.confirm(
                        $osf.joinPrompts(
                            response.errors, 
                            'Before you continue...'
                        ) + '<br /><hr /> ' + language.registerSkipAddons,
                        function(result) {
                            if(result) {
                                confirm();
                            }
                        }
                    );
                };

                if (response.errors && response.errors.length) {
                    preRegisterErrors(preRegisterWarnings);
                }
                else if (response.prompts && response.prompts.length) {
                    preRegisterWarnings();
                } 
                else {
                    registerNode(data);
                }
            }
        }).always(function() {
            $osf.unblock();
        });
        return false;
    });
});
