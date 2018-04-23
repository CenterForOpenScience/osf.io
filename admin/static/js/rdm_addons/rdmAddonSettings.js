// Copied from website/static/js/addonSettings.js
'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var oop = require('js/oop');

var $osf = require('js/osfHelpers');


var ConnectedProject = function(data) {
    var self = this;
    self.title = data.title;
    self.id = data.id;
    self.urls = data.urls;
};

var ExternalAccount = oop.defclass({
    constructor: function(data) {
        var self = this;
        self.name = data.display_name;
        self.id = data.id;
        self.profileUrl = data.profile_url;
        self.providerName = data.provider_name;

        self.connectedNodes = ko.observableArray();

        ko.utils.arrayMap(data.nodes, function(item) {
            self.connectedNodes.push(new ConnectedProject(item));
        });
    },
    _deauthorizeNodeConfirm: function(node) {
        var self = this;
        var url = node.urls.deauthorize;
        var request = $.ajax({
                url: url,
                type: 'DELETE'
            })
            .done(function(data) {
                self.connectedNodes.remove(node);
            })
            .fail(function(xhr, status, error) {
                Raven.captureMessage('Error deauthorizing node: ' + node.id, {
                    extra: {
                        url: url,
                        status: status,
                        error: error
                    }
                });
            });
    },
    deauthorizeNode: function(node) {
        var self = this;
        bootbox.confirm({
            title: 'Remove addon?',
            message: 'Are you sure you want to remove the ' + $osf.htmlEscape(self.providerName) + ' authorization from this project?',
            callback: function(confirm) {
                if (confirm) {
                    self._deauthorizeNodeConfirm(node);
                }
            },
            buttons:{
                confirm:{
                    label:'Remove',
                    className:'btn-danger'
                }
            }
        });
    }
});

var OAuthAddonSettingsViewModel = oop.defclass({
    constructor: function(name, displayName, institutionId) {
        var self = this;
        self.name = name;
        self.properName = displayName;
        self.institutionId = institutionId;
        self.accounts = ko.observableArray();
        self.message = ko.observable('');
        self.messageClass = ko.observable('');
    },
    setMessage: function(msg, cls) {
        var self = this;
        self.message(msg);
        self.messageClass(cls || 'text-info');
    },
    connectAccount: function() {
        var self = this;
        window.oauthComplete = function() {
            self.setMessage('');
            var accountCount = self.accounts().length;
            self.updateAccounts().done( function() {
                if (self.accounts().length > 0 && self.accounts().length >= accountCount) {  // If there's more than 1 and the count stays the same, probably reauthorizing
                    if (self.name === 'dropbox') {
                        self.setMessage('Add-on successfully authorized. If you wish to link a different account, log out of dropbox.com before attempting to connect to a second Dropbox account on the OSF. This will clear the credentials stored in your browser.', 'text-success');
                    } else if (self.name === 'bitbucket') {
                        self.setMessage('Add-on successfully authorized. If you wish to link a different account, log out of bitbucket.org before attempting to connect to a second Bitbucket account on the OSF. This will clear the credentials stored in your browser.', 'text-success');
                    } else {
                        self.setMessage('Add-on successfully authorized. To link this add-on to an OSF project, go to the settings page of the project, enable ' + self.properName + ', and choose content to connect.', 'text-success');
                    }
                } else {
                    self.setMessage('Error while authorizing add-on. Please log in to your ' + self.properName + ' account and grant access to the OSF to enable this add-on.', 'text-danger');
                }
            });
        };
        window.open('/addons/oauth/connect/' + self.name + '/' + self.institutionId + '/');
    },
    askDisconnect: function(account) {
        var self = this;
        var deletionKey = Math.random().toString(36).slice(-8);
        var id = self.name + "DeleteKey";
        bootbox.confirm({
            title: 'Disconnect Account?',
            message: '<p class="overflow">' +
                'Are you sure you want to disconnect the ' + $osf.htmlEscape(self.properName) + ' account <strong>' +
                $osf.htmlEscape(account.name) + '</strong>?<br>' +
                'This will revoke access to ' + $osf.htmlEscape(self.properName) + ' for all projects using this account.<br><br>' +
                "Type the following to continue: <strong>" + $osf.htmlEscape(deletionKey) + "</strong><br><br>" +
                "<input id='" + $osf.htmlEscape(id) + "' type='text' class='bootbox-input bootbox-input-text form-control'>" +
                '</p>',
            callback: function(confirm) {
                if (confirm) {
                    if ($('#'+id).val() == deletionKey) {
                        self.disconnectAccount(account);
                        self.setMessage('');
                    } else {
                        $osf.growl('Verification failed', 'Strings did not match');
                    }
                }
            },
            buttons:{
                confirm:{
                    label:'Disconnect',
                    className:'btn-danger'
                }
            }
        });
    },
    disconnectAccount: function(account) {
        var self = this;
        var url = '/addons/api/v1/oauth/accounts/' + account.id + '/' + self.institutionId + '/';
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
    },
    updateAccounts: function() {
        var self = this;
        var url = '/addons/api/v1/settings/' + self.name + '/' + self.institutionId + '/accounts/';
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                return new ExternalAccount(account);
            }));
            $('#' + self.name + '-header').osfToggleHeight({height: 160});
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
    }
});

module.exports = {
    ConnectedProject: ConnectedProject,
    ExternalAccount: ExternalAccount,
    OAuthAddonSettingsViewModel: OAuthAddonSettingsViewModel
};
