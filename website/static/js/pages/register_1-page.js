'use strict';
var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('osfHelpers');

var MetaData = require('../metadata_1.js');
var ctx = window.contextVars;
/**
    * Unblock UI and display error modal
    */
function registration_failed() {
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
        if (response.status === 'success') {
            window.location.href = response.result;
        }
        else if (response.status === 'error') {
            registration_failed();
        }
    }).fail(function() {
        registration_failed();
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
