/**
* Module that controls the CloudFiles user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.cloudfiles;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');
var ChangeMessageMixin = require('js/changeMessage');


var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#cloudfilesInputCredentials');


function ViewModel(url) {
    var self = this;

    self.properName = 'Cloud Files';
    self.username = ko.observable();
    self.secretKey = ko.observable();
    self.account_url = '/api/v1/settings/cloudfiles/accounts/';
    self.accounts = ko.observableArray();

    ChangeMessageMixin.call(self);

    /** Reset all fields from Cloud Files credentials input modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.username(null);
        self.secretKey(null);
    };

    self.connectAccount = function() {
        // Selection should not be empty
        if( !self.username() && !self.secretKey() ){
            self.changeMessage('Please enter both an username and API key.', 'text-danger');
            return;
        }

        if (!self.username() ){
            self.changeMessage('Please enter a username.', 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage('Please enter an API key.', 'text-danger');
            return;
        }
        return osfHelpers.postJSON(
            self.account_url,
            ko.toJS({
                username: self.username,
                secretKey: self.secretKey,
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 400 && xhr.responseJSON.message !== undefined) ? xhr.responseJSON.message : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with Cloud Files', {
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
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.username = account.oauth_key;
                externalAccount.secretKey = account.oauth_secret;
                return externalAccount;
            }));
            $('#cloudfiles-header').osfToggleHeight({height: 160});
        }).fail(function(xhr, status, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
    };

    self.askDisconnect = function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect Cloud Files Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the Cloud Files account <strong>' +
                osfHelpers.htmlEscape(account.name) + '</strong>? This will revoke access to Cloud' +
            ' Files for all projects associated with this account.' +
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

    self.updateAccounts();
}

$.extend(ViewModel.prototype, ChangeMessageMixin.prototype);

function CloudFilesUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    CloudFilesViewModel: ViewModel,
    CloudFilesUserConfig: CloudFilesUserConfig
};
