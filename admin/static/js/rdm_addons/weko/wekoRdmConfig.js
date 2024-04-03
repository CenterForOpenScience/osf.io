'use strict';

const ko = require('knockout');
const $ = require('jquery');
const Raven = require('raven-js');
const OAuthAddonSettingsViewModel = require('../rdmAddonSettings.js').OAuthAddonSettingsViewModel;
const bootbox = require('bootbox');
const oop = require('js/oop');
const WEKOHostSettingsMixin = require('./wekoHostSettings.js');
const osfHelpers = require('js/osfHelpers');
const language = require('js/osfLanguage').Addons.weko;
const addonSettings = require('../rdmAddonSettings');
const sprintf = require('agh.sprintf').sprintf;

const ExternalAccount = addonSettings.ExternalAccount;

const _ = require('js/rdmGettext')._;


function parseDisplayName(displayName) {
    const m = displayName.match(/^(.+)#(.+)$/);
    if (m) {
        return {
            url: m[1],
            name: m[2],
        };
    }
    return {
        url: displayName,
        name: displayName,
    };
}


const ViewModel = oop.extend(OAuthAddonSettingsViewModel, {
    constructor: function(url, institutionId) {
        this.super.constructor.call(this, 'weko', 'WEKO', institutionId);
        WEKOHostSettingsMixin.call(this);

        this.url = url;
        this.accounts = ko.observableArray();
    },
    addHost: function() {
        const self = this;
        this.sendAuth(function() {
            self.clearModal();
            $('#wekoInputHost').modal('hide');
            self.updateAccounts();
        });
    },
    updateAccounts: function() {
        const self = this;
        const url = self.url;
        $.get(url)
            .done(function(data) {
                self.accounts($.map(data.accounts, function(account) {
                    const displayName = parseDisplayName(account.display_name);
                    const externalAccount = new ExternalAccount(account);
                    externalAccount.wekoHost = account.provider_id;
                    externalAccount.wekoUrl = displayName.url;
                    externalAccount.wekoName = displayName.name;
                    return externalAccount;
                }));
                $('#weko-header').osfToggleHeight({height: 160});
            })
            .fail(function(xhr, status, error) {
                self.changeMessage(language.accountsError, 'text-danger');
                Raven.captureMessage(_('Error while retrieving addon account'), {
                    extra: {
                        url: url,
                        status: status,
                        error: error
                    }
                });
            });
    },
    sendAuth: function(callback) {
        const self = this;
        return osfHelpers.postJSON(
            self.url,
            ko.toJS(self.wekoConfig())
        ).done(function() {
            if (!callback) {
                return;
            }
            callback();
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(language.accountsError, 'text-danger');
            Raven.captureMessage(_('Could not set accounts for WEKO'), {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
            if (!callback) {
                return;
            }
            callback();
        });
    },
    askDisconnect: function(account) {
        var self = this;
        bootbox.confirm({
            title: _('Delete WEKO Application?'),
            message: '<p class="overflow">' +
                sprintf(_('Are you sure you want to delete the WEKO application <strong>%1$s</strong>? WEKO add-on connections already set up for the projects will be preserved.'),osfHelpers.htmlEscape(account.name)) +
                '</p>',
            callback: function (confirm) {
                if (confirm) {
                    self.disconnectAccount(account);
                }
            },
            buttons:{
                confirm:{
                    label:_('Disconnect'),
                    className:'btn-danger'
                }
            }
        });
    },
    disconnectAccount: function(account) {
        const self = this;
        const url = '/addons/api/v1/oauth/accounts/' + account.id + '/' + self.institutionId + '/';
        $.ajax({
            url: url,
            type: 'DELETE'
        })
            .done(function(data) {
                self.updateAccounts();
            })
            .fail(function(xhr, status, error) {
                self.changeMessage(language.accountsError, 'text-danger');
                Raven.captureMessage(sprintf(_('Error while removing addon authorization for %1$s') , account.id), {
                    extra: {
                        url: url,
                        status: status,
                        error: error
                    }
                });
            });
    },
    /** Change the flashed status message */
    changeMessage: function(text, css, timeout) {
        const self = this;
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
    },
});

$.extend(ViewModel.prototype, WEKOHostSettingsMixin.prototype);

function UserConfig(selector, url, institutionId) {
    const viewModel = new ViewModel(url, institutionId);
    ko.applyBindings(viewModel, $(selector)[0]);
    this.start = function() {
        viewModel.updateAccounts();
    };
}

module.exports = {
    WEKOViewModel: ViewModel,
    WEKOUserConfig: UserConfig
};
