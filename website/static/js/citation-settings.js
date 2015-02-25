'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('osfHelpers');

ko.punches.enableAll();

////////////////
// Public API //
////////////////

var CitationAccount = function(name, id) {
    this.name = name;
    this.id = id;
};

var SettingsViewModel = function(name) {
    this.name = name;
    this.properName = name.charAt(0).toUpperCase() + name.slice(1);
    this.accounts = ko.observableArray();
    this.message = ko.observable('');
    this.messageClass = ko.observable('');
};

$.extend(SettingsViewModel.prototype, {
    setMessage: function(msg, cls){
	this.message(msg);
	this.messageClass(cls || '');
    },
    connectAccount: function() {
        var self = this;
        window.oauthComplete = function() {
            self.updateAccounts();
	    self.setMessage('Add-on successfully authorized. To link this add-on to an OSF project, go to the settings page of the project, enable ' + self.properName + ', and choose content to connect.', '.text-success');
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
            callback: function(confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            }
        });
    },
    disconnectAccount: function(account) {
        var self = this;
        var url = '/api/v1/oauth/accounts/' + account.id + '/';
        $.ajax({
            url: url,
            type: 'DELETE'
        }).done(function(data) {
            self.updateAccounts();
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Error while removing addon authorization for ' + account.id, {
                url: url, status: status, error: error
            });
        });
    },
    updateAccounts: function() {
        var self = this;
        var url = '/api/v1/settings/' + self.name + '/accounts/';
        $.get(url).done(function(data) {
            self.accounts(data.accounts.map(function(account) {
                return new CitationAccount(account.display_name, account.id);
            }));
        }).fail(function(xhr, status, error) {
            Raven.captureMessage('Error while updating addon account', {
                url: url, status: status, error: error
            });
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
