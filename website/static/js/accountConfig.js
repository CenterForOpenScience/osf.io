'use strict';

var $ = require('jquery');
var ko = require('knockout');
require('knockout-validation');
require('knockout-punches');
ko.punches.enableAll();
var $osf = require('osfHelpers');

var ViewModel = function() {
    var self = this;
    self.username = ko.observable();
    self.newUsername = ko.observable().extend({
        required: {params: true, message: 'This field is required.'},
        email: true,
        validation: {
            validator: function(val, username) {
                return val !== username;
            },
            'message': 'Please enter a new email.',
            params: self.username
        }
    });
    self.confirmNewUsername = ko.observable().extend({
        required: {params: true, message: 'This field is required.'},
        email: true,
        validation: [
            {
                validator: function(val, username) {
                    return val !== username;
                },
                message: 'Please enter a new email.',
                params: self.username},
            {
                validator: function(val, newUsername) {
                    return val === newUsername;
                },
                message: 'Confirmed email address does not match.',
                params: self.newUsername}
        ]
    });

    var validated = ko.validatedObservable(self);
    self.isValid = ko.computed(function() {
        return validated.isValid();
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-success');
    self.showMessages = ko.observable(false);

    self.getUsername = function () {
        $.ajax({
            url: '/api/v1/settings/account/',
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            self.username(response.username);
        });
    };

    self.getUsername();

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    self.submit = function() {
        if (self.isValid()) {
            var payload = {
                'unconfirmed_username': self.newUsername()
            };
            var request = $osf.postJSON('/api/v1/settings/account/email/', payload);
            request.done(function () {
                var message = 'Settings updated. Please check ' + self.newUsername() + ' to confirm your email address.';
                self.changeMessage(message, 'text-success');
            });
            request.fail(function (xhr) {
                if (xhr.responseJSON.error_type === 'invalid_username') {
                    var message = "Could not update settings. A user with this username already exists.";
                    self.changeMessage(message, 'text-danger', 5000)
                } else {
                    self.changeMessage("Could not update settings.", 'text-danger', 5000)
                }
            });
        } else {
            self.showMessages(true);
        }
    };
};

// API
function AccountSettingsViewModel(selector) {
    var self = this;
    self.viewModel = new ViewModel();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AccountSettingsViewModel;