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

var ExternalAccount = addonSettings.ExternalAccount;

var $modal = $('#gitlabInputCredentials');


function ViewModel(url) {
    var self = this;
    const otherString = 'Other (Please Specify)';

    self.properName = 'GitLab';
    self.clientId = ko.observable();
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
        return Boolean(self.selectedHost());
    });
    self.tokenUrl = ko.pureComputed(function() {
        return self.host() ? 'https://' + self.host() + '/profile/personal_access_tokens' : null;
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    /** Reset all fields from GitLab host selection modal */
    self.clearModal = function() {
        self.message('');
        self.messageClass('text-info');
        self.clientId(null);
        self.selectedHost(null);
        self.customHost(null);
    };

    self.updateAccounts = function() {
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
    };

    /** Send POST request to authorize GitLab */
    self.sendAuth = function() {
        // Selection should not be empty
        if( !self.selectedHost() ){
            self.changeMessage("Please select a GitLab repository.", 'text-danger');
            return;
        }

        if ( !self.useCustomHost() && !self.clientId() ) {
            self.changeMessage("Please enter your Personal Access Token.", 'text-danger');
            return;
        }

        if ( self.useCustomHost() && (!self.customHost() || !self.clientId()) ) {
            self.changeMessage("Please enter a GitLab host and your Personal Access Token.", 'text-danger');
            return;
        }

        var url = self.urls().create;

        return osfHelpers.postJSON(
            url,
            ko.toJS({
                host: self.host,
                clientId: self.clientId
            })
        ).done(function() {
            self.updateAccounts();
            self.clearModal();
            $modal.modal('hide');

        }).fail(function(xhr, textStatus, error) {
            var errorMessage = (xhr.status === 401) ? 'Auth Error' : 'Other error';
            self.changeMessage(errorMessage, 'text-danger');
            Raven.captureMessage('Could not authenticate with GitLab', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.askDisconnect = function(account) {
        var self = this;
        bootbox.confirm({
            title: 'Disconnect GitLab Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the GitLab account on <strong>' +
                osfHelpers.htmlEscape(account.name) + '</strong>? This will revoke access to GitLab for all projects associated with this account.' +
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
            Raven.captureMessage('Could not GET GitLab settings', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.selectionChanged = function() {
        self.changeMessage('','');
    };

}

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
