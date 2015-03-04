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

    self.submit = function() {
        var payload = {
            'unconfirmed_username': self.newUsername()
        };
        var request = $osf.postJSON('/api/v1/settings/account/email/', payload);
    };
};

// API
function AccountSettingsViewModel(selector) {
    var self = this;
    self.viewModel = new ViewModel();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = AccountSettingsViewModel;