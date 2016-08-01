var ko = require('knockout');
var bootbox = require('bootbox');
var Raven = require('raven-js');

var $osf = require('js/osfHelpers');

var $modal = $('#ownCloudCredentialsModal');
var oop = require('js/oop');
var FolderPickerViewModel = require('js/folderPickerNodeConfig');

var ViewModel = oop.extend(FolderPickerViewModel,{
    constructor: function(addonName, url, selector, folderPicker, opts){
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        const otherString = 'Other (Please Specify)';

        self.addonName = 'ownCloud';
        self.url = url;
        self.urls = ko.observable([]);

        self.username = ko.observable("");
        self.password = ko.observable("");
        self.folderName = ko.observable("");

        self.ownerName = ko.observable();
        self.nodeHasAuth = ko.observable(false);
        self.userHasAuth = ko.observable(false);
        self.userIsOwner = ko.observable(false);
        self.validCredentials = ko.pureComputed(function() {
            return self.nodeHasAuth && self.userHasAuth;
        });
        self.loadedSettings = ko.observable(false);
        self.submitting = ko.observable(false);

        self.accounts = ko.observable([]);
        self.hosts = ko.observableArray([]);
        self.selectedHost = ko.observable();    // Host specified in select element
        self.customHost = ko.observable();      // Host specified in input element
        self.savedHost = ko.observable();       // Configured host

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

        // Whether to use select element or input element for host designation
        self.useCustomHost = ko.pureComputed(function() {
            return self.selectedHost() === otherString;
        });
        self.credentialsChanged = ko.pureComputed(function() {
            return self.nodeHasAuth() && !self.validCredentials();
        });
        self.showCredentials = ko.pureComputed(function() {
            return (self.credentialsChanged() && self.userIsOwner()) ||
                (!self.userHasAuth() && !self.nodeHasAuth() );
        });
        self.showCredentialInput = ko.pureComputed(function(){
            //
            return Boolean(self.selectedHost());
        });

        self.messages.userSettingsError = ko.pureComputed(function() {
                return 'Could not retrieve settings. Please refresh the page or ' +
                    'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                    'problem persists.';
        });
        self.messages.submitSettingsSuccess =  ko.pureComputed(function() {
            var name = self.options.decodeFolder($osf.htmlEscape(self.folder().name));
            return 'Successfully linked "' + name + '". Go to the <a href="' +
                self.urls().files + '">Files page</a> to view your content.';
        });

        self.messages.confirmDeauth = ko.pureComputed(function() {
            return 'Are you sure you want to remove this ' + self.addonName + ' account?';
        });
        self.messages.confirmAuth = ko.pureComputed(function() {
            return 'Are you sure you want to authorize this project with your ' + self.addonName + ' credentials?';
        });
        self.messages.deauthorizeSuccess = ko.pureComputed(function() {
            return 'Disconnected ' + self.addonName + '.';
        });
        self.messages.deauthorizeFail = ko.pureComputed(function() {
            return 'Could not disconnect because of an error. Please try again later.';
        });
        self.messages.authInvalid = ko.pureComputed(function() {
            return 'The credentials provided for ' + $osf.htmlEscape(self.host()) + ' are invalid.';
        });
        self.messages.authError = ko.pureComputed(function() {
            return 'Sorry, but there was a problem connecting to that instance of OwnCloud. It ' +
                'is likely that the instance hasn\'t been upgraded to OwnCloud 4.0. If you ' +
                'have any questions or believe this to be an error, please contact ' +
                'support@osf.io.';
        });
        self.messages.credentialImportSuccess = ko.pureComputed(function() {
            return 'Successfully imported credentials from profile.';
        });
        self.messages.credentialImportError = ko.pureComputed(function() {
            return 'Error occurred while importing credentials.';
        });
        self.messages.updateAccountsError = ko.pureComputed(function() {
            return 'Could not retrieve ' + self.addonName + ' account list at ' +
                'this time. Please refresh the page. If the problem persists, email ' +
                '<a href="mailto:support@osf.io">support@osf.io</a>.';
        });
        self.messages.forbiddenCharacters = ko.pureComputed(function() {
            return 'This owncloud cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.';
        });
        self.messages.setInfoSuccess = ko.pureComputed(function() {
            var filesUrl = window.contextVars.node.urls.web + 'files/';
            return 'Successfully linked folder \'' + $osf.htmlEscape(self.folderName()) + '\'. Go to the <a href="' +
                filesUrl + '">Files page</a> to view your content.';
        });
        self.messages.setFolderError = ko.pureComputed(function() {
            return 'Could not connect to this folder. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        });
        self.messages.getFoldersError = ko.pureComputed(function() {
            return 'Could not load folders. Please refresh the page or ' +
                'contact <a href="mailto: support@osf.io">support@osf.io</a> if the ' +
                'problem persists.';
        });

        // Overrides
        var defaults = {
            onPickFolder: function(evt, item) {
                evt.preventDefault();
                var name = item.data.path !== '/' ? item.data.path : '/ (Full ' + self.addonName + ')';
                self.selected({
                    name: name,
                    path: item.data.path,
                    id: item.data.id
                });
                self.folderName(name);
                return false; // Prevent event propagation
            },
            connectAccount: function() {
                window.location.href = this.urls().auth;
            },
            decodeFolder: function(folder_name) {
                return folder_name;
            }
        };
        // Overrides
        self.options = $.extend({}, defaults, opts);
        // Treebeard config
        self.treebeardOptions = $.extend(
            {},
            FolderPickerViewModel.prototype.treebeardOptions,
            {
                onPickFolder: function(evt, item) {
                    return this.options.onPickFolder.call(this, evt, item);
                }.bind(this),
                resolveLazyloadUrl: function(item) {
                    return item.data.urls.folders;
                },
                decodeFolder: function(item) {
                    return this.options.decodeFolder.call(this, item);
                }.bind(this)

            }
        );


        self.credentialsChanged = ko.pureComputed(function() {
            return self.nodeHasAuth() && !self.validCredentials();
        });
        self.showCredentialInput = ko.pureComputed(function() {
            return (self.credentialsChanged() && self.userIsOwner()) ||
                (!self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings());
        });

        self.showSettings = ko.pureComputed(function() {
            return self.nodeHasAuth() && self.validCredentials();
        });
        self.showImport = ko.pureComputed(function() {
            return self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
        });
        self.showCredentialCreateButton = ko.pureComputed(function() {
            return !self.userHasAuth() && !self.nodeHasAuth() && self.loadedSettings();
        });

        // Flashed messages
        self.message = ko.observable('');
        self.messageClass = ko.observable('text-info');

        // Update above observables with data from the server
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function(response) {
            // Update view model
            self.folderName(response.result.folder);
            self.updateFromData(response.result);
            self.loadedSettings(true);
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(self.messages.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET dataverse settings', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });

        self.selectionChanged = function() {
            self.changeMessage('','');
        };
    }
});


/** Reset all fields from OwnCloud host selection modal */
ViewModel.prototype.clearModal = function() {
    var self = this;
    self.message('');
    self.messageClass('text-info');
    self.apiToken(null);
    self.selectedHost(null);
    self.customHost(null);
};


/** Send POST request to authorize OwnCloud */
ViewModel.prototype.sendAuth = function() {
    var self = this;

    // Selection should not be empty
    if( !self.selectedHost() ){
        self.changeMessage("Please select a OwnCloud repository.", 'text-danger');
        return;
    }
    var url = self.urls().create;
    return $osf.postJSON(
        url,
        ko.toJS({
            host: self.host,
            api_token: self.apiToken
        })
    ).done(function() {
        self.clearModal();
        $modal.modal('hide');
        self.userHasAuth(true);
        self.importAuth();
    }).fail(function(xhr, textStatus, error) {
        var errorMessage = (xhr.status === 401) ? self.messages.authInvalid : self.messages.authError;
        self.changeMessage(errorMessage, 'text-danger');
        Raven.captureMessage('Could not authenticate with OwnCloud', {
            url: url,
            textStatus: textStatus,
            error: error
        });
    });
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
            url: self.url,
            textStatus: textStatus,
            error: error
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
    var msg = response.message || self.messages.credentialImportSuccess();
    // Update view model based on response
    self.changeMessage(msg, 'text-success', 3000);

    self.urls(response.result.urls);
    self.ownerName(response.result.ownerName);
    self.nodeHasAuth(response.result.nodeHasAuth);
    self.userHasAuth(response.result.userHasAuth);
    self.userIsOwner(response.result.userIsOwner);
    self.hosts(response.result.hosts);
};

ViewModel.prototype.onImportError = function(xhr, status, error) {
    var self = this;
    self.changeMessage(self.messages.credentialImportError(), 'text-danger');
    Raven.captureMessage('Failed to import ' + self.addonName + ' access token.', {
        xhr: xhr,
        status: status,
        error: error
    });
};

/**
 * Allows a user to create an access token from the nodeSettings page
 */
ViewModel.prototype.connectAccount = function() {
    var self = this;

    window.oauthComplete = function(res) {
        // Update view model based on response
        self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
        self.importAuth.call(self);
    };
    window.open(self.urls().auth);
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
                    title: 'Choose ' + $osf.htmlEscape(self.addonName) + ' Credentials to Import',
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
                    title: 'Import ' + $osf.htmlEscape(self.addonName) + ' Credentials?',
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
            url: self.urls().deauthorize,
            textStatus: textStatus,
            error: error
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

function OwnCloudNodeConfig(selector, url) {
    var self = this;
    self.viewModel = new ViewModel('owncloud', url, selector, '#owncloudGrid', {});
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = OwnCloudNodeConfig;
