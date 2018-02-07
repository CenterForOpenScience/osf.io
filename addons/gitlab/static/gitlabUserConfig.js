/**
* Module that controls the GitLab user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.gitlab;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');
var oop = require('js/oop');
var OAuthAddonSettingsViewModel = require('js/addonSettings.js').OAuthAddonSettingsViewModel;

var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#gitlabInputCredentials');


var ViewModel = oop.extend(OAuthAddonSettingsViewModel,{
    constructor: function(url){
        var self = this;
        self.name = 'gitlab';
        self.properName = 'GitLab';
        self.accounts = ko.observableArray();
        self.message = ko.observable('');
        self.messageClass = ko.observable('');
        const otherString = 'Other (Please Specify)';

        self.url = url;
        self.properName = 'GitLab';
        self.apiToken = ko.observable();
        self.urls = ko.observable({});
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();    // Host specified in select element
        self.customHost = ko.observable();      // Host specified in input element
        // Whether the initial data has been loaded
        self.loaded = ko.observable(false);

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
            return Boolean(self.selectedHost());
        });
        self.tokenUrl = ko.pureComputed(function() {
            return self.host() ? 'https://' + self.host() + '/profile/personal_access_tokens' : null;
        });
    },
    clearModal: function() {
        /** Reset all fields from GitLab host selection modal */
        var self = this;
        self.message('');
        self.messageClass('text-info');
        self.apiToken(null);
        self.selectedHost(null);
        self.customHost(null);
    },
    updateAccounts: function() {
        var self = this;
        var url = self.urls().accounts;
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                var externalAccount =  new ExternalAccount(account);
                externalAccount.gitlabHost = account.host;
                externalAccount.gitlabUrl = account.host_url;
                return externalAccount;
            }));
            $('#gitlab-header').osfToggleHeight({height: 160});
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage('Error while updating addon account', {
                extra: {
                    url: url,
                    status: status,
                    error: error
                }
            });
        });
        return request;
    },
    authSuccessCallback: function() {
        // Override for NS-specific auth success behavior
        // TODO: generalize this when rewriting addon configs for ember
        return;
    },
    sendAuth:  function() {
        /** Send POST request to authorize GitLab */
        // Selection should not be empty
        var self = this;
        if( !self.selectedHost() ){
            self.setMessage("Please select a GitLab repository.", 'text-danger');
            return;
        }

        if ( !self.useCustomHost() && !self.apiToken() ) {
            self.setMessage("Please enter your Personal Access Token.", 'text-danger');
            return;
        }

        if ( self.useCustomHost() && (!self.customHost() || !self.apiToken()) ) {
            self.setMessage("Please enter a GitLab host and your Personal Access Token.", 'text-danger');
            return;
        }

        var url = self.urls().create;

        return osfHelpers.postJSON(
            url,
            ko.toJS({
                host: self.host,
                access_token: self.apiToken
            })
        ).done(function() {
            self.updateAccounts();
            self.clearModal();
            $modal.modal('hide');
            self.authSuccessCallback();
        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? 'Auth Error' : 'Other error';
            self.setMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with GitLab', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    },
    fetch: function() {
        // Update observables with data from the server
        var self = this;
        $.ajax({
            url: self.url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            var data = response.result;
            self.urls(data.urls);
            self.hosts(data.hosts);
            self.loaded(true);
            self.updateAccounts();
        }).fail(function (xhr, textStatus, error) {
            self.setMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET GitLab settings', {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    },
    selectionChanged: function() {
        var self = this;
        self.setMessage('','');
    }
});

function GitLabUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    GitLabViewModel: ViewModel,
    GitLabUserConfig: GitLabUserConfig    // for backwards-compat
};
