'use strict';

var bootbox = require('bootbox');
////////////////
// Public API //
////////////////

function CitationUserSettings(name) {
    var selector = '#' + name + 'UserSettings';
    var $ = require('jquery');
    var ko = require('knockout');
    var $osf = require('osfHelpers');

    var CitationAccount = function (display_name, id) {
        var self = this;
        self.display_name = display_name;
        self.id = id;
    };

    var CitationUserSettingsViewModel = function () {
        var self = this;
        self.accounts = ko.observableArray();

        self.updateAccounts = function () {
            var request = $.ajax({
                url: '/api/v1/settings/' + name + '/accounts/'
            });
            request.done(function (data) {
                self.accounts([]);
                ko.utils.arrayMap(data.accounts, function (acct) {
                    self.accounts.push(
                        new CitationAccount(acct.display_name, acct.id)
                    )
                })
            });
            request.fail(function () {
                console.log('fail');
            });
        };

        self.connectAccount = function () {
            window.oauth_complete = function () {
                self.updateAccounts();
            };
            window.open('/oauth/connect/' + name + '/');
        };

        self.disconnectAccount = function (account) {
            var request = $.ajax({
                url: '/api/v1/oauth/accounts/' + account.id + '/',
                type: 'DELETE'
            });
            request.done(function (data) {
                self.updateAccounts();
            });
        };

        self.askDisconnect = function(account) {
        bootbox.confirm({
            title: 'Delete account?',
            message: '<p class="overflow">' +
            'Are you sure you want to delete <strong>' +
            account.display_name + '</strong>?' +
            '</p>',
            callback: function (confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            }
        });
    };

        self.updateAccounts();

    };

    var self = this;
    self.selector = selector;
    self.$element = $(selector);
    self.viewModel = new CitationUserSettingsViewModel();
    ko.applyBindings(self.viewModel, self.$element[0]);
}

module.exports = CitationUserSettings;