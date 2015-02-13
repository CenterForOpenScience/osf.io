'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var $osf = require('osfHelpers');

ko.punches.enableAll();

////////////////
// Public API //
////////////////

var CitationAccount = function(name, id) {
    this.name = name;
    this.id = id;
};

var SettingsViewModel = function (name) {
    this.name = name;
    this.accounts = ko.observableArray();
};

$.extend(SettingsViewModel.prototype, {
    connectAccount: function () {
        var self = this;
        window.oauthComplete = function () {
            self.updateAccounts();
        };
        window.open('/oauth/connect/' + self.name + '/');
    },
    askDisconnect: function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Delete account?',
            message: '<p class="overflow">' +
                'Are you sure you want to delete account <strong>' +
                account.name + '</strong>?' +
                '</p>',
            callback: function (confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            }
        });
    },
    disconnectAccount: function(account) {
        var self = this;
        $.ajax({
            url: '/api/v1/oauth/accounts/' + account.id + '/',
            type: 'DELETE'
        }).done(function(data) {
            self.updateAccounts();
        }).fail(function() {
            console.log('fail');
        });
    },
    updateAccounts: function() {
        var self = this;
        $.get('/api/v1/settings/' + self.name + '/accounts/').done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return new CitationAccount(account.display_name, account.id);
            }));
        }).fail(function() {
            console.log('fail');
        });
    }
});

function CitationUserSettings(name, selector) {
    this.$element = $(selector);
    this.viewModel = new SettingsViewModel(name);
    ko.applyBindings(this.viewModel, this.$element[0]);
    this.viewModel.updateAccounts();
}

module.exports = CitationUserSettings;
