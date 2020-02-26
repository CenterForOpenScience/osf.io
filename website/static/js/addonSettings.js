'use strict';

var $ = require('jquery');
var ko = require('knockout');
var bootstrap = require('bootstrap');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var oop = require('js/oop');

var $osf = require('js/osfHelpers');

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };
var agh = require('agh.sprintf');

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
                Raven.captureMessage(_('Error deauthorizing node: ') + node.id, {
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
            title: _('Remove addon?'),
            message: agh.sprintf(_('Are you sure you want to remove the %1$s authorization from this project?'),$osf.htmlEscape(self.providerName)),
            callback: function(confirm) {
                if (confirm) {
                    self._deauthorizeNodeConfirm(node);
                }
            },
            buttons:{
                confirm:{
                    label:_('Remove'),
                    className:'btn-danger'
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    }
});

var OAuthAddonSettingsViewModel = oop.defclass({
    constructor: function(name, displayName) {
        var self = this;
        self.name = name;
        self.properName = displayName;
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
                        self.setMessage(_('Add-on successfully authorized. If you wish to link a different account, log out of dropbox.com before attempting to connect to a second Dropbox account on the GakuNin RDM. This will clear the credentials stored in your browser.'), 'text-success');
                    } else if (self.name === 'bitbucket') {
                        self.setMessage(_('Add-on successfully authorized. If you wish to link a different account, log out of bitbucket.org before attempting to connect to a second Bitbucket account on the GakuNin RDM. This will clear the credentials stored in your browser.'), 'text-success');
                    } else if (self.name === 'onedrive') {
                        self.setMessage(_('Add-on successfully authorized. If you wish to link a different account, log out of onedrive.live.com before attempting to connect to a second OneDrive account on the GakuNin RDM. This will clear the credentials stored in your browser.'), 'text-success');
                    } else {
                        self.setMessage(agh.sprintf(_('Add-on successfully authorized. To link this add-on to an GakuNin RDM project, go to the settings page of the project, enable %1$s, and choose content to connect.'),self.properName), 'text-success');
                    }
                } else {
                    self.setMessage(agh.sprintf(_('Error while authorizing add-on. Please log in to your %1$s account and grant access to the GakuNin RDM to enable this add-on.'),self.properName), 'text-danger');
                }
            });
        };
        window.open('/oauth/connect/' + self.name + '/');
    },
    askDisconnect: function(account) {
        var self = this;
        bootbox.confirm({
            title: _('Disconnect Account?'),
            message: '<p class="overflow">' +
                agh.sprintf(_('Are you sure you want to disconnect the %1$s account <strong>%2$s</strong>? This will revoke access to %1$s for all projects you have authorized.'),$osf.htmlEscape(self.properName),$osf.htmlEscape(account.name)) +
                '</p>',
            callback: function(confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                    self.setMessage('');
                }
            },
            buttons:{
                confirm:{
                    label:_('Disconnect'),
                    className:'btn-danger'
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    },
    disconnectAccount: function(account) {
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
            Raven.captureMessage(agh.sprintf(_('Error while removing addon authorization for %1$s') , account.id), {
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
        var url = '/api/v1/settings/' + self.name + '/accounts/';
        var request = $.get(url);
        request.done(function(data) {
            self.accounts($.map(data.accounts, function(account) {
                return new ExternalAccount(account);
            }));
            $('#' + self.name + '-header').osfToggleHeight({height: 160});
        });
        request.fail(function(xhr, status, error) {
            Raven.captureMessage(_('Error while updating addon account'), {
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
