/**
* Module that controls the Swift user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.swift;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');
var ChangeMessageMixin = require('js/changeMessage');


var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#swiftInputCredentials');


function ViewModel(url) {
    var self = this;

    self.properName = 'Swift';
    self.authVersion = ko.observable('v2');
    self.authUrl = ko.observable();
    self.accessKey = ko.observable();
    self.secretKey = ko.observable();
    self.tenantName = ko.observable();
    self.userDomainName = ko.observable();
    self.projectDomainName = ko.observable();
    self.account_url = '/api/v1/settings/swift/accounts/';
    self.accounts = ko.observableArray();

    ChangeMessageMixin.call(self);

    /** Reset all fields from Swift credentials input modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.authVersion('v2');
        self.authUrl(null);
        self.accessKey(null);
        self.userDomainName(null);
        self.secretKey(null);
        self.tenantName(null);
        self.projectDomainName(null);
    };
    /** Send POST request to authorize Swift */
    self.connectAccount = function() {
        var authVersion = null;
        if (self.authVersion() == 'v2') {
            authVersion = '2';
        }else if (self.authVersion() == 'v3') {
            authVersion = '3';
        }else{
            self.changeMessage('Please enter valid Identity version.', 'text-danger');
            return;
        }
        // Selection should not be empty
        if(!self.authUrl() && !self.accessKey() && !self.secretKey() && !self.tenantName()){
            self.changeMessage('Please enter all an API authentication URL, tenant name, username and password.', 'text-danger');
            return;
        }

        if (!self.authUrl() ){
            self.changeMessage('Please enter your authentication URL.', 'text-danger');
            return;
        }

        if (!self.accessKey() ){
            self.changeMessage('Please enter an API username.', 'text-danger');
            return;
        }
        if(authVersion == '3' && !self.userDomainName()) {
            self.changeMessage('Please enter a domain name for your username.', 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage('Please enter an API password.', 'text-danger');
            return;
        }

        if (!self.tenantName() ){
            self.changeMessage('Please enter your tenant name.', 'text-danger');
            return;
        }
        if(authVersion == '3' && !self.projectDomainName()) {
            self.changeMessage('Please enter a domain name for your project.', 'text-danger');
            return;
        }
        return osfHelpers.postJSON(
            self.account_url,
            ko.toJS({
                auth_version: authVersion,
                auth_url: self.authUrl,
                access_key: self.accessKey,
                secret_key: self.secretKey,
                tenant_name: self.tenantName,
                user_domain_name: self.userDomainName,
                project_domain_name: self.projectDomainName
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 400 && xhr.responseJSON.message !== undefined) ? xhr.responseJSON.message : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with Swift', {
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
                externalAccount.authVersion = account.authVersion;
                externalAccount.accessKey = account.oauth_key;
                externalAccount.secretKey = account.oauth_secret;
                externalAccount.tenantName = account.tenant_name;
                externalAccount.userDomainName = account.user_domain_name;
                externalAccount.projectDomainName = account.project_domain_name;
                return externalAccount;
            }));
            $('#swift-header').osfToggleHeight({height: 160});
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
            title: 'Disconnect Swift Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the Swift account <strong>' +
                osfHelpers.htmlEscape(account.name) + '</strong>? This will revoke access to Swift for all projects associated with this account.' +
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

function SwiftUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    SwiftViewModel: ViewModel,
    SwiftUserConfig: SwiftUserConfig
};
