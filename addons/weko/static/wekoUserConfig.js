/**
* Module that controls the WEKO user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.weko;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');
var ChangeMessageMixin = require('js/changeMessage');


var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#wekoInputCredentials');


function ViewModel(configUrl, accountsUrl) {
    var self = this;

    self.properName = 'WEKO';
    self.selectedRepo = ko.observable();
    self.repositories = ko.observableArray();
    self.swordUrl = ko.observable('');
    self.accessKey = ko.observable('');
    self.secretKey = ko.observable('');
    self.account_url = '/api/v1/settings/weko/accounts/';
    self.accounts = ko.observableArray();

    self.basicAuth = 'Other Repository (Basic Auth)';

    ChangeMessageMixin.call(self);

    /** Reset all fields from WEKO credentials input modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.selectedRepo(null);
        self.swordUrl(null);
        self.secretKey(null);
        self.accessKey(null);
    };

    self.setMessage = function(msg, cls) {
        var self = this;
        self.message(msg);
        self.messageClass(cls || 'text-info');
    };

    /** Send POST request to authorize WEKO */
    self.connectOAuth = function() {
        var self = this;
        // Selection should not be empty
        if(!self.selectedRepo()) {
            self.changeMessage('Please select WEKO repository.', 'text-danger');
            return;
        }
        if(self.selectedRepo() == self.basicAuth) {
            self.connectAccount();
            return;
        }
        console.log('Connect via OAuth: ' + self.selectedRepo());
        window.oauthComplete = function() {
            self.setMessage('');
            var accountCount = self.accounts().length;
            self.updateAccounts().done( function() {
                if (self.accounts().length > accountCount) {
                    self.setMessage('Add-on successfully authorized. To link this add-on to an OSF project, go to the settings page of the project, enable WEKO, and choose content to connect.', 'text-success');
                } else {
                    self.setMessage('Error while authorizing add-on. Please log in to your WEKO account and grant access to the OSF to enable this add-on.', 'text-danger');
                }
            });
        };
        window.open('/oauth/connect/weko/' + self.selectedRepo() + '/');
        $modal.modal('hide');
    };

    /** Send POST request to authorize WEKO */
    self.connectAccount = function() {
        // Selection should not be empty
        if(!self.swordUrl() && !self.accessKey() && !self.secretKey()){
            self.changeMessage('Please enter all a SWORD URL, WEKO username and password.', 'text-danger');
            return;
        }

        if (!self.swordUrl() ){
            self.changeMessage('Please enter your SWORD URL.', 'text-danger');
            return;
        }

        if (!self.accessKey() ){
            self.changeMessage('Please enter a WEKO username.', 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage('Please enter a WEKO password.', 'text-danger');
            return;
        }

        return osfHelpers.postJSON(
            self.account_url,
            ko.toJS({
                sword_url: self.swordUrl,
                access_key: self.accessKey,
                secret_key: self.secretKey
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 400 && xhr.responseJSON.message !== undefined) ? xhr.responseJSON.message : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with WEKO', {
                extra: {
                    url: self.account_url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.updateAccounts = function() {
        return $.ajax({
            url: accountsUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.accessKey = account.oauth_key;
                externalAccount.secretKey = account.oauth_secret;
                return externalAccount;
            }));
            $('#weko-header').osfToggleHeight({height: 160});
        }).fail(function(xhr, status, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: accountsUrl,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.askDisconnect = function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect WEKO Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the WEKO account <strong>' +
                osfHelpers.htmlEscape(account.name) + '</strong>? This will revoke access to WEKO for all projects associated with this account.' +
                '</p>',
            callback: function (confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
                }
            }
        });
    };

    self.disconnectAccount = function(account) {
        var self = this;
        var url = '/api/v1/oauth/accounts/' + account.id + '/';
        var request = $.ajax({
            url: url,
            type: 'DELETE'
        });
        request.done(function(data) {
            self.updateAccounts();
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while removing addon authorization for ' + account.id, {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
        return request;
    };

    self.selectionChanged = function() {
        self.changeMessage('','');
    };

    self.fetch = function() {
        $.ajax({
            url: configUrl,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            var data = response.result;
            self.repositories(data.repositories.concat([self.basicAuth]));
            self.updateAccounts();
        }).fail(function (xhr, textStatus, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET WEKO settings', {
                extra: {
                    url: configUrl,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.updateAccounts();
}

$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);

function WEKOUserConfig(selector, configUrl, accountsUrl) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.configUrl = configUrl;
    self.accountsUrl = accountsUrl;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(configUrl, accountsUrl);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    WEKOViewModel: ViewModel,
    WEKOUserConfig: WEKOUserConfig
};
