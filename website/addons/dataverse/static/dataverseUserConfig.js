/**
* Module that controls the Dataverse user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
require('knockout.punches');
ko.punches.enableAll();
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');

var language = require('js/osfLanguage').Addons.dataverse;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');

var ConnectedProject = addonSettings.ConnectedProject; // TODO
var ExternalAccount = addonSettings.ExternalAccount;

var modal = $('#dataverseInputCredentials');


function ViewModel(url) {
    var self = this;
    var otherString = 'Other (Please Specify)';

    self.properName = 'Dataverse';
    self.apiToken = ko.observable();
    self.urls = ko.observable({});
    self.hosts = ko.observableArray([]);
    self.selectedHost = ko.observable();    // Host specified in select element
    self.customHost = ko.observable();      // Host specified in input element
    // Whether the initial data has been loaded
    self.loaded = ko.observable(false);
    self.accounts = ko.observableArray();

    // Designated host, specified from select or input element
    self.host = ko.pureComputed(function() {
        return self.useCustomHost() ? self.customHost() : self.selectedHost();
    });
    // Hosts visible in select element. Includes presets and "Other" option
    self.visibleHosts = ko.pureComputed(function() {
        return self.hosts().concat([otherString]);
    });
    // Whether to use select element or input element for host designation
    self.useCustomHost = ko.pureComputed(function() {
        return self.selectedHost() === otherString;
    });
    self.showApiTokenInput = ko.pureComputed(function() {
        return typeof self.selectedHost() !== 'undefined';
    });
    self.tokenUrl = ko.pureComputed(function() {
       return self.host() ? 'https://' + self.host() + '/account/apitoken' : undefined;
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    /** Reset all fields from Dataverse host selection modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.apiToken(undefined);
        self.selectedHost(undefined);
        self.customHost(undefined);
    };

    self.updateAccounts = function() {
        var url = self.urls().accounts;
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.dataverseHost = account.host;
                externalAccount.dataverseUrl = account.host_url;
                return externalAccount;
            }));
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

    /** Send POST request to authorize Dataverse */
    self.sendAuth = function() {
        var url = self.urls().create;
        return osfHelpers.postJSON(
            url,
            ko.toJS({
                host: self.host,
                api_token: self.apiToken
            })
        ).done(function() {
            self.clearModal();
            modal.modal('hide');
            self.updateAccounts();
        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with Dataverse', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    };

    // TODO: Should next two methods be inherited from js/addonSettings?
    self.askDisconnect = function(account) {
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
    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        var data = response.result;
        self.urls(data.urls);
        self.hosts(data.hosts);
        self.loaded(true);
        self.updateAccounts();
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(language.userSettingsError, 'text-warning');
        Raven.captureMessage('Could not GET Dataverse settings', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
}

function DataverseUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, '#dataverseAddonScope');
}
module.exports = DataverseUserConfig;
