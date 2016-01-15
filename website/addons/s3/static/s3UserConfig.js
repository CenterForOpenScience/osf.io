/**
* Module that controls the S3 user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
require('knockout.punches');
ko.punches.enableAll();
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.s3;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');

var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#s3InputCredentials');


function ViewModel(url) {
    var self = this;

    self.properName = 'Amazon S3';
    self.accessKey = ko.observable();
    self.secretKey = ko.observable();
    self.urls = ko.observable({});
    // Whether the initial data has been loaded
    self.loaded = ko.observable(false);
    self.accounts = ko.observableArray();

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    /** Reset all fields from S3 credentials input modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.accessKey(null);
        self.secretKey(null);
    };

    self.updateAccounts = function() {
        var url = self.urls().accounts;
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.accessKey = account.oauth_key;
                externalAccount.secretKey = account.oauth_secret;
                return externalAccount;
            }));
            $('.addon-auth-table').osfToggleHeight({height: 140});
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while updating addon account', {
                url: url,
                status: status,
                error: error
            });
        });
        return request;
    };

    /** Send POST request to authorize S3 */
    self.sendAuth = function() {
        // Selection should not be empty
        if( !self.accessKey() && !self.secretKey() ){
            self.changeMessage("Please enter both an API access key and secret key.", 'text-danger');
            return;
        }

        if (!self.accessKey() ){
            self.changeMessage("Please enter an API access key.", 'text-danger');
            return;
        }

        if (!self.secretKey() ){
            self.changeMessage("Please enter an API secret key.", 'text-danger');
            return;
        }

        var url = self.urls().create;

        return osfHelpers.postJSON(
            url,
            ko.toJS({
                access_key: self.accessKey,
                secret_key: self.secretKey,
            })
        ).done(function() {
            self.clearModal();
            $modal.modal('hide');
            self.updateAccounts();

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with S3', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    };

    self.askDisconnect = function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect Amazon S3 Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the S3 account on <strong>' +
                account.name + '</strong>? This will revoke access to S3 for all projects associated with this account.' +
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
                url: url,
                status: status,
                error: error
            });
        });
        return request;
    };

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

    // Update observables with data from the server
    self.fetch = function() {
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            var data = response.result;
            self.urls(data.urls);
            self.hosts(data.hosts);
            self.loaded(true);
            self.updateAccounts();
        }).fail(function (xhr, textStatus, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET S3 settings', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    };

    self.selectionChanged = function() {
        self.changeMessage('','');
    };

}

function S3UserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    S3ViewModel: ViewModel,
    S3UserConfig: S3UserConfig
};
