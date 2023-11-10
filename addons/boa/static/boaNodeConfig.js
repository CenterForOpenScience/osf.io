'use strict';

var $ = require('jquery');
var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var bootbox = require('bootbox');
var $modal = $('#boaCredentialsModal');
var language = require('js/osfLanguage').Addons.boa;


function ViewModel(url) {
    var self = this;

    self.addonName = 'Boa';
    self.url = url;
    self.urls = ko.observable();

    // Non-Oauth fields:
    self.username = ko.observable('');
    self.password = ko.observable('');

    // Magical mystery fields
    self.clearModal = function() {};

    self.ownerName = ko.observable();
    self.nodeHasAuth = ko.observable(false);
    self.userHasAuth = ko.observable(false);
    self.userIsOwner = ko.observable(false);
    self.validCredentials = ko.observable(false);
    self.loadedSettings = ko.observable(false);

    // rename this, boa uses username/auth, not token
    self.showTokenCreateButton = ko.pureComputed(function() {
        return !self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });


    self.showSettings = ko.pureComputed(function() {
        return self.nodeHasAuth() && self.validCredentials();
    });
    self.showImport = ko.pureComputed(function() {
        return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
    });

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');
    self.messages = {
        userSettingsError: ko.pureComputed(function() {
            return 'Could not retrieve settings. Please refresh the page or ' +
                'contact ' + $osf.osfSupportLink() + ' if the problem persists.';
        }),
        confirmDeauth: ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.addonName + ' account?';
        }),
        confirmAuth: ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.addonName + ' credentials?';
        }),
        deauthorizeSuccess: ko.pureComputed(function() {
            return 'Disconnected ' + self.addonName + '.';
        }),
    };

    self.accounts = ko.observable([]);

    // Update above observables with data from the server
    console.debug('>> update observables, url ib:', url);
    $.ajax({
        url: url,
        type: 'GET',
        dataType: 'json'
    }).done(function(response) {
        // Update view model
        self.updateFromData(response.result);
        self.loadedSettings(true);
    }).fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.userSettingsError, 'text-danger');
        Raven.captureMessage('Could not GET Boa settings', {
            extra: {
                url: url,
                textStatus: textStatus,
                error: error
            }
        });
    });

}

/**
 * Update the view model from data returned from the server.
 */
ViewModel.prototype.updateFromData = function(data) {
    var self = this;
    self.urls(data.urls);
    self.ownerName(data.ownerName);
    self.nodeHasAuth(data.nodeHasAuth);
    self.userHasAuth(data.userHasAuth);
    self.userIsOwner(data.userIsOwner);

    if (self.nodeHasAuth()) {
        self.validCredentials(data.connected);
    }
};


ViewModel.prototype.fetchAccounts = function() {
    var self = this;
    var ret = $.Deferred();
    var request = $.get(self.urls().accounts);
    request.then(function(data) {
        ret.resolve(data.accounts);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.updateAccountsError(), 'text-danger');
        Raven.captureMessage('Could not GET ' + self.addonName + ' accounts for user', {
            extra: {
                url: self.url,
                textStatus: textStatus,
                error: error
            }
        });
        ret.reject(xhr, textStatus, error);
    });
    return ret.promise();
};

ViewModel.prototype.updateAccounts = function() {
    var self = this;
    return self.fetchAccounts()
        .done(function(accounts) {
            self.accounts(
                $.map(accounts, function(account) {
                    return {
                        name: account.display_name,
                        id: account.id
                    };
                })
            );
        });
};

ViewModel.prototype.onImportSuccess = function(response) {
    var self = this;
    var msg = response.message || self.messages.tokenImportSuccess();
    // Update view model based on response
    self.changeMessage(msg, 'text-success', 3000);
    self.updateFromData(response.result);
};

ViewModel.prototype.onImportError = function(xhr, status, error) {
    var self = this;
    self.changeMessage(self.messages.tokenImportError(), 'text-danger');
    Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
        extra: {
            xhr: xhr,
            status: status,
            error: error
        }
    });
};


ViewModel.prototype.clearModal = function() {
    var self = this;
};

/**
 * Allows a user to create an access token from the nodeSettings page
 */
ViewModel.prototype.connectAccount = function() {
    var self = this;

    if ( !(self.username() && self.password()) ){
        self.changeMessage('Please enter a username and password.', 'text-danger');
        return;
    }

    var url = self.urls().auth;
    $osf.postJSON(
        url,
        ko.toJS({
            password: self.password,
            username: self.username
        })
    ).done(function() {
        self.clearModal();
        $modal.modal('hide');
        self.updateAccounts().then(function() {
            try{
                $osf.putJSON(
                    self.urls().importAuth, {
                        external_account_id: self.accounts()[0].id
                    }
                ).done(self.onImportSuccess.bind(self)
                      ).fail(self.onImportError.bind(self));
                self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
            }
            catch(err){
                self.changeMessage(self.messages.connectAccountDenied(), 'text-danger', 6000);
            }
        });
    }).fail(function(xhr, textStatus, error) {
        var errorMessage = (xhr.status === 401) ? language.authInvalid : language.authError;
        self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with Boa', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
};

ViewModel.prototype.connectExistingAccount = function(account_id) {
    var self = this;

    return $osf.putJSON(
        self.urls().importAuth, {
            external_account_id: account_id
        }
    ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
};

/**
 *  Send PUT request to import access token from user profile.
 */
ViewModel.prototype.importAuth = function() {
    var self = this;
    self.updateAccounts()
        .then(function(){
            if (self.accounts().length > 1) {
                bootbox.prompt({
                    title: 'Choose ' + $osf.htmlEscape(self.addonName) + ' credentials to Import',
                    inputType: 'select',
                    inputOptions: ko.utils.arrayMap(
                        self.accounts(),
                        function(item) {
                            return {
                                text: $osf.htmlEscape(item.name),
                                value: item.id
                            };
                        }
                    ),
                    value: self.accounts()[0].id,
                    callback: function(accountId) {
                        if (accountId) {
                            self.connectExistingAccount.call(self, (accountId));
                        }
                    },
                    buttons:{
                        confirm:{
                            label: 'Import'
                        }
                    }
                });
            } else {
                bootbox.confirm({
                    title: 'Import ' + $osf.htmlEscape(self.addonName) + ' credentials?',
                    message: self.messages.confirmAuth(),
                    callback: function(confirmed) {
                        if (confirmed) {
                            self.connectExistingAccount.call(self, (self.accounts()[0].id));
                        }
                    },
                    buttons:{
                        confirm:{
                            label:'Import'
                        }
                    }
                });
            }
        });
};

/**
 * Send DELETE request to deauthorize this node.
 */
ViewModel.prototype._deauthorizeConfirm = function() {
    var self = this;
    var request = $.ajax({
        url: self.urls().deauthorize,
        type: 'DELETE'
    });
    request.done(function() {
        // Update observables
        self.nodeHasAuth(false);
        self.clearModal();
        self.changeMessage(self.messages.deauthorizeSuccess(), 'text-warning', 3000);
    });
    request.fail(function(xhr, textStatus, error) {
        self.changeMessage(self.messages.deauthorizeFail(), 'text-danger');
        Raven.captureMessage('Could not deauthorize ' + self.addonName + ' account from node', {
            extra: {
                url: self.urls().deauthorize,
                textStatus: textStatus,
                error: error
            }
        });
    });
    return request;
};

/** Pop up a confirmation to deauthorize addon from this node.
 *  Send DELETE request if confirmed.
 */
ViewModel.prototype.deauthorize = function() {
    var self = this;
    bootbox.confirm({
        title: 'Disconnect ' + $osf.htmlEscape(self.addonName) + ' Account?',
        message: self.messages.confirmDeauth(),
        callback: function(confirmed) {
            if (confirmed) {
                self._deauthorizeConfirm();
            }
        },
        buttons:{
            confirm:{
                label: 'Disconnect',
                className: 'btn-danger'
            }
        }
    });
};

/** Change the flashed status message */
ViewModel.prototype.changeMessage = function(text, css, timeout) {
    var self = this;
    if (typeof text === 'function') {
        text = text();
    }
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

function BoaNodeConfig(selector, url) {
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    $osf.applyBindings(self.viewModel, '#boaScope');
}

module.exports = BoaNodeConfig;
