/**
 * Module that controls the citations addons node settings. Includes Knockout view-model
 * for syncing data, and HGrid-folderpicker for selecting a folder.
 */
'use strict';

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var $osf = require('js/osfHelpers');
var oop = require('js/oop');
var FolderPickerViewModel = require('js/folderPickerNodeConfig');


/**
 * View model to support instances of CitationsNodeConfig (folder picker widget)
 *
 * @class AddonFolderPickerViewModel
 * @param {String} addonName Full display name of the addon
 * @param {String} url API url to initially fetch settings
 * @param {String} selector CSS selector for containing div
 * @param {String} folderPicker CSS selector for folderPicker div
 */
var CitationsFolderPickerViewModel = oop.extend(FolderPickerViewModel, {
    constructor: function(addonName, url, selector, folderPicker) {
        var self = this;
        self.super.constructor.call(self, addonName, url, selector, folderPicker);
        self.userAccountId = ko.observable('');
        // externalAccounts
        self.accounts = ko.observable([]);

        self.messages.submitSettingsSuccess = ko.pureComputed(function(){
            return 'Successfully linked "' + $osf.htmlEscape(self.folder().name) + '". Go to the <a href="' +
                self.urls().files + '">Overview page</a> to view your citations.';
        });

        self.treebeardOptions = $.extend(
            {},
            FolderPickerViewModel.prototype.treebeardOptions,
            {
                /** Callback for chooseFolder action.
                 *   Just changes the ViewModel's self.selected observable to the selected
                 *   folder.
                 */
                onPickFolder: function(evt, item){
                    evt.preventDefault();
                    this.selected({
                        name: item.data.name,
                        id: item.data.id
                    });
                    return false; // Prevent event propagation
                }.bind(this),
                lazyLoadPreprocess: function(data) {
                    return data.contents.filter(function(item) {
                    return item.kind === 'folder';
                    });
                },
                resolveLazyloadUrl: function(item) {
                    return this.urls().folders + item.data.id + '/?view=folders';
                }.bind(this)
            });
    },
    fetchAccounts: function() {
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
    },
    updateAccounts: function() {
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
    },
    /**
     * Allows a user to create an access token from the nodeSettings page
     */
    connectAccount: function() {
        var self = this;

        window.oauthComplete = function(res) {
            // Update view model based on response
            self.changeMessage(self.messages.connectAccountSuccess(), 'text-success', 3000);
            self.userHasAuth(true);
            self.importAuth.call(self);
        };
        window.open(self.urls().auth);
    },
    connectExistingAccount: function(account_id) {
        var self = this;

        return $osf.putJSON(
            self.urls().importAuth, {
                external_account_id: account_id
            }
        ).then(self.onImportSuccess.bind(self), self.onImportError.bind(self));
    },
    _updateCustomFields: function(settings){
        var self = this;
        self.userAccountId(settings.userAccountId);
        self.validCredentials(settings.validCredentials);
    },
    _serializeSettings: function(){
        return {
            external_account_id: this.userAccountId(),
            external_list_id: this.selected().id,
            external_list_name: this.selected().name
        };
    },
    importAuth: function() {
        var self = this;
        self.updateAccounts()
            .then(function(){
                if (self.accounts().length > 1) {
                    bootbox.prompt({
                        title: 'Choose ' + $osf.htmlEscape(self.addonName) + ' Access Token to Import',
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
                        title: 'Import ' + $osf.htmlEscape(self.addonName) + ' access token',
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
    },
    afterUpdate: function() {
        var self = this;
        if (self.nodeHasAuth() && !self.validCredentials()) {
            var message;
            if (self.userIsOwner()) {
                message = self.messages.invalidCredOwner();
            }
            else {
                message = self.messages.invalidCredNotOwner();
            }
            self.changeMessage(message, 'text-danger');
        }
    }
});
// Public API
function CitationsNodeConfig(addonName, selector, url, folderPicker) {
    var self = this;
    self.url = url;
    self.folderPicker = folderPicker;
    self.viewModel = new CitationsFolderPickerViewModel(addonName, url, selector, folderPicker);
    self.viewModel.updateFromData();
    $osf.applyBindings(self.viewModel, selector);
}

module.exports = {
    CitationsNodeConfig: CitationsNodeConfig,
    _CitationsNodeConfigViewModel: CitationsFolderPickerViewModel
};
