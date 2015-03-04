'use strict';

var ko = require('knockout');
require('knockout-punches');
var $ = require('jquery');
var $osf = require('osfHelpers');
ko.punches.enableAll();

var ViewModel = function() {
    var self = this;
    self.username = ko.observable();
    self.newUsername = ko.observable();
    self.confirmNewUsername = ko.observable();
    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-success');

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
    };
};

// API
function AccountSettingsViewModel(selector) {
    var self = this;
    self.viewModel = new ViewModel();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AccountSettingsViewModel;