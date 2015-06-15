'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

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

function postRegisterNode() {
    $('#registration_template').children().remove();
    $osf.block('<h4>Your registration request was submitted successfully. Files are being copied to the newly created registration, and you will receive an email notification containing a link to the registration when the copying is finished.</h4> <br /> <h4>Click <a href="' + ctx.node.urls.web + 'registrations/">here</a> to return to the registrations page.</h4>');
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
            postRegisterNode();
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
                    'Invalid embargo end date',
                    'Please choose a date more than two days, but less than four years, from today.',
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

        $.ajax({
            url: ctx.node.urls.api + 'beforeregister/',
            contentType: 'application/json',
            success: function(response) {
                if (response.prompts && response.prompts.length) {
                    bootbox.confirm(
                        $osf.joinPrompts(response.prompts, 'Are you sure you want to register this project?'),
                        function(result) {
                            if (result) {
                                registerNode(data);
                            }
                        }
                    );
                } else {
                    registerNode(data);
                }
            }
        });

        return false;

    });
});
